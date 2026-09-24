# AGENTS.md

The one authored rules file for this repository. Every AI coding agent in scope
reads it: Codex and GitHub Copilot in VS Code load it directly, and Claude loads it
through the one-line `CLAUDE.md` import stub. Edit rules here and nowhere else.

Keep this file well under 32 KiB, the Codex combined limit. Long reference material
belongs in `_engineer/` or an a-brain document, fetched on demand.

A repository on the lightweight template profile receives this file, `CLAUDE.md`,
`.claude/`, the boundary workflow and the pre-commit config, and nothing else. There,
sections that point into `_engineer/`, `docs/` or `AI-TASKS.md` do not apply; the rules
themselves still do.

---

## Work Ledger: check it first

Before answering any question about prior work, history or status, and at the start
of every task, call `brain_ledger_search` on the a-brain MCP server (the Codex
namespace is `a_brain`) for the repo or topic. Treat what it returns as the first
source; use `gh` or git only to verify or extend it, and say which you used. When a
task finishes, call `brain_ledger_add` with one line. This is how one tool learns
what another already did.

---

## This Repository

The block between the markers belongs to this repository. Template sync never
touches it. Everything outside it is owned by a-repo-template: change it there.

<!-- repo-rules:begin -->
# OpenAI Codex CLI — Project Standards

This file is auto-loaded by the OpenAI Codex CLI.
Loading order: root → current directory (downward path only).
Also reads `~/.codex/AGENTS.md` as a global file. Combined limit: 32 KiB.

---

## Project Layout

| Path | Purpose |
|------|---------|
| `AI-TASKS.md` | Canonical task list — read before starting any work |
| `_engineer/REQUIREMENTS.template.md` | Project scope and requirements (copy → REQUIREMENTS.md) |
| `_engineer/ENGINEER-FLOW.md` | Engineer lifecycle checklist |
| `_engineer/ENGINEER-README.md` | Shared AI rules, conventions, and guardrails |
| `_engineer/ado-sync/` | ADO sync utilities and scripts |
| `_engineer/dev-env/` | Terminal profile and dev-machine setup scripts |
| `_engineer/hipaa-sanitize/` | HIPAA redaction utility |
| `_engineer/dev-env/log_util.py` | Structured JSON logging utility — import in all Python scripts |
| `_engineer/workbench/` | Scratch space — not deployed, not reviewed |
| `requirements.txt` | Python dependencies — includes `python-json-logger` |
| `docs/` | Human-facing documentation templates |
| `infra-setup/` | Azure Bicep — `main.bicep` subscription-scoped orchestration; individual templates are standalone modules |
| `tests/fixture-library/` | Shared fixtures — never real user data |
| `tests/test-case-N/` | Scenario test cases; run `tests/new-test-case.ps1` to scaffold |
| `logs/dev-testing/` | Log output during active development |
| `logs/test-case-N/` | Log output per scenario run |
| `publish/` | Build output / release artefacts — gitignored |
| `.mcp.json` | Project-level MCP server configuration |
| `codex.json` | Codex project config including MCP servers |

---

## Core Rules

- Read `AI-TASKS.md` before starting any work
- Work one task at a time; each task = one coding step, not a feature
- Mark tasks `[x] (YYYY-MM-DD)` when done; add newly discovered work as new tasks
- All terminal commands must be written in Microsoft PowerShell (`pwsh`)
- Database schema changes must produce a migration file for subsequent execution
- When a pattern is replaced, clean up all references to the old pattern

---

## Session Handoff

Before ending or resetting a session, write a structured handoff note to `CONTEXT.md`.

**Threshold:** after 20 user-AI exchanges, proactively suggest writing the handoff.
**At PBI boundaries:** always write the handoff before ending the session.
**At session start:** check `CONTEXT.md` — if non-empty, read and acknowledge the prior context before doing any other work.

Handoff note format (overwrite the file):
```
# Session Handoff — YYYY-MM-DD

## Accomplished This Session
- [bullet]

## In Progress — Pick Up Here
[~] [task] — State: [...] — Next action: [...]

## Decisions Made
- [decision]: [reason]

## Open Blockers
- [item] (or "None")

## Next Step
> [Single sentence.]
```

Do not commit `CONTEXT.md` — it is session state.

