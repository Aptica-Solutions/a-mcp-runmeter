# Engineer Guide

> Audience: DevOps, Platform, Support Engineers
> Purpose: Installation, configuration, and advanced operational topics

---

## Prerequisites

TODO: List runtime dependencies, required access, tool versions.

## Installation

TODO: Step-by-step installation for each environment (dev / test / prod).

## Configuration

All configuration via environment variables. See `.env.example`.

### Key Vault Integration

```powershell
# Retrieve a secret
pwsh -NoProfile -Command "az keyvault secret show --vault-name <vault> --name <secret-name>"

# Inject secrets at runtime
pwsh -NoProfile -Command "op run -- <start-command>"
```

## Deployment

See `docs/INFRA.md` for infrastructure provisioning.
See `.github/workflows/` for CI/CD pipeline definitions.

## Secrets Rotation

1. Rotate the secret in Key Vault
2. Restart affected services
3. Verify health checks pass
4. Update `AI-TASKS.md` with a `[PBI:runbook]` entry

## Monitoring & Alerts

TODO: Links to dashboards, alert rules, on-call runbook.

## Troubleshooting

TODO: Common failure modes and resolution steps.

---

## ADO Sync Toolkit

Scripts live in `_engineer/ado-sync/`. All configuration via environment variables — copy `.env.example` and fill in values before running.

### Required env vars

| Variable | Purpose |
|---|---|
| `ADO_ORG` | Azure DevOps organization name |
| `ADO_PROJECT` | ADO project name |
| `ADO_PAT` | Personal access token (Work Items read/write) |
| `ADO_API_VERSION` | API version (default: `7.1`) |
| `ANTHROPIC_API_KEY` | Claude API key for AI interpretation |

Optional: `ADO_PROJECT_GUID`, `ADO_CONTEXT_CACHE_PATH`, `ADO_PLAN_OUTPUT_DIR`, `ADO_TASKS_MD_PATH`.

### Interactive REPL (recommended first run)

```powershell
# Always start with --dry-run to preview before writing to ADO
pwsh -NoProfile -Command "python3 _engineer/ado-sync/ai_ado_creator.py --dry-run"
```

At the prompt, type plain-English updates:
```
> B126 CHIRP nav is done; now working on suffix iteration
> Need a new PBI under B121 for the CalAIM API timeout
```

REPL commands: `dry-run` (toggle), `refresh` (reload context cache), `quit`.

### Scaffold modes

```powershell
# Discovery scaffold — Epic + Discovery PBI + tasks (paste text at prompt)
pwsh -NoProfile -Command "python3 _engineer/ado-sync/ai_ado_creator.py --discovery-scaffold --dry-run"

# Discovery scaffold from a document
pwsh -NoProfile -Command "python3 _engineer/ado-sync/ai_ado_creator.py --discovery-scaffold --source-info <path> --dry-run"

# Development scaffold from a document or folder
pwsh -NoProfile -Command "python3 _engineer/ado-sync/ai_ado_creator.py --development-scaffold --source-info <path> --dry-run"
```

### Expected dry-run flow

1. Script loads ADO context (or reads from `.ado_context_cache.json` if cached).
2. AI generates a proposed operation list and prints it with `[DRY RUN]` prefix.
3. A plan file is saved to `_engineer/ado-sync/plans/ado-plan-<timestamp>.json`.
4. No ADO changes are made.

To execute a saved plan:

```powershell
pwsh -NoProfile -Command "python3 _engineer/ado-sync/ai_ado_creator.py --execute-plan _engineer/ado-sync/plans/ado-plan-<timestamp>.json"
```

### Force-refresh context cache

```powershell
pwsh -NoProfile -Command "python3 _engineer/ado-sync/ai_ado_creator.py --refresh"
```

The context cache (`.ado_context_cache.json`) is generated at runtime and is gitignored.

### ADO work item creation

Run `ai_ado_creator.py` interactively to create or update work items from `AI-TASKS.md`:

```powershell
pwsh -NoProfile -Command "python3 _engineer/ado-sync/ai_ado_creator.py"
```
