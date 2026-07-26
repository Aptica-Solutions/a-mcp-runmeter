# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ONBOARDING GATE — Read This First

### Canonical template repository exception

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

**Do not write code, create files, plan architecture, run scripts, or make any project decisions until `ONBOARDING.md` exists in the project root and the user has confirmed it is accurate in this session.**

If `ONBOARDING.md` is missing or empty:
> "ONBOARDING.md not found. I cannot begin any project work until the survey is complete. Please run `/project-init`."

If `ONBOARDING.md` exists but has not been confirmed this session, ask once:
> "Is ONBOARDING.md current and accurate for this project? (yes to confirm / describe what changed)"

The gate applies to all work — coding, planning, infra, documentation, and task creation. Answering questions about the template itself is permitted.

A `UserPromptSubmit` hook in `.claude/settings.json` enforces this automatically on every prompt.

---

## What This Repo Is

This is an enterprise **project template** — a scaffold for Azure-based solutions. `backend/` and `frontend/` are empty stubs. Fill in the actual solution; treat everything in `_engineer/` as the engineering meta-layer (AI context, task tracking, ADO sync, dev tooling).

---

## Setup

```powershell
pwsh -NoProfile -File "_engineer/dev-env/init-repo-tooling.ps1"
```

Works on macOS and Windows. Then activate the venv and configure credentials:

```powershell
# macOS
source .venv/bin/activate

# Windows
.\.venv\Scripts\Activate.ps1

cp .env.example .env  # fill in Azure credentials
```

All terminal commands must be written in **PowerShell** (`pwsh`), not bash/zsh.

---

## Repo Layout

| Path | Purpose |
|------|---------|
| `_engineer/` | Engineering meta-layer — entry point: `ENGINEER-README.md` |
| `_engineer/ado-sync/` | ADO sync utilities — publish tasks to Azure DevOps |
| `_engineer/dev-env/` | Cross-platform PowerShell profile and launcher scripts |
| `_engineer/hipaa-sanitize/` | HIPAA redaction utility |
| `_engineer/dev-env/log_util.py` | Structured JSON logging utility — import in all Python scripts |
| `_engineer/workbench/` | Scratch space — not deployed, not reviewed |
| `docs/` | Human-facing docs (use `*.template.md` files as source) |
| `infra-setup/` | Azure Bicep templates — `main.bicep` orchestrates all resources |
| `requirements.txt` | Python dependencies — includes `python-json-logger` |
| `tests/fixture-library/` | Shared fixtures — never real user data |
| `tests/test-case-N/` | Scenario test cases; run `tests/new-test-case.ps1` to scaffold |
| `logs/dev-testing/` | Log output during active development (`LOG_FILE=./logs/dev-testing/dev.log`) |
| `logs/test-case-N/` | Log output per scenario run (`LOG_FILE=./logs/test-case-N/run.log`) |
| `publish/dist/` | Build output — gitignored |

---

## Session Handoff

Run `/handoff` before every `/clear`. It writes a structured note to `CONTEXT.md` covering what was done, what's in progress, decisions made, and the exact next step. The next session reads this file at start.

**Turn threshold:** after 20 exchanges, Claude will proactively suggest `/handoff`.
**Session start:** if `CONTEXT.md` is non-empty, Claude reads it and acknowledges prior context before doing anything else.

Do not commit `CONTEXT.md` — it is session state.

---

## Memory

Memory lives at `~/.claude/projects/<encoded-path>/memory/`.

**Save:** role/expertise, confirmed non-obvious approaches, project decisions, external resource locations.
**Do not save:** code patterns (read the code), ephemeral task state (use AI-TASKS.md), git history.

---

## AI Modes

Switch explicitly — paste the relevant snippet into the chat.

**Planning:** *Do not write code. Review REQUIREMENTS.md and AI-TASKS.md, refine and prioritize tasks only.*
**Coding:** *Work on one task at a time. Return complete file contents.*
**Debug:** *Do not change architecture. Fix only the reported issue.*

---

## Subagent Usage

- `Explore` — broad codebase research spanning multiple files
- `Plan` — architecture and implementation planning before non-trivial work
- `general-purpose` — research that should not pollute main context
- Run independent agents in parallel; do not duplicate subagent work

---

## Initialization

To start a new project from this template, run the `/project-init` slash command. It walks through:
1. Loading and confirming all rules
2. An interactive survey (writes `ONBOARDING.md`)
3. Tooling setup (gitleaks, venv, deps)
4. Environment verification and handoff to Plan mode

Underlying scripts (also callable standalone):
- `pwsh -NoProfile -File "_engineer/dev-env/init-repo-tooling.ps1"` — cross-platform tooling setup + verification (macOS and Windows)

---

## Engineer Flow

Follow `_engineer/ENGINEER-FLOW.md` strictly. The required sequence:

1. Complete `ONBOARDING.md` and `REQUIREMENTS.md` (do not write code before this)
2. Enter Plan mode — confirm AI understands ONBOARDING, guardrails, and REQUIREMENTS
3. Build `AI-TASKS.md` from approved plan
4. Switch to Code mode, work one task at a time
5. Write tests at end of each PBI (80%+ coverage target)