---

## Engineer Flow

Follow `_engineer/ENGINEER-FLOW.md`. Required sequence before any coding:
2. REQUIREMENTS.md approved
3. AI-TASKS.md built from approved plan


---

## Security Rules — Non-Negotiable

- **Never** commit `.env`, credentials, keys, tokens, or PHI-containing files
- **Never** suggest hardcoded secrets, connection strings, or API keys in code
- **Always** use environment variables or Key Vault references for secrets
- **Flag immediately** if you detect a credential or PII in any file being edited
- **Never** run `rm -rf`, force-push to main, or drop database tables without explicit confirmation
- Secrets belong in `.env` (gitignored) or Key Vault — never in source
- Do not generate cryptographic primitives — use established libraries

---

## Task Tracking

### PBI Type Markers
| Marker | ADO Feature |
|--------|-------------|
| `[PBI:enhancement]` | Enhancements & New Capabilities |
| `[PBI:defect]` | Defects & Production Issues |
| `[PBI:tech-debt]` | Tech Debt & Refactoring |
| `[PBI:runbook]` | Runbooks, Monitoring & Operations |

### Status Convention
- `[ ]` todo
- `[~]` in progress
- `[x]` done — always include date `(YYYY-MM-DD)`

### ADO Sync
- Primary script: `_engineer/ado-sync/ai_ado_creator.py`
- Repo sync script: `_engineer/ado-sync/ado_repo_sync.py`
- Publish: `pwsh -NoProfile -Command "python ./_engineer/ado-sync/ai_ado_creator.py"`
- Do not commit `.ado_context_cache.json` or `_engineer/ado-sync/plans/*`

---

## Commit Conventions

- Commit at PBI boundaries, not mid-task
- Format: `PBI N: short description` + blank line + why/detail
- Never commit: `.env`, credentials, PHI, build artifacts
<!-- repo-rules:end -->

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

---

## Repo Layout

| Path | Purpose |
|------|---------|
| `AI-TASKS.md` | Canonical task list. Read before starting any work |
| `_engineer/` | Engineering meta-layer. Entry point: `ENGINEER-README.md` |
| `_engineer/REQUIREMENTS.template.md` | Project scope and requirements (copy to `REQUIREMENTS.md`) |
| `_engineer/ENGINEER-FLOW.md` | Engineer lifecycle checklist |
| `_engineer/ASSURANCE.md` | Assurance baseline: framework gates by workflow phase, scaled by AI impact tier |
| `_engineer/ado-sync/` | ADO sync utilities. Publish tasks to Azure DevOps |
| `_engineer/dev-env/` | Cross-platform PowerShell profile and launcher scripts |
| `_engineer/dev-env/log_util.py` | Structured JSON logging utility. Import in all Python scripts |
| `_engineer/hipaa-sanitize/` | HIPAA redaction utility |
| `_engineer/workbench/` | Scratch space. Not deployed, not reviewed |
| `docs/` | Human-facing docs (use `*.template.md` files as source) |
| `infra-setup/` | Azure Bicep. `main.bicep` orchestrates all resources at subscription scope |
| `requirements.txt` | Python dependencies, including `python-json-logger` |
| `tests/fixture-library/` | Shared fixtures. Never real user data |
| `tests/test-case-N/` | Scenario test cases. Run `tests/new-test-case.ps1` to scaffold |
| `logs/dev-testing/` | Log output during active development (`LOG_FILE=./logs/dev-testing/dev.log`) |
| `logs/test-case-N/` | Log output per scenario run (`LOG_FILE=./logs/test-case-N/run.log`) |
| `publish/dist/` | Build output, gitignored |
| `.mcp.json`, `codex.json`, `.vscode/mcp.json` | MCP server configuration per tool |

---

## Core Rules

- Read `AI-TASKS.md` before starting any work
- Work one task at a time. Each task is one coding step, not a feature
- Mark tasks `[x] (YYYY-MM-DD)` when done and add newly discovered work as new tasks
- All terminal commands must be written in **PowerShell** (`pwsh`), not bash or zsh
- Do not refactor unrelated code, rename files, or change dependencies unless the task requires it
- When a pattern is replaced, clean up all references to the old pattern
- Database schema changes must produce a migration file
- Prefer grounding answers in files read from the workspace over general knowledge
- After the user confirms `ONBOARDING.md`, run `python _engineer/ai-cost/configure.py`
  to apply the explicit AI cost choice. Configure only the selected scope. If no choice
  is present, leave existing configuration unchanged. Registration is not proof that
  provider usage is being collected, so verify the selected collector separately

