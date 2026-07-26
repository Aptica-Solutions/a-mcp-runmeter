# ENGINEER TASKS
Human Task Staging Area to tee up for AI

## Task List

### GitHub-native organization optimization [PBI:tech-debt]

Approved policy:

> Aptica-Solutions will use GitHub Secret Protection across all repositories,
> with local gitleaks pre-commit scanning retained and the organization-wide
> gitleaks Action retired after validation. Aptica-Solutions will retain GitHub
> Code Security for a 60-day, risk-based CodeQL rollout, beginning with PHI,
> PII, high-risk, and currently affected supported-language repositories.
> Expansion will depend on findings, remediation value, and Actions usage.

- [x] (2026-07-23) Repair the template boundary manifest and add bidirectional integrity validation
- [x] (2026-07-23) Document the property-driven GitHub control plane, rollout cohorts, rollback procedure, and success metrics
- [x] (2026-07-23) Add centralized template-compliance validation suitable for organization-ruleset enforcement
- [x] (2026-07-23) Harden organization Actions defaults and add metered-usage budget guidance
- [x] (2026-07-23) Implement CodeQL-scannable Python template synchronization with profiles, dry-run, conflict-safe apply, downstream lock state, and a PowerShell compatibility wrapper
- [x] (2026-07-24) Harden canary bootstrap to upgrade exact historical template files, preserve genuine customizations, remove copied markers, and require marker plus canonical origin
- [ ] Tag `template-v2026.07.2` after the canary-hardening patch merges and revalidate the three canaries
- [ ] Add the GitHub App release controller and idempotent pull-request orchestration
- [ ] Consolidate Secret Protection settings and validate equivalent or better coverage on every repository
- [ ] Retire the organization-wide gitleaks Action and license secret after validation; retain local pre-commit gitleaks
- [~] Enable the 60-day CodeQL pilot for PHI, PII, high-risk, and currently affected supported-language repositories — configuration 262167 attached to `a-repo-template`; remaining cohort pending
- [ ] Remediate or disposition the seven existing open CodeQL alerts
- [ ] Evaluate Code Security after 60 days using findings, remediation value, false positives, and Actions usage

## History
- [x] 2026-05-08 — Template/reference audit: fixed `init-project.ps1` → `init-repo-tooling.ps1` in CLAUDE.md; fixed `infra-setup/bicep/` → `infra/` in CLAUDE.md and README.md; fixed `profile-and-utils` and `profile/` subdir references in README.md; fixed `launch-code.ps1` (standalone script that doesn't exist) → `Launch-Code` profile function in README.md; removed nonexistent Terraform row from README.md infra table
- [x] 2026-05-08 — Added `Invoke-HipaaRedact` to `functions.ps1` — wraps `_engineer/hipaa-sanitize/hipaa_redact.py`; supports `-InputPdf`, `-OutputPdf`, `-OffsetDays`, `-Names`, `-Facilities`, `-Repo`; uses project venv Python when available
- [x] 2026-05-08 — Added `Invoke-AdoCreator` to `functions.ps1` — wraps `_engineer/ado-sync/ai_ado_creator.py` for interactive ADO work item creation; updated `Invoke-AdoRepoSync` to check local `_engineer/ado-sync` as first candidate before central automation repo
- [x] 2026-05-08 — Added `Invoke-ProjectSetup` to `functions.ps1` — calls `runtime-setup/setup.ps1` from the project root; deleted duplicate `_engineer/dev-machine-setup/set-dev-env.ps1` (identical copy of `runtime-setup/setup.ps1`); added `_Get-VenvPython` private helper used by all three new functions
