#!/usr/bin/env python3
"""
AI-powered ADO work item creator.

Usage:
  python3 ai_ado_creator.py                                             # interactive mode
  python3 ai_ado_creator.py --dry-run                                   # preview, no ADO changes
  python3 ai_ado_creator.py --refresh                                   # force-reload context cache
  python3 ai_ado_creator.py --discovery-scaffold          # Epic + Discovery PBI + tasks
  python3 ai_ado_creator.py --discovery-scaffold --source-info <file>   # from doc
  python3 ai_ado_creator.py --development-scaffold        # full hierarchy (paste text)
  python3 ai_ado_creator.py --development-scaffold --source-info <path> # from file

At the prompt, type plain English:
  "We finished the API integration for PROJ-001 and are now working on error handling."
  "Need a new PBI under PROJ-002 to handle the timeout issue."
  "PROJ-003 referral is blocked waiting on Epic sign-off."
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

# ── Auto-install deps (mirrors pattern from existing scripts) ──────────────────
import subprocess
for _pkg in ("anthropic", "requests"):
    try:
        __import__(_pkg)
    except ModuleNotFoundError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", _pkg, "-q", "--break-system-packages"],
            stdout=subprocess.DEVNULL,
        )

# pylint: disable=wrong-import-position
from ado_lib import (
    ADOClient, ORG, PROJECT, PAT, ADO_WEB, PLAN_DIR, PLAN_FILE,
    interpret, format_field,
    load_context, build_context_summary,
    ingest,
    build_from_documents, build_scaffold,
    execute_operation, execute_operation_returning_id, print_proposed,
)
# pylint: enable=wrong-import-position


# ── REPL ───────────────────────────────────────────────────────────────────────

def repl(  # pylint: disable=too-many-branches,too-many-statements
    ado: ADOClient, dry_run: bool, items: list,
) -> None:
    """Run the interactive REPL for plain-English ADO update requests."""
    context_summary = build_context_summary(items)

    print(f"\n  Loaded {len(items)} work items.")
    print("  Type a plain-English update. Commands: dry-run · refresh · quit\n")

    while True:
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye.")
            break

        if not raw:
            continue

        cmd = raw.lower()
        if cmd == "quit":
            break
        if cmd == "dry-run":
            dry_run = not dry_run
            print(f"  Dry-run {'ON' if dry_run else 'OFF'}\n")
            continue
        if cmd == "refresh":
            items           = load_context(ado, force_refresh=True)
            context_summary = build_context_summary(items)
            print(f"  Reloaded {len(items)} work items.\n")
            continue

        print("\n  Interpreting...", flush=True)
        try:
            result = interpret(raw, context_summary)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"  AI error: {exc}\n")
            continue

        ops     = result.get("operations", [])
        summary = result.get("summary", "")

        if not ops:
            print("  No operations inferred — try being more specific.\n")
            continue

        print(f"\n  {summary}\n")
        print("  Proposed operations:")
        print_proposed(ops)

        if dry_run:
            print("\n  [DRY RUN — previewing patches]\n")
            for op in ops:
                execute_operation(ado, op, dry_run=True)
            print()
            continue

        prompt = f"\n  Apply {len(ops)} operation(s)?  [y / n / d (dry-run preview)]:  "
        print(prompt, end="", flush=True)
        try:
            answer = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"

        print()
        if answer == "y":
            for op in ops:
                execute_operation(ado, op, dry_run=False)
        elif answer == "d":
            for op in ops:
                execute_operation(ado, op, dry_run=True)
        else:
            print("  Cancelled.")
        print()


# ── Shared Confirm + Execute ───────────────────────────────────────────────────


def _make_plan_path() -> str:
    """Return a timestamped plan file path and ensure the plan directory exists."""
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(PLAN_DIR, exist_ok=True)
    return os.path.join(PLAN_DIR, f"ado-plan-{ts}.json")


def _save_plan(result: dict, source: str) -> str:
    """Serialise the plan dict to a timestamped JSON file and print the execute command."""
    plan_path = _make_plan_path()
    plan = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "summary": result.get("summary", ""),
        "operations": result.get("operations", []),
    }
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_ado_creator.py")
    print(f"  Plan saved → {plan_path}")
    print()
    print("  ┌─ Run this command to execute when ready ──────────────────────────")
    print(f"  │  python3 {script} --execute-plan {plan_path}")
    print("  └───────────────────────────────────────────────────────────────────")
    print()
    return plan_path


def _confirm_and_execute(  # pylint: disable=too-many-branches,too-many-statements
    ado: ADOClient, result: dict, dry_run: bool, mode_label: str, source: str = "",
) -> None:
    """Summarise proposed ops, save plan, then prompt user to confirm and execute."""
    ops     = result.get("operations", [])
    summary = result.get("summary", "")

    if not ops:
        print(
            "  No operations generated \u2014 check that your input "
            "contains project scope information."
        )
        return

    print(f"  {summary}\n")
    print(f"  Proposed {mode_label} ({len(ops)} items):")
    print_proposed(ops)
    _save_plan(result, source or mode_label)  # prints path + execute command

    if dry_run:
        print(
            "  [DRY RUN \u2014 no changes made. Edit the plan file then run "
            "--execute-plan to apply.]\n"
        )
        return

    prompt = f"\n  Create {len(ops)} work item(s) in ADO?  [y / n / d (dry-run preview)]:  "
    print(prompt, end="", flush=True)
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"

    print()
    if answer == "y":
        _execute_ops(ado, ops)
    elif answer == "d":
        for op in ops:
            execute_operation(ado, op, dry_run=True)
    else:
        print("  Cancelled.")
    print()


def _execute_ops(ado: ADOClient, ops: list) -> None:
    created: dict[str, int] = {}
    for op in ops:
        if not op.get("parent_id") and op.get("parent_title"):
            resolved = created.get(op["parent_title"])
            if resolved:
                op["parent_id"] = resolved
        item_id = execute_operation_returning_id(ado, op, dry_run=False)
        if item_id:
            created[op["title"]] = item_id
    print(f"\n  Done. {len(created)} item(s) created.")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _prompt_epic_name() -> str | None:
    print("\n  Epic name (e.g. 'PROJ-001 – Customer Onboarding Automation'):  ", end="", flush=True)
    try:
        name = input().strip()
    except (EOFError, KeyboardInterrupt):
        name = ""
    if not name:
        print("  No Epic name entered — cancelled.")
        return None
    return name


# ── Scaffold Text Flow ─────────────────────────────────────────────────────────

def _query_epic_features(ado: ADOClient, epic_name: str) -> tuple[int | None, bool, list[str]]:
    """
    Look up the Epic by title, then fetch its child Features.
    Returns (epic_id, has_initial_build, list_of_feature_titles).
    """
    epic_id = ado.find_work_item("Epic", epic_name)
    if not epic_id:
        print(f"  Note: Epic '{epic_name}' not found in ADO — will be created fresh.")
        return None, False, []

    features = ado.get_child_features(epic_id)
    titles = [f["fields"]["System.Title"] for f in features]
    has_initial_build = any(t.lower() == "initial build" for t in titles)
    if titles:
        print(f"  Found Epic #{epic_id} with {len(titles)} feature(s): {', '.join(titles)}")
    else:
        print(f"  Found Epic #{epic_id} — no features yet.")
    return epic_id, has_initial_build, titles


def run_text_input_flow(ado: ADOClient, dry_run: bool, discovery: bool) -> None:
    """Accept pasted project request text and build either a discovery or development scaffold."""
    mode_label = "discovery scaffold" if discovery else "development scaffold"
    print("\n  Paste or type your project request below.")
    print(
        "  When done, press Enter on a blank line then EOF"
        " (Ctrl+D on Mac/Linux, Ctrl+Z on Windows).\n"
    )

    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    text = "\n".join(lines).strip()
    if not text:
        print("  No input received — cancelled.")
        return

    epic_name = _prompt_epic_name()
    if not epic_name:
        return

    has_initial_build = False
    existing_features: list[str] = []
    if not discovery:
        _, has_initial_build, existing_features = _query_epic_features(ado, epic_name)

    print(f"\n  Generating {mode_label}...\n", flush=True)
    try:
        if discovery:
            result = build_scaffold(
                text, epic_name=epic_name, source_label="pasted project request"
            )
        else:
            result = build_from_documents(
                text, ["pasted text"],
                epic_name=epic_name,
                has_initial_build=has_initial_build,
                existing_features=existing_features,
            )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"  AI error: {exc}")
        return

    _confirm_and_execute(ado, result, dry_run, mode_label=mode_label)


# ── Zip / Document Flow ────────────────────────────────────────────────────────

def run_doc_flow(ado: ADOClient, doc_path: str, dry_run: bool, discovery: bool) -> None:
    """Extract documents from a file or folder, call Claude, then execute."""
    mode_label = "discovery scaffold" if discovery else "development scaffold"
    print(f"\n  Reading document(s) from: {doc_path}", flush=True)
    try:
        doc_text, file_names = ingest(doc_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"  Error: {exc}")
        return

    print(f"  Parsed {len(file_names)} file(s): {', '.join(file_names)}")

    epic_name = _prompt_epic_name()
    if not epic_name:
        return

    has_initial_build = False
    existing_features: list[str] = []
    if not discovery:
        _, has_initial_build, existing_features = _query_epic_features(ado, epic_name)

    print(f"  Generating {mode_label}...\n", flush=True)

    try:
        if discovery:
            result = build_scaffold(
                doc_text, epic_name=epic_name, source_label=", ".join(file_names)
            )
        else:
            result = build_from_documents(
                doc_text, file_names,
                epic_name=epic_name,
                has_initial_build=has_initial_build,
                existing_features=existing_features,
            )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"  AI error: {exc}")
        return

    _confirm_and_execute(ado, result, dry_run, mode_label=mode_label, source=", ".join(file_names))




# ── Plan Execution Flow ────────────────────────────────────────────────────────

def run_plan_flow(ado: ADOClient, plan_path: str, dry_run: bool) -> None:
    """Load a saved plan JSON and execute it — no AI call required."""
    if not os.path.exists(plan_path):
        print(f"  Plan file not found: {plan_path}")
        return

    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)

    ops     = plan.get("operations", [])
    summary = plan.get("summary", "")
    source  = plan.get("source", "")
    ts      = plan.get("generated_at", "")

    if not ops:
        print("  Plan file contains no operations.")
        return

    print(f"  Plan: {source}  (generated {ts})")
    print(f"  {summary}\n")
    print(f"  Operations ({len(ops)} items):")
    print_proposed(ops)

    if dry_run:
        print("\n  [DRY RUN — previewing patches]\n")
        for op in ops:
            execute_operation(ado, op, dry_run=True)
        print()
        return

    prompt = f"\n  Execute {len(ops)} operation(s) in ADO?  [y / n / d (dry-run preview)]:  "
    print(prompt, end="", flush=True)
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"

    print()
    if answer == "y":
        _execute_ops(ado, ops)
    elif answer == "d":
        for op in ops:
            execute_operation(ado, op, dry_run=True)
    else:
        print("  Cancelled.")
    print()


# ── Entry Point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate ADO flow."""
    parser = argparse.ArgumentParser(
        description="Create or update ADO work items from plain-English descriptions."
    )
    parser.add_argument("--dry-run",              action="store_true",
                        help="Preview operations; make no changes.")
    parser.add_argument("--refresh",              action="store_true",
                        help="Force-reload the ADO context cache.")
    parser.add_argument("--discovery-scaffold",   action="store_true",
                        help="Minimal scaffold: Epic + Discovery & Solution Design PBI + tasks.")
    parser.add_argument("--development-scaffold", action="store_true",
                        help="Full scaffold: Epic, all four Features, content-driven PBIs/tasks.")
    parser.add_argument("--source-info",          metavar="PATH",
                        help="Path to a PDF, DOCX, TXT, MD or XLSX file (or folder of files). "
                             "Used with either scaffold flag; "
                             "omit to paste text at the prompt instead.")
    parser.add_argument("--execute-plan",         metavar="PATH",
                        help=f"Execute a saved plan JSON directly without calling the AI. "
                             f"Defaults to {PLAN_FILE} if PATH is omitted.",
                        nargs="?", const=PLAN_FILE)
    args = parser.parse_args()

    if not args.execute_plan and not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    ado = ADOClient(org=ORG, project=PROJECT, pat=PAT)

    sep = "─" * 62
    print(f"\n  {sep}")
    print(f"  IA ADO Creator  ·  {ORG} / {PROJECT}")
    print(f"  Mode: {'DRY RUN (no changes will be made)' if args.dry_run else 'LIVE'}")
    print(f"  {sep}")
    print("  Loading project context...", flush=True)

    items = load_context(ado, force_refresh=args.refresh)

    if args.execute_plan:
        run_plan_flow(ado, args.execute_plan, dry_run=args.dry_run)
    elif args.discovery_scaffold:
        if args.source_info:
            run_doc_flow(ado, args.source_info, dry_run=args.dry_run, discovery=True)
        else:
            run_text_input_flow(ado, dry_run=args.dry_run, discovery=True)
    elif args.development_scaffold:
        if args.source_info:
            run_doc_flow(ado, args.source_info, dry_run=args.dry_run, discovery=False)
        else:
            run_text_input_flow(ado, dry_run=args.dry_run, discovery=False)
    else:
        repl(ado, dry_run=args.dry_run, items=items)


if __name__ == "__main__":
    main()
