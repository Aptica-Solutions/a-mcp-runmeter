# Engineer README

Shared AI rules, conventions, and guardrails for this project template.
Read by AI assistants as a detailed supplement to the root context files (CLAUDE.md, AGENTS.md, GEMINI.md).

---

# Repo Structure

```
repo-root/
├── CLAUDE.md                       Claude Code context (auto-loaded)
├── AGENTS.md                       Codex CLI context (auto-loaded)
├── GEMINI.md                       Gemini CLI context (auto-loaded)
├── AI-TASKS.md                     Active project task list
├── ONBOARDING.md                       Completed project survey (written by /project-init)
├── REQUIREMENTS.md                 Project requirements (written from template)
├── CONTEXT.md                      Session handoff — gitignored, not source
├── README.md                       Project readme
│
├── docs/                           Human-facing solution documents
│   └── *.template.md               Fill-in templates for each audience
│
├── _engineer/                      AI context, tooling, and meta-layer
│   ├── ENGINEER-README.md          This file — shared AI rules and conventions
│   ├── ENGINEER-FLOW.md            Engineer lifecycle checklist
│   ├── ENGINEER-TASKS.md           Template development task tracking
│   ├── ONBOARDING.template.md          Survey template (filled → ONBOARDING.md)
│   ├── REQUIREMENTS.template.md    Requirements template (filled → REQUIREMENTS.md)
│   ├── BRANCHING.md                Branch naming and workflow guide (template only)
│   ├── ado-sync/                   ADO sync utilities and publishing scripts
│   ├── hipaa-sanitize/             HIPAA redaction utility
│   ├── test-case-automation/       Test case scaffolding scripts
│   │   └── new-test-case.ps1       Scaffold script — creates test + log dirs
│   ├── dev-env/                    Dev machine profiles, init scripts, and tooling
│   │   ├── init-repo-tooling.ps1   Cross-platform tooling setup and verification
│   │   ├── template-sync.ps1       PowerShell compatibility wrapper
│   │   ├── template_sync.py        CodeQL-scannable template sync engine
│   │   └── log_util.py             Structured JSON logger — import in all Python scripts
│   └── workbench/                  Scratch space — not deployed, not reviewed
│
├── .claude/                        Claude Code project settings
│   ├── settings.json               Permissions, hooks
│   ├── commands/                   Slash commands (/project-init, /handoff)
│   └── hooks/                      UserPromptSubmit hooks (onboarding gate)
├── .github/
│   ├── copilot-instructions.md     GitHub Copilot context
│   ├── dependabot.yml              Dependency update configuration
│   ├── CODEOWNERS                  Required reviewers for sensitive paths
│   └── workflows/secret-scan.yml  CI — gitleaks on push and PR
├── .gemini/settings.json           Gemini CLI project config + MCP
├── .vscode/mcp.json                VS Code / Copilot MCP servers
├── .mcp.json                       Claude Code MCP servers
├── codex.json                      Codex project config + MCP
├── .pre-commit-config.yaml         Pre-commit hooks (gitleaks on every commit)
│
├── backend/                        API, services, routes, middleware
├── frontend/                       UI application
├── infra-setup/                    Azure Bicep templates — main.bicep orchestrates; individual templates are modules
├── tests/
│   ├── fixture-library/            Shared fixtures — never real user data
│   ├── test-case-1/                Sample input/output test case
│   │   ├── in/                     Raw inputs for this scenario
│   │   └── out/                    Expected outputs (locked reference)
│   └── new-test-case.ps1           Scaffold script — creates test + log dirs
├── logs/                           Runtime logs — *.log gitignored, *.md markers tracked
│   ├── dev-testing/                Log output during active development
│   └── test-case-1/                Log output when running test-case-1 scenarios
└── publish/dist/                   Build output — gitignored
```

---

# ONBOARDING GATE — NON NEGOTIABLE

## Canonical template repository exception

Before applying this gate, determine whether the current checkout is the canonical
template source. Both conditions must be true:

1. `.is-template-repo` exists in the repository root.
2. `git remote get-url origin` identifies `Aptica-Solutions/a-repo-template` or
   the legacy `szeltneraptica/repo-template` GitHub repository.

