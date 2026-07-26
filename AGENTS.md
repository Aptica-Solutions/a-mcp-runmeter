# OpenAI Codex CLI — Project Standards

This file is auto-loaded by the OpenAI Codex CLI.
Loading order: root → current directory (downward path only).
Also reads `~/.codex/AGENTS.md` as a global file. Combined limit: 32 KiB.

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

**Do not write code, create files, plan architecture, run scripts, or make any project decisions until `ONBOARDING.md` exists in the project root and the user has confirmed it is accurate.**

If `ONBOARDING.md` is missing or empty, respond with:
> "ONBOARDING.md not found. I cannot begin any project work until the survey is complete. Walk through `_engineer/ONBOARDING.template.md` with the user and write the answers to `ONBOARDING.md`."

If `ONBOARDING.md` exists but has not been confirmed in this session, ask once:
> "Is ONBOARDING.md current and accurate? (yes to confirm / describe what changed)"

Answering questions about the template itself is permitted. All project-specific work is blocked until confirmed.

---

## Project Layout

| Path | Purpose |
|------|---------|
| `AI-TASKS.md` | Canonical task list — read before starting any work |
| `_engineer/REQUIREMENTS.template.md` | Project scope and requirements (copy → REQUIREMENTS.md) |
| `_engineer/ONBOARDING.template.md` | Stakeholder survey template (copy → ONBOARDING.md) |
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

## Initialization

To start a new project from this template, run the init script. It installs and verifies required tooling.

```powershell
pwsh -NoProfile -File "_engineer/dev-env/init-repo-tooling.ps1"
```

Then walk through the survey (`_engineer/ONBOARDING.template.md`) with the user before any planning or coding.

---

## Engineer Flow

Follow `_engineer/ENGINEER-FLOW.md`. Required sequence before any coding:
1. ONBOARDING.md complete and accurate
2. REQUIREMENTS.md approved
3. AI-TASKS.md built from approved plan

Do not write code without explicit user confirmation that ONBOARDING is complete and accurate.

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
