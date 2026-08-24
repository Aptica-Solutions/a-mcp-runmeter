# Google Gemini CLI — Project Standards

This file is auto-loaded by the Google Gemini CLI.
Loading order: all ancestor directories (upward from cwd) + all subdirectories recursively (BFS downward).
Use `/memory list` and `/memory reload` to inspect what's loaded in a session.

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
| `.mcp.json` | Shared project-level MCP server configuration |
| `.gemini/settings.json` | Gemini CLI project config including MCP servers |

---

## Core Rules

- Read `AI-TASKS.md` before starting any work
- Work one task at a time; each task = one coding step, not a feature
- Do not refactor unrelated code, rename files, or change dependencies unless required
- Mark tasks `[x] (YYYY-MM-DD)` when done; add newly discovered work as new tasks
- All terminal commands must be written in PowerShell (`pwsh`)
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

## AI Modes

Paste the relevant snippet to switch modes.

**Planning:** *Do not write code. Review REQUIREMENTS.md and AI-TASKS.md, refine and prioritize the task list only.*
**Coding:** *Work on the current task only. Return complete file contents for any file you modify.*
**Debug:** *Do not change architecture or unrelated code. Fix only the issue described.*

---

## Gemini-Specific Notes

- Gemini scans all subdirectories — keep context files focused; do not put sensitive data in `GEMINI.md`
- Use `/memory reload` after adding a new `GEMINI.md` in a subdirectory to pick it up mid-session
- Prefer grounding responses in files read from the workspace over general knowledge

---

## Commit Conventions

- Commit at PBI boundaries, not mid-task
- Format: `PBI N: short description` + blank line + why/detail
- Co-author line: `Co-Authored-By: Google Gemini <noreply@google.com>`
