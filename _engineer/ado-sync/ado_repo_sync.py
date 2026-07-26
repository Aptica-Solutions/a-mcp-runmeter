#!/usr/bin/env python3
"""
Generate and optionally apply Azure DevOps work item updates from a source repo.

Typical use from any repo:
  python3 /path/to/ia-ado-pbi-automation/ado_repo_sync.py --repo . --parent-id 2505
  python3 /path/to/ia-ado-pbi-automation/ado_repo_sync.py --repo . --parent-id 2505 --apply

The script is dry-run/plan-first by default. It reads git evidence from the
source repo, reads the target ADO parent and descendants, asks Claude to map
completed repo work to existing work items, saves a plan JSON, and previews the
ADO JSON Patch updates. Use --apply to execute the generated plan.
"""
from __future__ import annotations
# pylint: disable=duplicate-code

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

for _pkg in ("anthropic", "requests"):
    try:
        __import__(_pkg)
    except ModuleNotFoundError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", _pkg, "-q", "--break-system-packages"],
            stdout=subprocess.DEVNULL,
        )

# pylint: disable=wrong-import-position
import anthropic  # type: ignore[import]
import requests  # type: ignore[import]

from ado_lib import ADOClient, ORG, PROJECT, execute_operation, print_proposed, PLAN_DIR
# pylint: enable=wrong-import-position


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


SUBMIT_TOOL = {
    "name": "submit_ado_update_plan",
    "description": "Submit ADO update operations inferred from source repository evidence.",
    "input_schema": {
        "type": "object",
        "required": ["summary", "operations"],
        "properties": {
            "summary": {"type": "string"},
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["action", "work_item_type", "work_item_id", "title"],
                    "properties": {
                        "action": {"type": "string", "enum": ["update", "find"]},
                        "work_item_type": {
                            "type": "string",
                            "enum": [
                                "Epic", "Feature", "Automation Request",
                                "Product Backlog Item", "Task",
                                "Bug", "Issue", "Automation Asset", "Support Item",
                            ],
                        },
                        "work_item_id": {"type": "integer"},
                        "title": {"type": "string"},
                        "state": {"type": "string"},
                        "tags": {"type": "string"},
                        "description": {"type": "string"},
                        "acceptance_criteria": {"type": "string"},
                        "reasoning": {"type": "string"},
                    },
                },
            },
        },
    },
}


SYSTEM_PROMPT = """\
You are an Azure DevOps work item synchronization assistant.

Your job is to compare source repository evidence against an existing ADO work
item subtree and return only updates to existing ADO items. Do not create new
work items. Prefer conservative updates: mark tasks Done only when the repo has
clear code or documentation evidence that the work was implemented. Keep PBIs in
an in-progress state when live testing, UAT, production validation, deployment,
or stakeholder sign-off remains open.

Rules:
- Always call submit_ado_update_plan.
- Use only work_item_id values present in the supplied ADO subtree.
- Use only valid states listed in the supplied state reference.
- Preserve useful existing tags when you can infer them; add tags like
  "Repo Reviewed", "Completed In Code", "Mostly Implemented", or a technology
  tag only when supported by evidence.
- Include a one-sentence reasoning for every operation.
- If evidence is ambiguous, omit the update rather than guessing.
"""


def _run(cmd: list[str], cwd: Path, limit: int = 20000) -> str:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)
    except FileNotFoundError:
        return f"ERROR: command not found: {cmd[0]}"
    out = (p.stdout or "") + (p.stderr or "")
    if len(out) > limit:
        return out[:limit] + "\n... [truncated]"
    return out.strip()


def collect_repo_evidence(repo: Path, base_ref: str | None, max_commits: int) -> str:
    """Return a multi-section string summarising git evidence for the repo."""
    if not (repo / ".git").exists():
        raise ValueError(f"Not a git repo: {repo}")

    parts: list[str] = []
    parts.append(f"# Source repository\nPath: {repo}")
    parts.append("## Git remote\n" + _run(["git", "remote", "-v"], repo))
    parts.append(
        "## Branch / HEAD\n"
        + _run(["git", "branch", "--show-current"], repo)
        + "\n"
        + _run(["git", "rev-parse", "HEAD"], repo)
    )
    parts.append(
        "## Recent commits\n"
        + _run(["git", "log", "--oneline", "--decorate", f"--max-count={max_commits}"], repo)
    )
    parts.append("## Status\n" + (_run(["git", "status", "--short"], repo) or "clean"))

    if base_ref:
        parts.append(
            f"## Changed files since {base_ref}\n"
            + _run(["git", "diff", "--name-status", base_ref], repo)
        )
        parts.append(
            f"## Diff summary since {base_ref}\n"
            + _run(["git", "diff", "--stat", base_ref], repo)
        )
    else:
        parts.append("## Tracked files\n" + _run(["git", "ls-files"], repo, limit=30000))

    for rel in ["AI-TASKS.md", "REQUIREMENTS.md", "README.md", "CLAUDE.md"]:
        p = repo / rel
        if p.exists() and p.is_file():
            text = p.read_text(errors="replace")
            if len(text) > 20000:
                text = text[:20000] + "\n... [truncated]"
            parts.append(f"## {rel}\n{text}")

    return "\n\n".join(parts)


