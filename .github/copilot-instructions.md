# GitHub Copilot Instructions

Read `_engineer/ENGINEER-README.md` for full project conventions and guardrails.
This file is a Copilot-specific summary. MCP servers are configured in `.vscode/mcp.json`.

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

If `ONBOARDING.md` is missing or empty:
> "ONBOARDING.md not found. Complete the survey in `_engineer/ONBOARDING.template.md` and save it as `ONBOARDING.md` before I can begin any project work."

If `ONBOARDING.md` exists but has not been confirmed this session, ask once:
> "Is ONBOARDING.md current and accurate? (yes to confirm / describe what changed)"

---

## Project Context

TODO: Describe the project domain, tech stack, and primary users.

---

## Code Conventions

- Business logic in `services/` — never in routes or components
- Routes handle HTTP only
- Validation in `middleware/`
- Config from environment variables — never hardcoded
- TypeScript strict mode
- Structured JSON logging with correlation IDs

## Security — Always

- Never suggest hardcoded credentials, tokens, API keys, or connection strings
- Secrets belong in `.env` (local) or Key Vault (deployed) — always via env vars
- Validate all external inputs
- Flag any code that could expose PHI, PII, or credentials

## What to Avoid

- Do not refactor code unrelated to the current task
- Do not rename files or change dependencies unless the task requires it
- Do not generate cryptographic primitives — use established libraries
- Do not suggest `console.log` for production logging — use the structured logger

## Testing

- Unit tests for all service functions
- Integration tests for workflows
- Use test fixtures from `tests/fixture-library/` and `tests/test-case-1/` — never real data
- Target 80% code coverage minimum

## Documentation

When adding a doc file to `docs/`, update `docs/DOC-TOC.md` with a one-line description.

---

## Task Tracking

All work flows from `AI-TASKS.md`. Each task is one coding step.
Status: `[ ]` todo · `[~]` in progress · `[x]` done `(YYYY-MM-DD)`
