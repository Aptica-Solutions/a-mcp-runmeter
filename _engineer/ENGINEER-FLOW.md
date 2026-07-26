# Engineer Flow - The Human Kind

## Architecture, Design, Initial Build
- [ ] `ONBOARDING.md` completed
- [ ] `REQUIREMENTS.md` completed
- [ ] Engage AI in PLAN mode
- [ ] CONFIRM AI understands ONBOARDING, GUARDRAILS, and REQUIREMENTS **BEFORE CODE MODE**
- [ ] once plan is created and approved, have AI build the AI-TASKS.md
- [ ] Review tasks and proceed to initial build
- [ ] Switch to CODE MODE and have it take a first pass at developing it
- [ ] After first pass is complete, confirm **Security Baseline**

## Security Baseline
- [ ] `.env.example` complete and accurate
- [ ] `pre-commit install` is run once after cloning
- [ ] Gitleaks secret scan passing on main branch `gitleaks detect --source . --verbose`
- [ ] Dependabot enabled
- [ ] Key Vault provisioned and secrets loaded

## Ensure Components and Standards are in progress/done
- [ ] Auth flow working (even if it is local creds)
- [ ] Structured logging with correlation IDs working
- [ ] Project components build and run

## Development Iteration
- [ ] Work through the features and TASKS.  Update ADO if desired
- [ ] Ensure tests are created at the end of each PBI

## Testing
- [ ] Unit tests written and passing (80%+ coverage)
- [ ] Integration tests passing
- [ ] Security scan clean
- [ ] WCAG 2.1 accessibility verified (as applicable)

## Documentation
- [ ] `docs/DEMO.md` completed
- [ ] `docs/DEVELOPER.md` completed
- [ ] `docs/ENGINEER.md` completed
- [ ] `docs/INFRA.md` completed
- [ ] `README.md` reflects current state
- [ ] `docs/DOC-TOC.md` TOC is current

## Pre-Production
- [ ] Bicep templates deployed to staging and validated
- [ ] CI/CD pipeline configured and passing
- [ ] Monitoring and alerts configured
- [ ] Cost tracking and budget alerts set
- [ ] Disaster recovery tested
- [ ] Security review completed
- [ ] Compliance validation passed *(include only regulations listed in ONBOARDING "Compliance"; skip if None)*

## Go Live
- [ ] Production deployment executed
- [ ] Post-deployment health checks passing
- [ ] Logs flowing to configured destination *(Application Insights if selected in ONBOARDING "Log Destination")*
- [ ] Team trained on operations
- [ ] Support runbook in place

## Post-Launch
- [ ] Monitoring logs reviewed for errors in first 48 hours
- [ ] Cost tracking verified
- [ ] User feedback collected
- [ ] Retrospective completed

# Notes on Priming the AI Agents
OpenAI Codex CLI — AGENTS.md
  - Walks root → current directory (downward path only):
  - Also reads ~/.codex/AGENTS.md as a global file
  - Files are concatenated in order (deeper = later = higher precedence)
  - AGENTS.override.md takes priority over AGENTS.md at the same level
  - Max one file per directory; 32 KiB combined limit

Claude Code CLI - CLAUDE.md
  - Walks from root down to the file being edited, as well as ~/.claude/CLAUDE.md globally.

Google Gemini CLI — GEMINI.md

  - Reads Ancestor directories (upward from cwd)
  - All subdirectories recursively (BFS downward scan)
  - All found files are concatenated and sent with every prompt
  - /memory list and /memory reload commands to inspect what's loaded

# ADO Sync

Publish TASKS.md to Azure DevOps after each PBI:

```powershell
pwsh -NoProfile -Command "python ./_engineer/ado-sync/ai_ado_creator.py"
```
