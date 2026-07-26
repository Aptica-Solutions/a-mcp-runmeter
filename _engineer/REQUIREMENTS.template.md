# Requirements

<!-- INSTRUCTIONS FOR AI
When filling in this template from ONBOARDING.md answers:
- Replace all TODO placeholders with content derived from the survey
- Delete any conditional section whose condition is not met — do not leave placeholders
- Conditional sections are marked: > *(Include if: condition. Delete if not applicable.)*
-->

## Overview and Purpose

> Describe what the system does, who uses it, and why it exists.

---

## Entity & Environment

- **Entity:** TODO
- **Environments:** dev · test · prod
- **Compliance:** TODO — choose from: HIPAA / SOC 2 / PCI DSS / None

---

## Functional Requirements

> List the key features and behaviors the system must have.

- TODO

---

## Non-Functional Requirements

- **Performance:** TODO (e.g. p95 response time < 500ms under X concurrent users)
- **Security:** Secrets via env injection or Key Vault; encrypted at rest and in transit
- **Scalability:** TODO
- **Availability:** TODO (e.g. 99.9% uptime SLA)
- **Observability:** Structured JSON logging with correlation IDs; log destination per survey

> *(Include if: ONBOARDING "Auth" = Entra / OAuth. Delete if not applicable.)*
> - **Authentication:** OAuth via Entra interactive login; bearer token validation; RBAC

> *(Include if: ONBOARDING "Log Destination" = Application Insights. Delete if not applicable.)*
> - **Telemetry:** Application Insights for metrics, traces, and alerts

---

## UI Standards

> *(Include if: ONBOARDING "Project Type" includes Frontend. Delete if not applicable.)*

- Settings page required, backed by a config file
- Responsive layout, WCAG 2.1 compliant
- No technology brand names in the UI — use generic terminology
- Background tasks must show progress and allow cancellation

---

## Compliance Requirements

> *(Include if: ONBOARDING "Compliance" includes HIPAA. Delete if not applicable.)*
> - PHI must not appear in logs, error messages, or API responses beyond what is necessary
> - Access to PHI must be role-based and audited
> - BAA must be in place with all third-party processors

> *(Include if: ONBOARDING "Compliance" includes SOC 2. Delete if not applicable.)*
> - All changes go through PR review with CODEOWNERS approval
> - Incident response process documented in `docs/ENGINEER.md`
> - Availability SLA: TODO

> *(Include if: ONBOARDING "Compliance" includes PCI DSS. Delete if not applicable.)*
> - Cardholder data must never be stored locally
> - All payment flows must use a certified payment processor

---

## Constraints

- TODO (budget, timeline, platform, team size, existing systems to integrate with)

---

## Success Criteria

- TODO (what does "done" look like? What metrics define success?)

---

## Out of Scope

- TODO (what are we explicitly NOT building?)