This read-only check is permitted before onboarding. If both conditions are true,
the onboarding gate and the requirement to read `AI-TASKS.md` do not apply;
template review, maintenance, and validation may proceed without project onboarding
artifacts. Never rely on the marker alone because GitHub copies it into newly
created repositories until initialization removes it.

**Do not write code, create files, plan architecture, run scripts, or make any project decisions until `ONBOARDING.md` exists in the project root and the user has confirmed it is accurate.**

If `ONBOARDING.md` is missing or empty:
> "ONBOARDING.md not found. I cannot begin any project work until the survey is complete. Run `/project-init` (Claude) or walk through `_engineer/ONBOARDING.template.md` and save the answers to `ONBOARDING.md`."

If `ONBOARDING.md` exists but has not been confirmed this session, ask once:
> "Is ONBOARDING.md current and accurate? (yes to confirm / describe what changed)"

Answering questions about the template itself is permitted. All project-specific work is blocked until confirmed.

---

# Guardrails — NON NEGOTIABLE

**Secrets Management**
- All secrets, tokens, and credentials are stored in Key Vault or injected via environment variables at runtime
- Never hardcode credentials, connection strings, API keys, or tokens
- `.env` files are gitignored — never committed
- Use `op run -- <command>` (1Password CLI) to inject secrets locally if available
- CI/CD reads secrets from Key Vault or GitHub Secrets — never from source

**Dependency Security**
- Dependencies are pinned to specific versions
- Dependabot is enabled for automated vulnerability alerts
- `npm audit` / `pip-audit` run in CI on every PR
- Do not generate cryptographic primitives — use established libraries

**Secret Scanning**
- Gitleaks runs on every commit (pre-commit hook) and every push/PR (CI)
- If a secret is detected: rotate it immediately, then remediate the commit history
- Flag any file containing what looks like a credential before proceeding

**Compliance**
- Never include PHI, PII, or real user data in code, logs, tests, or fixtures

---

# Conditional Task Filtering

When generating `AI-TASKS.md` from `AI-TASKS.example.md` and `ONBOARDING.md`, **only include conditional blocks whose survey condition is met**. Delete block markers and their entire content if the condition is not met. Do not leave commented-out tasks or placeholder sections.

| Block tag | Include if ONBOARDING answer |
|-----------|--------------------------|
| `IF:oauth` | "Auth Requirements" = Entra / OAuth |
| `IF:frontend` | "Project Type" = Frontend or Full Stack |
| `IF:application-insights` | "Log Destination" = Application Insights |
| `IF:azure-infra` | "Cloud" = Azure |
| `IF:hipaa` | "Compliance" includes HIPAA |
| `IF:soc2` | "Compliance" includes SOC 2 |
| `IF:pci` | "Compliance" includes PCI DSS |
| `IF:ado-sync` | User explicitly wants Azure DevOps integration |

Apply the same logic when filling in `REQUIREMENTS.template.md` and `docs/*.template.md` — delete sections marked `*(Include if: condition. Delete if not applicable.)*` when the condition is not met.

---

# Core AI Coding Rules

- `AI-TASKS.md` is the canonical task list — always read it before starting work
- Work one task at a time; each task = one coding step, not a feature
- Mark tasks `[x] (YYYY-MM-DD)` when done; add newly discovered work as new tasks
- All terminal commands must be written in PowerShell (`pwsh`)
- Database schema changes must produce a migration file for subsequent execution
- When a pattern is replaced, clean up all references to the old pattern

## Task Tracking

| Marker | ADO Feature |
|--------|-------------|
| `[PBI:enhancement]` | Enhancements & New Capabilities |
| `[PBI:defect]` | Defects & Production Issues |
| `[PBI:tech-debt]` | Tech Debt & Refactoring |
| `[PBI:runbook]` | Runbooks, Monitoring & Operations |

Status: `[ ]` todo · `[~]` in progress · `[x]` done `(YYYY-MM-DD)`

Follow `_engineer/ENGINEER-FLOW.md` for the full lifecycle checklist.

---

# Logging

## Directory Structure

```
logs/
├── dev-testing/      ← active development; one rolling log file, overwrite freely
└── test-case-<N>/    ← one directory per test case; mirrors tests/test-case-<N>/
```