---

## Engineer Flow

Follow `_engineer/ENGINEER-FLOW.md` strictly. The required sequence:

1. Complete `REQUIREMENTS.md` (do not write code before this)
2. Plan first. Confirm the guardrails and `REQUIREMENTS.md` are understood
3. Build `AI-TASKS.md` from the approved plan
4. Code one task at a time
5. Write tests at the end of each PBI (80 percent coverage target)

---

## AI Modes

Switch explicitly. Paste the relevant snippet into the chat.

**Planning:** *Do not write code. Review REQUIREMENTS.md and AI-TASKS.md, refine and prioritize tasks only.*
**Coding:** *Work on one task at a time. Return complete file contents for any file you modify.*
**Debug:** *Do not change architecture or unrelated code. Fix only the reported issue.*

---

## Assurance Baseline

`_engineer/ASSURANCE.md` is binding for design, implementation, and documentation
work in this repo. Read it before design work, and before any change touching model
inference, authentication, data handling, or deployment.

How it works:

- This repo declares an **AI impact tier** (T0 to T3) in `_engineer/REQUIREMENTS.md`.
- `ASSURANCE.md` lists obligations by workflow phase. Each is marked with the tiers
  it applies to and tagged with the control ID it satisfies.
- Apply the gates for this repo's declared tier. Do not skip gates at or below that
  tier, and do not impose higher-tier gates by default.

Non-negotiable at every tier above T0:

- **Treat all model output as untrusted input.** Validate, encode, and bound it
  before it reaches a shell, a query, a filesystem, a browser, or another model.
- **Record the AI system in the Aptica AI inventory** before first deployment. The
  inventory is the `a-governance` registry: add an `ai:` block to the artifact's
  registry entry. No second inventory, no substitute, no exemption.
- **Define security requirements during design**, in `REQUIREMENTS.md`, alongside
  functional requirements rather than appended afterward.

If a requested change would raise this repo's tier, say so before implementing it.
Adding autonomy or removing a human review step raises the tier.

---

## Security Rules (Non-Negotiable)

- **Never** commit `.env`, credentials, keys, tokens, or PHI-containing files
- **Never** suggest hardcoded secrets, connection strings, or API keys in code
- **Always** use environment variables or Key Vault references for secrets
- **Flag immediately** any credential, PHI, or PII detected in a file being edited
- **Never** run `rm -rf`, force-push to main, or drop database tables without explicit confirmation
- Validate all external inputs
- Do not generate cryptographic primitives. Use established libraries

### Secrets: Local vs Deployed

- Local: `cp .env.example .env` and fill in values, or use `op run -- <command>` (1Password CLI) to inject at runtime
- Deployed: secrets come from Azure Key Vault, never from source
- `.env` is gitignored. `.env.example` documents all required keys
- Gitleaks runs on every push and PR via `.github/workflows/secret-scan.yml`

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

## Code Conventions

**Backend (Node.js/TypeScript)**
- Business logic in `services/`, never in routes or components
- Routes handle HTTP only. Validation lives in `middleware/`
- Structured JSON logging with correlation IDs. Log level is controlled via the `LOG_LEVEL` env var
- HTTP request/response logging is filtered under DEBUG level
- Do not use `console.log` for production logging. Use the structured logger

**Frontend**
- A settings page is required, backed by a config file for defaults
- UI must be responsive and WCAG 2.1 compliant
- Background tasks must show progress and allow cancellation. The UI never appears frozen
- No technology brand names in UI ("cloud storage", not "Azure Blob")

**General**
- Config from environment variables, never hardcoded
- TypeScript strict mode

