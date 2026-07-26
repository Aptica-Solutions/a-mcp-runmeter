# TASKS

Status: `[ ]` todo · `[~]` in progress · `[x]` done `(YYYY-MM-DD)`

PBI markers: `[PBI:enhancement]` · `[PBI:defect]` · `[PBI:tech-debt]` · `[PBI:runbook]`

Publish to ADO: `pwsh -NoProfile -Command "python ./_engineer/ado-sync/ai_ado_creator.py"`

---

<!-- CONDITIONAL TASKS — AI GENERATION RULES
When generating AI-TASKS.md from this example, include ONLY the conditional blocks
whose survey condition is met. Delete blocks whose condition is not met entirely —
do not leave behind commented-out tasks or placeholder sections.

Condition → Survey answer required to INCLUDE the block:
  IF:oauth              → ONBOARDING "Auth Requirements" includes "Entra / OAuth"
  IF:frontend           → ONBOARDING "Project Type" includes "Frontend Application" or "Full Stack"
  IF:application-insights → ONBOARDING "Log Destination" includes "Application Insights"
  IF:azure-infra        → ONBOARDING "Cloud" includes "Azure"
  IF:hipaa              → ONBOARDING "Compliance" includes "HIPAA"
  IF:soc2               → ONBOARDING "Compliance" includes "SOC 2"
  IF:pci                → ONBOARDING "Compliance" includes "PCI DSS"
  IF:ado-sync           → ONBOARDING "AI Tooling" includes ADO integration or user explicitly wants ADO sync

All tasks NOT inside a conditional block are always included.
-->

# Solution Standards [PBI:enhancement]

[ ] Use 1Password CLI (`op run -- <command>`) to inject secrets at runtime — never hardcoded values
[ ] Configure `.env` scoped per technical area (backend, frontend, infra)
[ ] Implement structured JSON logging with correlation IDs; log level configurable via Settings page
[ ] Settings page backed by a config file for default values
[ ] Build `tasks.json` in VS Code workspace for clean/build/restart with process teardown
[ ] Configure MCP servers in the relevant config files (`.mcp.json`, `.vscode/mcp.json`, etc.)
[ ] Update `REPO-README.md` as features are added

<!-- IF:azure-infra -->
[ ] Write Bicep templates for all infrastructure in `infra-setup/bicep/`
<!-- /IF:azure-infra -->

<!-- IF:oauth -->
[ ] Incorporate OAuth flow via Entra interactive login
<!-- /IF:oauth -->

<!-- IF:frontend -->
[ ] UI is responsive and WCAG 2.1 compliant
[ ] UI never appears frozen — show progress and allow cancellation for background tasks
<!-- /IF:frontend -->

---

# Security Baseline [PBI:enhancement]

[ ] Verify gitleaks secret scan is passing on all branches
[ ] Confirm `.env` is gitignored and `.env.example` is complete and accurate
[ ] Enable Dependabot for dependency vulnerability alerts
[ ] Validate all external inputs (API endpoints, file uploads, query params)
[ ] Implement rate limiting on all public API routes
[ ] Confirm all secrets are sourced from Key Vault or env injection — no hardcoded values
[ ] Add CORS configuration appropriate for deployment environment
[ ] Enable audit logging for all authentication events

---

# Standard Solution Components

## Backend — API Setup [PBI:enhancement]

[ ] Initialize `backend/` with Node.js project (package.json, TypeScript config, tsconfig.json)
[ ] Set up Express with middleware: cors, body-parser, morgan
[ ] Implement structured logging with correlation IDs (winston or pino)
[ ] Configure env loading with validation (zod or joi)
[ ] Create `services/` for business logic, `routes/` for HTTP, `middleware/` for validation/auth

## Backend — Authentication & Authorization [PBI:enhancement]

<!-- IF:oauth -->
[ ] Implement OAuth middleware (Entra)
[ ] Add bearer token validation
[ ] Implement RBAC / tenant isolation logic
[ ] Add auth events to audit log
<!-- /IF:oauth -->

<!-- IF NOT oauth -->
[ ] Implement API key / bearer token validation middleware (no OAuth)
[ ] Add auth events to audit log
<!-- /IF NOT oauth -->

<!-- IF:frontend -->
## Frontend — Setup [PBI:enhancement]

[ ] Initialize `frontend/` (React + Vite or framework of choice)
[ ] Create layout components (header, nav, footer)
[ ] Implement API client with axios/fetch and error handling
[ ] Configure env variables for API endpoints

## Frontend — Settings Page [PBI:enhancement]

[ ] Create Settings component backed by config file
[ ] API key management (masked display, never plain text)
[ ] Log level selector
[ ] Settings save with validation

<!-- IF:oauth -->
[ ] OAuth toggle and configuration UI
<!-- /IF:oauth -->
<!-- /IF:frontend -->

## Infrastructure [PBI:enhancement]

<!-- IF:azure-infra -->
[ ] Key Vault for secrets management
[ ] Diagnostic settings for logging and monitoring
[ ] Tag all resources: env, app, feature, customer, workload
<!-- /IF:azure-infra -->

<!-- IF:application-insights -->
[ ] Application Insights for telemetry
<!-- /IF:application-insights -->

<!-- IF:hipaa -->
[ ] Implement PHI access controls — role-based, audited
[ ] Confirm PHI does not appear in logs, error messages, or API responses
[ ] Verify BAA is in place with all third-party processors
<!-- /IF:hipaa -->

<!-- IF:soc2 -->
[ ] Validate change management process: all changes via PR with CODEOWNERS approval
[ ] Define and document incident response process
<!-- /IF:soc2 -->

<!-- IF:pci -->
[ ] Confirm cardholder data is never stored locally
[ ] Validate all payment flows use a certified payment processor
<!-- /IF:pci -->

## DevOps [PBI:runbook]

[ ] Create deployment pipeline (CI/CD)
[ ] Set up cost threshold alerts
[ ] Add Swagger/OpenAPI documentation
[ ] Ensure no extraneous files in source (exclude `_engineer/workbench/`)
[ ] Create demo data and walkthrough script

<!-- IF:application-insights -->
[ ] Configure Application Insights and alert rules
<!-- /IF:application-insights -->

## Testing [PBI:enhancement]

[ ] Unit tests for all service functions (target 80% coverage)
[ ] Integration tests for key workflows
[ ] Validate correlation ID propagation end-to-end
[ ] Security scan passing (gitleaks, npm audit)

<!-- IF:oauth -->
[ ] Test OAuth flow end-to-end
<!-- /IF:oauth -->

<!-- IF:hipaa -->
[ ] Verify PHI does not leak in test logs or fixtures
<!-- /IF:hipaa -->

---

# History

<!-- Mark completed PBIs here with date and summary -->