Each subdirectory contains a `*.md` marker that is tracked in git. Log files (`*.log`) are gitignored.

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `LOG_LEVEL` | `debug \| info \| warn \| error` | `info` |
| `LOG_FILE` | Full path to the active log file | `./logs/dev-testing/dev.log` |
| `TEST_CASE_LOG_DIR` | Base directory; test runners append `/<name>/run.log` | `./logs` |

Switch `LOG_FILE` to `./logs/test-case-<N>/run.log` when running a specific test case scenario. Switch back to `./logs/dev-testing/dev.log` for development iteration.

## Python Logging Utility

`_engineer/dev-env/log_util.py` provides a structured JSON logger backed by `python-json-logger`. It reads `LOG_LEVEL` and `LOG_FILE` from the environment and attaches both a console and file handler automatically.

Because `dev-env/` contains a hyphen, use `sys.path` rather than dotted imports:

```python
import sys
from pathlib import Path
# For scripts in _engineer/<subdir>/ (e.g. ado-sync/, hipaa-sanitize/):
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dev-env"))
from log_util import get_logger

log = get_logger(__name__)
log.info("Processing file", extra={"file": path, "correlation_id": cid})
```

Scripts that already live in `dev-env/` can import directly: `from log_util import get_logger`.
Scripts in the repo root use `parent / "_engineer/dev-env"` instead of `parent.parent / "dev-env"`.

`python-json-logger` is listed in `requirements.txt` and is verified by `init-repo-tooling.ps1`. If it is not installed, `log_util.py` falls back to plain-text output with a warning.

## Node.js / TypeScript Logging

Use `winston` with a JSON transport. Configure it to read `LOG_LEVEL` and write to `LOG_FILE` from `process.env`. Correlation IDs must propagate through the full request chain via a middleware-set header (`X-Correlation-Id`).

---

# Test Cases

## Structure

Each test case lives under `tests/` and has a paired log directory under `logs/`:

```
tests/test-case-<N>/
├── in/                         Raw input files for this scenario
├── out/                        Expected output files (committed reference)
└── (unit test files)

logs/test-case-<N>/
└── run.log                     Gitignored; written during scenario execution
```

Shared fixtures used across multiple test cases belong in `tests/fixture-library/`.

## Adding a New Test Case

Run the scaffold script — it creates the full directory structure and prints the `.env` lines to add:

```powershell
pwsh -NoProfile -File tests/new-test-case.ps1 -Name 2
pwsh -NoProfile -File tests/new-test-case.ps1 -Name "invoice-edge-case"
```

The script creates:
- `tests/test-case-<N>/in/` and `out/` with marker files
- `logs/test-case-<N>/` with a marker file
- Prints the `.env.example` lines to add manually

## Running a Test Case

Set `LOG_FILE` to the test case log path before running:

```powershell
$env:LOG_FILE = "./logs/test-case-1/run.log"
$env:PDF_INPUT_PATH = "./tests/test-case-1/in/sample.pdf"
$env:OUTPUT_DIR = "./tests/test-case-1/out"
pwsh -NoProfile -Command "python your_script.py"
```

---

# Backend Conventions (Node.js/TypeScript)

- Config from environment variables — never hardcoded
- Correlation IDs must propagate through the full request chain
- Structured JSON logging; log level controlled via `LOG_LEVEL` env var
- HTTP request/response logging filtered under DEBUG level
- Business logic in `services/` — never in routes or components
- Routes handle HTTP only; validation in `middleware/`

# Frontend Conventions

- Settings page required — backed by a config file for defaults
- UI must be responsive and WCAG 2.1 compliant
- Background tasks must show progress and allow cancellation — UI never appears frozen
- No technology brand names visible in the UI ("cloud storage", not "Azure Blob")

---

# Infrastructure Conventions (Azure Bicep)