**Infrastructure (Azure Bicep)**
- All Bicep deployments use **subscription scope** (`targetScope = 'subscription'`) via `main.bicep`. Never require a pre-existing resource group
- `main.bicep` creates the resource group and calls individual resource templates as modules. Individual templates remain standalone and reusable
- Deploy with: `az deployment sub create --location <region> --template-file infra/main.bicep --parameters infra/main.bicepparam`
- Individual templates (`keyvault.bicep`, `document-intelligence.bicep`, `app-service.bicep`) use resource-group scope and can be deployed independently when only one resource needs updating
- Wire cross-module values (for example the Document Intelligence endpoint into App Service) from module outputs. Never duplicate endpoint URLs across param files
- Use `dependsOn` explicitly when a module references another by name string rather than resource reference (for example a Key Vault access policy added by the App Service module)
- All resources must carry the standard tag set: `project`, `managedBy: 'bicep'`, `environment`, `component`
- Never commit secrets to param files. Use Key Vault references (`@Microsoft.KeyVault(...)`) in App Settings, with `adminObjectId` and `spObjectId` as the only identity values in param files
- Validate every template before committing: `az bicep build --file <template> --outfile /tmp/check.json`
- All templates must be **idempotent**: re-running a deployment must produce the same result without errors. Key rules:
  - Role assignments: use `guid(resourceId, principalId, roleId)` for deterministic names (already ARM-idempotent)
  - Key Vault access policies: use the `add` action (merges, not replaces)
  - Cognitive Services (Document Intelligence, Azure OpenAI): soft-delete means a re-deploy after deletion fails until the resource is purged. Document this in the template header and add the purge command as a comment: `az cognitiveservices account purge --location <region> --resource-group <rg> --name <name>`
  - Key Vault: same soft-delete behavior. Purge with `az keyvault purge --name <name>` if a deleted vault blocks redeployment
  - Never set `enablePurgeProtection: true` on Key Vault unless required for compliance. It permanently prevents purging

---

## Testing

- Unit tests for all service functions and integration tests for workflows
- Use fixtures from `tests/fixture-library/` and `tests/test-case-1/`, never real data
- Target 80 percent code coverage minimum

---

## Commit Conventions

- Commit at PBI boundaries, not mid-task
- Format: `PBI N: short description` + blank line + why/detail
- Never add a `Co-Authored-By` trailer for an AI assistant. Aptica policy is that
  assistants do not attribute themselves as git co-authors. This is enforced, not
  merely preferred: the `strip-ai-coauthors` hook in `.pre-commit-config.yaml`
  runs at the `commit-msg` stage and removes the trailer for any assistant. Adding
  one produces a commit whose recorded message differs from the one authored,
  which is worse than omitting it.
- Never commit: `.env`, credentials, PHI, build artifacts, `_engineer/workbench/`

---

## Session Handoff

Before ending or resetting a session, write a structured handoff note to `CONTEXT.md`.

**Threshold:** after 20 exchanges, proactively suggest writing the handoff.
**At PBI boundaries:** always write the handoff before ending the session.
**At session start:** if `CONTEXT.md` is non-empty, read it and acknowledge the prior context before doing any other work.

Handoff note format (overwrite the file):

```
# Session Handoff: YYYY-MM-DD

## Accomplished This Session
- [bullet]

## In Progress: Pick Up Here
[~] [task]. State: [...]. Next action: [...]

## Decisions Made
- [decision]: [reason]

## Open Blockers
- [item] (or "None")

## Next Step
> [Single sentence.]
```

Do not commit `CONTEXT.md`. It is session state.

### Session Checkpoint

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

Use templates in `docs/` when asked to produce a solution document. After adding a
doc, update `docs/DOC-TOC.md` with a one-line description.

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

---

## Tool-Specific Notes

These apply only to the named tool. Everything above applies to all of them.

**Claude Code**
- `/handoff` writes the `CONTEXT.md` note described above. Run it before every `/clear`
- Memory lives at `~/.claude/projects/<encoded-path>/memory/`. Save role and expertise,
  confirmed non-obvious approaches, project decisions, and external resource locations.
  Do not save code patterns (read the code), ephemeral task state (use `AI-TASKS.md`),
  or git history
- Subagents: `Explore` for broad codebase research, `Plan` for architecture before
  non-trivial work, `general-purpose` for research that should not pollute main context.
  Run independent agents in parallel and do not duplicate subagent work

**GitHub Copilot (VS Code)**
- MCP servers are configured in `.vscode/mcp.json`