**Do not start coding without explicit user confirmation that ONBOARDING is complete and accurate.**

---

## Task Tracking

Tasks live in `AI-TASKS.md`.

```
[ ]  todo
[~]  in progress
[x]  done (YYYY-MM-DD)
```

PBI type markers:

| Marker | ADO Feature |
|--------|-------------|
| `[PBI:enhancement]` | Enhancements & New Capabilities |
| `[PBI:defect]` | Defects & Production Issues |
| `[PBI:tech-debt]` | Tech Debt & Refactoring |
| `[PBI:runbook]` | Runbooks, Monitoring & Operations |

---

## ADO Sync

Publish tasks to Azure DevOps after each PBI using the interactive creator:

```powershell
pwsh -NoProfile -Command "python ./_engineer/ado-sync/ai_ado_creator.py"
```

Sync completed repo work to existing ADO items:

```powershell
pwsh -NoProfile -Command "python ./_engineer/ado-sync/ado_repo_sync.py --repo . --parent-id <id> --apply"
```

Required env vars: `ADO_ORG`, `ADO_PROJECT`, `ADO_API_VERSION`, `ADO_PAT`, `ADO_PROJECT_GUID`, `ADO_PLAN_DIR`, `ADO_CONTEXT_CACHE_PATH`, `ANTHROPIC_API_KEY`.

Do not commit `.ado_context_cache.json` or files under `_engineer/ado-sync/plans/`.

---

## Secrets — Local vs Deployed

- Local: `cp .env.example .env` and fill in values, OR use `op run -- <command>` (1Password CLI) to inject at runtime
- Deployed: secrets come from Azure Key Vault — never from source
- `.env` is gitignored; `.env.example` documents all required keys
- Gitleaks runs on every push/PR via `.github/workflows/secret-scan.yml`

---

## Code Conventions

**Backend (Node.js/TypeScript)**
- Business logic in `services/` — never in routes or components
- Routes handle HTTP only; validation in `middleware/`
- Structured JSON logging with correlation IDs; log level controlled via `LOG_LEVEL` env var
- HTTP request/response logging filtered under DEBUG level

**Frontend**
- Settings page is required — backed by a config file for defaults
- UI must be responsive and WCAG 2.1 compliant
- Background tasks must show progress and allow cancellation — UI never appears frozen
- No technology brand names in UI ("cloud storage", not "Azure Blob")

**General**
- Config from environment variables — never hardcoded
- TypeScript strict mode
- Database schema changes must produce a migration file

**Infrastructure (Azure Bicep)**
- All Bicep deployments use **subscription scope** (`targetScope = 'subscription'`) via `main.bicep` — never require a pre-existing resource group
- `main.bicep` creates the resource group and calls individual resource templates as modules; individual templates remain standalone and reusable
- Deploy with: `az deployment sub create --location <region> --template-file infra/main.bicep --parameters infra/main.bicepparam`
- Individual templates (`keyvault.bicep`, `document-intelligence.bicep`, `app-service.bicep`) use resource-group scope and can be deployed independently when only one resource needs updating
- Wire cross-module values (e.g. Document Intelligence endpoint → App Service) from module outputs — never duplicate endpoint URLs across param files
- Use `dependsOn` explicitly when a module references another by name string rather than resource reference (e.g. Key Vault access policy added by App Service module)
- All resources must carry the standard tag set: `project`, `managedBy: 'bicep'`, `environment`, `component`
- Never commit secrets to param files — use Key Vault references (`@Microsoft.KeyVault(...)`) in App Settings and `adminObjectId`/`spObjectId` as the only identity values in param files
- Validate every template before committing: `az bicep build --file <template> --outfile /tmp/check.json`
- All templates must be **idempotent** — re-running a deployment must produce the same result without errors. Key rules:
  - Role assignments: use `guid(resourceId, principalId, roleId)` for deterministic names (already ARM-idempotent)
  - Key Vault access policies: use the `add` action (merges, not replaces — idempotent)
  - Cognitive Services (Document Intelligence, Azure OpenAI): soft-delete means a re-deploy after deletion fails until the resource is purged — document this in the template header and add the purge command as a comment: `az cognitiveservices account purge --location <region> --resource-group <rg> --name <name>`
  - Key Vault: same soft-delete behavior — purge with `az keyvault purge --name <name>` if a deleted vault blocks redeployment
  - Never set `enablePurgeProtection: true` on Key Vault unless required for compliance — it permanently prevents purging

---

## Commit Conventions

- Commit at PBI boundaries, not mid-task
- Format: `PBI N: short description` + blank line + why/detail
- Always include: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
- Never commit: `.env`, credentials, PHI, build artifacts, `_engineer/workbench/`

---

## Session Checkpoint

At the end of each PBI (all tasks committed, task file updated), signal:

```
SESSION CHECKPOINT
Completed: [summary]
Next: [what comes next]
Safe to start a fresh session.
```

Then ask the user if they want to push to ADO.

---

## Solution Documents

Use templates in `docs/` when asked to produce a solution document. After adding a doc, update `docs/DOC-TOC.md` with a one-line description.

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