- All Bicep deployments use **subscription scope** (`targetScope = 'subscription'`) via `main.bicep` — never require the caller to pre-create a resource group
- `main.bicep` creates the resource group as a resource and calls individual templates as modules; individual templates remain standalone for targeted redeployment
- **Deploy command:** `az deployment sub create --location <region> --template-file infra-setup/main.bicep --parameters infra-setup/main.bicepparam`
- **Targeted redeployment** (single resource only): use `az deployment group create` with the individual template; resource group must already exist
- Wire cross-module values from module outputs (e.g. Document Intelligence endpoint → App Service) — never duplicate endpoint URLs across param files
- Use `dependsOn` explicitly when a module references a sibling by name string rather than resource reference
- All resources must carry the standard tag set: `project`, `managedBy: 'bicep'`, `environment`, `component`
- Never commit secrets to param files — use Key Vault references in App Settings; `adminObjectId` and `spObjectId` are the only identity values that belong in param files
- Validate every template before committing: `az bicep build --file <template> --outfile /tmp/check.json`
- `pwsh -NoProfile -Command` strings must use **single quotes** on macOS/Linux to prevent the outer shell from expanding PowerShell `$` variables
- All templates must be **idempotent** — re-running a deployment must succeed without errors:
  - Role assignments: use `guid(resourceId, principalId, roleId)` for deterministic, idempotent names
  - Key Vault access policies: use the `add` action (merges existing policies, does not replace)
  - **Soft-delete caveat**: Cognitive Services (Document Intelligence, Azure OpenAI) and Key Vault have soft-delete enabled by default. Re-deploying a resource with the same name after deletion fails until the deleted resource is purged. Each template header must document the purge command:
    - Cognitive Services: `az cognitiveservices account purge --location <region> --resource-group <rg> --name <name>`
    - Key Vault: `az keyvault purge --name <name>`
  - Never set `enablePurgeProtection: true` unless required for compliance — it permanently prevents purging and breaks idempotent redeployment

---

# Session Management

## Session Start

Check `CONTEXT.md` at session start. If non-empty, read the handoff note and acknowledge it before doing any other work.

## Session Reset Threshold

After **20 user-AI exchanges**, proactively suggest:
> "This session is getting long. Run `/handoff` before `/clear` to preserve context."

Run `/handoff` before every `/clear`. It writes a structured note to `CONTEXT.md` and prompts for `/clear`.

Do not commit `CONTEXT.md` — it is session state, not source.

## Cost Management

- If a request is too vague to act on efficiently, ask for specifics rather than running broad searches
- A new task should be a fresh session; if context is missing, read `CONTEXT.md` first
- Remind the user to name specific files and sources to reduce tool calls

---

# Template Sync

Use `_engineer/dev-env/template-sync.ps1` to pull DISTRIBUTABLE improvements
from a versioned template release into a project repo. The PowerShell entry
point is a thin compatibility wrapper around the standard-library Python engine
in `_engineer/dev-env/template_sync.py`. The Python engine is cross-platform and
covered by CodeQL; it reads `.templatefiles` and `.template-policy.json` from
the requested template ref. Both interfaces default to a read-only dry run.

```powershell
git remote add template https://github.com/Aptica-Solutions/a-repo-template.git  # once
git fetch --tags template
git checkout -b chore/template-sync
pwsh -NoProfile -File _engineer/dev-env/template-sync.ps1 `
  -TemplateRef template-v2026.07.1 `
  -Profile standard
pwsh -NoProfile -File _engineer/dev-env/template-sync.ps1 `
  -TemplateRef template-v2026.07.1 `
  -Profile standard `
  -Apply