def _child_ids(ado: ADOClient, parent_id: int) -> list[int]:
    """Return direct child work item IDs for *parent_id*."""
    result = ado.run_wiql(f"""
        SELECT [System.Id] FROM WorkItems
        WHERE [System.TeamProject] = '{ado.project}'
          AND [System.Parent] = {parent_id}
          AND [System.State] <> 'Removed'
        ORDER BY [System.Id]
    """)
    return [int(i["id"]) for i in result.get("workItems", [])]


def _descendant_ids(ado: ADOClient, root_id: int) -> list[int]:
    """Return all descendant work item IDs (BFS) starting from *root_id*."""
    seen: set[int] = set()
    queue = [root_id]
    ordered: list[int] = []
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        ordered.append(current)
        queue.extend(_child_ids(ado, current))
    return ordered


def _valid_states(ado: ADOClient, work_item_types: set[str]) -> dict[str, list[str]]:
    """Return a mapping of work item type → list of valid state names."""
    states: dict[str, list[str]] = {}
    for wit in sorted(work_item_types):
        enc = urllib.parse.quote(wit, safe="")
        url = f"{ado.base_url}/_apis/wit/workitemtypes/{enc}/states?api-version=7.1"
        r = requests.get(url, auth=ado.auth, timeout=30)
        if r.ok:
            states[wit] = [s["name"] for s in r.json().get("value", [])]
    return states


def collect_ado_context(ado: ADOClient, parent_id: int) -> tuple[str, dict[str, list[str]]]:
    """Build an ADO context string + valid-states map for the *parent_id* subtree."""
    ids = _descendant_ids(ado, parent_id)
    fields = [
        "System.Id", "System.Title", "System.WorkItemType",
        "System.State", "System.Parent", "System.Tags",
    ]
    items = ado.get_work_items_batch(ids, fields=fields)
    types = {i["fields"].get("System.WorkItemType", "") for i in items if i.get("fields")}
    states = _valid_states(ado, types)

    lines = [f"# Target ADO subtree rooted at #{parent_id}"]
    for item in items:
        f = item["fields"]
        lines.append(
            f"- #{item['id']} [{f.get('System.WorkItemType')}] {f.get('System.Title')} "
            f"| state={f.get('System.State')} | parent={f.get('System.Parent', '')} "
            f"| tags={f.get('System.Tags', '')}"
        )
    lines.append("\n# Valid states by work item type")
    lines.append(json.dumps(states, indent=2))
    return "\n".join(lines), states


def generate_plan(repo_evidence: str, ado_context: str, model: str) -> dict:
    """Call Claude to generate an ADO update plan from repo and ADO context."""
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=6000,
        system=[{"type": "text", "text": SYSTEM_PROMPT}],
        tools=[SUBMIT_TOOL],  # type: ignore[arg-type]
        tool_choice={"type": "tool", "name": "submit_ado_update_plan"},
        messages=[{"role": "user", "content": ado_context + "\n\n" + repo_evidence}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_ado_update_plan":
            return block.input
    raise ValueError("Claude did not return submit_ado_update_plan")


def save_plan(plan: dict, repo: Path, parent_id: int) -> Path:
    """Serialise *plan* to a timestamped JSON file in PLAN_DIR and return the path."""
    plan_dir = Path(PLAN_DIR)
    plan_dir.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = plan_dir / f"ado-repo-sync-{parent_id}-{ts}.json"
    wrapped = {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "source": f"repo={repo}; parent_id={parent_id}",
        "summary": plan.get("summary", ""),
        "operations": plan.get("operations", []),
    }
    path.write_text(json.dumps(wrapped, indent=2))
    return path


def main() -> int:
    """Parse CLI args, collect evidence, generate a plan, then apply or save it."""
    parser = argparse.ArgumentParser(
        description="Generate/apply ADO updates from the current source repo."
    )
    parser.add_argument(
        "--repo", default=".",
        help="Source git repo to inspect. Defaults to current directory.",
    )
    parser.add_argument(
        "--parent-id", type=int, required=True,
        help="ADO parent/root work item ID whose descendants may be updated.",
    )
    parser.add_argument(
        "--base-ref",
        help="Optional git ref to diff against, e.g. origin/main or HEAD~5.",
    )
    parser.add_argument(
        "--max-commits", type=int, default=30,
        help="Number of recent commits to include.",
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-6",
        help="Anthropic model to use.",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply generated updates. Default is dry-run preview only.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    ado = ADOClient(org=ORG, project=PROJECT)

    print(f"Collecting repo evidence from {repo}...")
    repo_evidence = collect_repo_evidence(repo, args.base_ref, args.max_commits)
    print(f"Loading ADO subtree rooted at #{args.parent_id}...")
    ado_context, _ = collect_ado_context(ado, args.parent_id)
    print("Generating ADO update plan...")
    plan = generate_plan(repo_evidence, ado_context, args.model)
    plan_path = save_plan(plan, repo, args.parent_id)

    ops = plan.get("operations", [])
    print(f"\nPlan saved: {plan_path}")
    print(f"\n{plan.get('summary', '')}\n")
    print_proposed(ops)

    print("\nPreviewing patches:" if not args.apply else "\nApplying updates:")
    for op in ops:
        execute_operation(ado, op, dry_run=not args.apply)

    if not args.apply:
        cmd = (
            f"python3 {Path(__file__).resolve()}"
            f" --repo {repo} --parent-id {args.parent_id} --apply"
        )
        print(f"\nDRY RUN only. To apply: {cmd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
