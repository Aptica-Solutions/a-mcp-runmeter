# ADO Sync Toolkit

Tools for creating and synchronising Azure DevOps work items from plain-English descriptions, project documents, and git repository evidence.

---

## Files

| File | Role |
|------|------|
| `ai_ado_creator.py` | Create and update work items interactively or from documents |
| `ado_repo_sync.py` | Sync completed git work back to existing ADO items |
| `ado_lib.py` | Shared library — ADO client, AI interpreters, field formatter, doc ingester |

`ai_ado_creator.py` and `ado_repo_sync.py` both import from `ado_lib.py`. You do not call `ado_lib.py` directly.

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `ADO_ORG` | Azure DevOps organisation name (e.g. ``your-org`) |
| `ADO_PROJECT` | ADO project name |
| `ADO_PAT` | Personal Access Token with Work Items read/write scope |
| `ANTHROPIC_API_KEY` | API key for Claude (not needed for `--execute-plan`) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `ADO_API_VERSION` | `7.1` | ADO REST API version |
| `ADO_PROJECT_GUID` | — | Project GUID used in parent-link URLs (needed for cross-project links) |
| `ADO_CONTEXT_CACHE_PATH` | `<script-dir>/.ado_context_cache.json` | Path to the context cache file |
| `ADO_PLAN_DIR` | `./_engineer/ado-sync/plans` | Directory where plan JSON files are saved |

Set these in `.env` or inject via `op run --` (1Password CLI). Never commit `.env`.

---

## ai_ado_creator.py

Creates and updates ADO work items. Three entry points: interactive REPL, scaffold generation, and plan execution.

### Interactive REPL (default)

```powershell
python ./_engineer/ado-sync/ai_ado_creator.py
```

Type plain-English progress updates at the prompt:

```
> We finished the API integration for PROJ-001 and are now working on error handling.
> Need a new PBI under the error handling feature for timeout retries.
> PROJ-003 is blocked waiting on Epic sign-off.
```

Claude interprets the input against the live ADO hierarchy and proposes operations. You confirm (`y`), preview (`d`), or cancel (`n`).

**REPL commands:**

| Command | Effect |
|---------|--------|
| `dry-run` | Toggle dry-run mode on/off |
| `refresh` | Force-reload the ADO context cache |
| `quit` | Exit |

### Scaffold Modes

Generate a full work item hierarchy from a project request or document.

**Discovery scaffold** — minimal: Epic + Discovery Feature + one PBI + 5–7 tasks:

```powershell
# Paste text at the prompt
python ./_engineer/ado-sync/ai_ado_creator.py --discovery-scaffold

# From a file or folder
python ./_engineer/ado-sync/ai_ado_creator.py --discovery-scaffold --source-info path/to/brief.docx
```

**Development scaffold** — full hierarchy: Epic, four standard Features (Initial Build / Enhancements / Defects / Tech Debt / Runbooks), content-driven PBIs and tasks:

```powershell
# Paste text at the prompt
python ./_engineer/ado-sync/ai_ado_creator.py --development-scaffold

# From a file or folder of documents
python ./_engineer/ado-sync/ai_ado_creator.py --development-scaffold --source-info docs/requirements/
```

**Supported document types:** `.pdf`, `.docx`, `.txt`, `.md`, `.xlsx`

After generation, you are shown a numbered list of proposed operations and prompted to confirm before anything is written to ADO. The plan is always saved to `ADO_PLAN_DIR` before execution.

### Plan Execution

Every scaffold run and confirmation step saves a plan JSON to `ADO_PLAN_DIR`. You can review and edit this file, then execute it without a second AI call:

```powershell
python ./_engineer/ado-sync/ai_ado_creator.py --execute-plan path/to/ado-plan-20260508-120000.json
```

Omit the path to execute the most recent plan (`ado_last_plan.json`):

```powershell
python ./_engineer/ado-sync/ai_ado_creator.py --execute-plan
```

This is the safe review-then-apply workflow: generate → inspect JSON → execute.

### Global Flags

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview all operations; make no changes to ADO |
| `--refresh` | Force-reload the ADO context cache before running |

---

## ado_repo_sync.py

Reads git evidence from a repository, loads an ADO work item subtree, asks Claude to map completed work to existing items, and proposes state/tag updates. **Does not create new work items** — updates only.

### Dry-run (default)

```powershell
python ./_engineer/ado-sync/ado_repo_sync.py --repo . --parent-id 2505
```

Collects repo evidence, calls Claude, saves a plan JSON, and previews the proposed patches. Nothing is written to ADO.

### Apply

```powershell
python ./_engineer/ado-sync/ado_repo_sync.py --repo . --parent-id 2505 --apply
```

Executes the generated plan immediately after previewing.

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--repo` | No (default: `.`) | Path to the source git repository |
| `--parent-id` | Yes | ADO work item ID at the root of the subtree to update |
| `--base-ref` | No | Git ref to diff against (e.g. `origin/main`, `HEAD~5`). When omitted, all tracked files are listed instead. |
| `--max-commits` | No (default: `30`) | Number of recent commits to include in evidence |
| `--model` | No (default: `claude-sonnet-4-6`) | Anthropic model to use |
| `--apply` | No | Execute updates; default is preview only |

### What it reads

- `git log`, `git status`, `git diff --stat`, `git ls-files` (or changed files since `--base-ref`)
- `AI-TASKS.md`, `REQUIREMENTS.md`, `README.md`, `CLAUDE.md` if present

---

## Context Cache

`ai_ado_creator.py` caches the full ADO project hierarchy to avoid repeated API calls. The cache expires after 10 minutes.

- Default location: `<script-dir>/.ado_context_cache.json`
- Override: set `ADO_CONTEXT_CACHE_PATH`
- Force refresh: pass `--refresh` or type `refresh` at the REPL prompt

Do not commit `.ado_context_cache.json`.

---

## Plan Files

Both tools save generated plans as timestamped JSON files:

```
ADO_PLAN_DIR/
  ado-plan-20260508-120000.json          # from ai_ado_creator scaffolds
  ado-repo-sync-2505-20260508-130000.json  # from ado_repo_sync
```

Plan file structure:

```json
{
  "generated_at": "2026-05-08T12:00:00",
  "source": "discovery scaffold",
  "summary": "Create Epic and discovery scaffold for PROJ-007",
  "operations": [
    {
      "action": "create",
      "work_item_type": "Epic",
      "title": "PROJ-007 – Inpatient Discharge Summarization",
      "state": "To Do"
    }
  ]
}
```

Do not commit files under `ADO_PLAN_DIR`.

---

## Profile Function Shortcuts

If the PowerShell ultra-profile is loaded (`_engineer/dev-env/functions.ps1`), these wrappers are available:

```powershell
# Interactive REPL — defaults to current directory as repo root
Invoke-AdoCreator

# Specify a different repo
Invoke-AdoCreator -Repo C:\repos\other-project

# Repo sync — dry run
Invoke-AdoRepoSync -ParentId 2505

# Repo sync — apply
Invoke-AdoRepoSync -ParentId 2505 -Apply
```

`Invoke-AdoCreator` wraps `ai_ado_creator.py` in interactive mode.
`Invoke-AdoRepoSync` wraps `ado_repo_sync.py` and auto-discovers the script path from the local repo or central automation repo.

---

## Typical Workflows

### Start a new project

```powershell
# 1. Generate discovery scaffold from a brief
python ./_engineer/ado-sync/ai_ado_creator.py --discovery-scaffold --source-info docs/project-brief.docx

# 2. Review the saved plan JSON, edit if needed
# 3. Execute
python ./_engineer/ado-sync/ai_ado_creator.py --execute-plan
```

### Promote to development scaffold after discovery sign-off

```powershell
python ./_engineer/ado-sync/ai_ado_creator.py --development-scaffold --source-info docs/requirements/
```

### Update work items after completing a sprint

```powershell
# Dry-run first to review
python ./_engineer/ado-sync/ado_repo_sync.py --repo . --parent-id 2505 --base-ref origin/main

# Apply when satisfied
python ./_engineer/ado-sync/ado_repo_sync.py --repo . --parent-id 2505 --base-ref origin/main --apply
```

### Post plain-English progress notes

```powershell
python ./_engineer/ado-sync/ai_ado_creator.py
> Finished the symbol normalisation work under PROJ-001, now working on unit tests.
```