git add -A
git commit -m "chore: sync template improvements"
# open PR → develop
```

The first adoption of a repository with pre-existing template files may report
`No baseline`. Review those files, then add `-AcceptExistingAsBaseline` to the
apply command. During bootstrap, the engine checks each existing blob against
the selected template release's history:

- an exact historical template version is safely upgraded to the release;
- content that never appeared in template history is preserved as a downstream
  customization; and
- seed-policy files are always preserved when they already exist.

The engine also removes a copied `.is-template-repo` marker from downstream
repositories. Canonical-template status always requires both the marker and the
canonical GitHub `origin`.

The generated `.aptica/template-lock.json` records the applied template commit,
profile, and per-file template blobs. Later runs use that baseline to:

- update files unchanged by the downstream repository;
- preserve downstream-only changes and seed files;
- three-way merge non-overlapping edits;
- stop on overlapping edits or unsafe deletions; and
- advance the lock only after a conflict-free apply.

Commit synchronized files and the lock together. `.TODO-` prefixed files remain
manual-adoption assets and are skipped automatically.

---

# ADO Sync Toolkit

Use the ADO sync toolkit in `_engineer/ado-sync/` to publish plans and progress to Azure DevOps.

- Primary script: `_engineer/ado-sync/ai_ado_creator.py`
- Repo sync script: `_engineer/ado-sync/ado_repo_sync.py`

Required env vars: `ADO_ORG`, `ADO_PROJECT`, `ADO_API_VERSION`, `ADO_PAT`, `ADO_PROJECT_GUID`, `ADO_PLAN_DIR`, `ADO_CONTEXT_CACHE_PATH`, `ANTHROPIC_API_KEY`

Generated artifacts — do not commit:
- `_engineer/ado-sync/.ado_context_cache.json`
- `_engineer/ado-sync/plans/`

**Publish tasks to ADO:**
```powershell
pwsh -NoProfile -Command "python ./_engineer/ado-sync/ai_ado_creator.py"
```

---

# HIPAA Sanitize Toolkit

Use the HIPAA sanitize toolkit in `_engineer/hipaa-sanitize/` to de-identify discharge summary PDFs before using them as test fixtures or sharing them outside a HIPAA-covered environment.

- Script: `_engineer/hipaa-sanitize/hipaa_redact.py`
- Handles both text-based and scanned (image-based) PDFs via OCR
- Applies HIPAA Safe Harbor rules: shifts dates by a random offset, redacts names, MRNs, phone numbers, addresses, and other PHI patterns

**Dependencies** (install once into the project venv):
```powershell
pip install pdfplumber reportlab pikepdf pytesseract pdf2image
# macOS: brew install tesseract poppler
# Linux: sudo apt install tesseract-ocr poppler-utils
```

**Basic usage — auto date offset, regex patterns only:**
```powershell
pwsh -NoProfile -Command "python ./_engineer/hipaa-sanitize/hipaa_redact.py report.pdf"
# saves report_REDACTED.pdf alongside the source
```

**With known names, facilities, and a fixed offset:**
```powershell
pwsh -NoProfile -Command "python ./_engineer/hipaa-sanitize/hipaa_redact.py `
    report.pdf redacted.pdf `
    --offset-days 45 `
    --names 'Jane Smith' 'Dr. David Cho' `
    --facilities 'Morristown Medical Center'"
```

**Via the PowerShell ultra-profile wrapper** (if `functions.ps1` is loaded):
```powershell
Invoke-HipaaRedact -InputPdf report.pdf -OffsetDays 45 `
    -Names 'Jane Smith','Dr. David Cho' `
    -Facilities 'Morristown Medical Center'
```

> **Always manually review the redacted output** — automated redaction is never 100% complete. This tool is a starting point, not a substitute for legal or compliance review. Never commit original (un-redacted) PDFs containing PHI.

---

# Session Checkpoint (end of each PBI)

When all tasks in a PBI are committed and AI-TASKS.md is updated, signal:

```
SESSION CHECKPOINT
Completed: [summary]
Next: [what comes next]
Safe to start a fresh session.
```

Then ask the user if they want to push to ADO. If yes, run the publish command above.

---

# Governance Reference

Use `docs/GOVERNANCE.template.md` when asked to produce a governance document.

**Data Classification**

| Classification | Examples | Handling |
|---------------|----------|---------|
| Public | Marketing copy, docs | No restrictions |
| Internal | Business logic, configs | Restrict external sharing |
| Confidential | PII, financial data | Encrypt at rest and in transit |
| Restricted / PHI | Health records | HIPAA controls, audit logging required |

**Audit Logging** — all sensitive operations must log:
- Timestamp (UTC), Actor (user ID or service principal), Action, Resource affected, Outcome

Compliance sections (HIPAA, SOC 2, PCI DSS) are conditional — only include in docs when relevant per ONBOARDING.

---

# Solution Documentation

Produce these documents from templates in `docs/` when requested:

| Template | Audience |
|----------|----------|
| `DEMO.template.md` | Stakeholders |
| `DEVELOPER.template.md` | Engineers |
| `ENGINEER.template.md` | DevOps / Support |
| `GOVERNANCE.template.md` | Compliance |
| `INFRA.template.md` | Platform |
| `LEADERSHIP.template.md` | Executive Leadership |
| `QA.template.md` | QA |
| `SYSADMIN.template.md` | SysAdmin |

After adding a doc, update `docs/DOC-TOC.md` with a one-line description.
