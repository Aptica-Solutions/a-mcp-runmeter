# Engineer Flow - The Human Kind

> Items marked *(T1+)*, *(T2+)*, or *(T3)* apply only at or above that AI impact
> tier. The tier is declared in `REQUIREMENTS.md`. Full gates and control mappings
> live in `_engineer/ASSURANCE.md`. A T0 project skips every marked item.

## Architecture, Design, Initial Build
- [ ] `ONBOARDING.md` completed
- [ ] Apply the explicit AI cost choice with `python _engineer/ai-cost/configure.py`; verify the selected collector/integration separately
- [ ] `REQUIREMENTS.md` completed
- [ ] **AI impact tier declared** in `REQUIREMENTS.md`, with rationale if the call was close
- [ ] Security requirements written into `REQUIREMENTS.md` alongside functional requirements
- [ ] Threat model recorded: what an attacker targets, what they gain, what stops them
- [ ] Data sensitivity classified before storage design is fixed
- [ ] *(T1+)* AI system entered in the Aptica AI inventory in `a-governance`
- [ ] *(T1+)* MAP record drafted in `docs/GOVERNANCE.md`
- [ ] *(T1+)* Human oversight defined: who reviews what, when, with what override authority
- [ ] *(T2+)* Agency bounded: narrowest tool and permission set that meets the requirement
- [ ] *(T3)* Go or no-go decision recorded with a named accountable owner
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
- [ ] *(T1+)* Model output treated as untrusted input at every boundary it crosses
- [ ] *(T1+)* Sensitive data kept out of prompts, logs, and telemetry
- [ ] *(T2+)* Retrieval and embedding sources access-controlled per requesting principal
- [ ] *(T2+)* Consumption bounded server side: token, cost, rate, and recursion limits

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
- [ ] *(T1+)* Evaluation set version controlled and separate from development examples
- [ ] *(T2+)* Adversarial testing against OWASP LLM Top 10 2026, minimally prompt injection and improper output handling
- [ ] *(T2+)* Failure modes characterized, not just pass rates: what it gets wrong and who absorbs it
- [ ] *(T3)* Fairness and harmful bias evaluated across the subpopulations the system will encounter
- [ ] *(T3)* Results reviewed by someone who did not build the system

## Documentation
- [ ] `docs/DEMO.md` completed
- [ ] `docs/DEVELOPER.md` completed
- [ ] `docs/ENGINEER.md` completed
- [ ] `docs/INFRA.md` completed
- [ ] *(T1+)* `docs/GOVERNANCE.md` completed, including the AI System Record
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
- [ ] Release integrity verifiable: tagged, signed, reproducible
- [ ] *(T1+)* AI monitoring live: output quality, refusal and error rates, cost, drift
- [ ] *(T1+)* Disengage path tested, confirming the system can be reverted without a deployment
- [ ] *(T2+)* Users informed they are interacting with an AI system and what it can be relied on for
- [ ] *(T2+)* Incident response covers a confidently wrong output that already reached a client

## Go Live
- [ ] Production deployment executed
- [ ] Post-deployment health checks passing
- [ ] Logs flowing to configured destination *(Application Insights if selected in ONBOARDING "Log Destination")*
- [ ] Team trained on operations
- [ ] Support runbook in place

## Post-Launch
- [ ] Monitoring logs reviewed for errors in first 48 hours
- [ ] *(T1+)* Monitoring review cadence set with a named owner. An unreviewed dashboard is not monitoring
- [ ] *(T1+)* Model or provider version changes flagged as requiring re-evaluation, not treated as transparent upgrades
- [ ] *(T2+)* Override rate reviewed as the most honest available quality signal
- [ ] Cost tracking verified
- [ ] User feedback collected
- [ ] Retrospective completed

# Notes on Priming the AI Agents
AGENTS.md is the only authored rules file.

  - Codex CLI reads it from root down to the current directory, plus ~/.codex/AGENTS.md globally. 32 KiB combined limit
  - GitHub Copilot in VS Code reads the root AGENTS.md (setting chat.useAgentsMdFile)
  - Claude Code reads CLAUDE.md, which is a one-line stub containing @AGENTS.md. Do not add rules to the stub

# ADO Sync

Publish TASKS.md to Azure DevOps after each PBI:

```powershell
pwsh -NoProfile -Command "python ./_engineer/ado-sync/ai_ado_creator.py"
```
