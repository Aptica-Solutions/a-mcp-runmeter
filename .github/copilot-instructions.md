# GitHub Copilot Instructions

Read `_engineer/ENGINEER-README.md` for full project conventions and guardrails.
This file is a Copilot-specific summary. MCP servers are configured in `.vscode/mcp.json`.

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
