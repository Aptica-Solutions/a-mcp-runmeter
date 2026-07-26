# Governance Guide

> Audience: Compliance / Legal / Risk
> Purpose: Data lineage, explainability, audit trails, and regulatory posture

<!-- INSTRUCTIONS FOR AI
Delete any compliance section (HIPAA / SOC 2 / PCI DSS) whose condition is not met per ONBOARDING.md.
Do not leave "(if applicable)" stubs — either fill them in or delete them entirely.
-->

---

## Data Classification

| Classification | Examples | Handling |
|---------------|----------|---------|
| Public | Marketing copy, docs | No restrictions |
| Internal | Business logic, configs | Restrict external sharing |
| Confidential | PII, financial data | Encrypt at rest and in transit |
| Restricted / PHI | Health records | HIPAA controls, audit logging required |

> *(Delete the "Restricted / PHI" row if ONBOARDING "Compliance" does not include HIPAA.)*

---

## Data Lineage

TODO: Describe where data enters the system, how it flows between components, and where it exits or is persisted.

---

## Audit Logging

All sensitive operations must be logged with:
- Timestamp (UTC)
- Actor (user ID or service principal)
- Action performed
- Resource affected
- Outcome (success / failure)

Log destination: TODO — specify per ONBOARDING "Log Destination" answer.

---

## Explainability

> *(Include if: AI/ML models are used. Delete if not applicable.)*
> TODO: Describe how predictions can be explained to affected individuals and regulators.

---

## Compliance Controls

> *(Include if: ONBOARDING "Compliance" includes HIPAA. Delete this entire section if not applicable.)*

### HIPAA

- PHI must not appear in logs, error messages, or API responses beyond what is necessary
- Access to PHI must be role-based and audited
- BAA must be in place with all third-party processors
- TODO: List covered data elements and their handling

---

> *(Include if: ONBOARDING "Compliance" includes SOC 2. Delete this entire section if not applicable.)*

### SOC 2

- Change management: all changes go through PR review with CODEOWNERS approval
- Incident response: see `docs/ENGINEER.md`
- Availability SLA: TODO

---

> *(Include if: ONBOARDING "Compliance" includes PCI DSS. Delete this entire section if not applicable.)*

### PCI DSS

- Cardholder data must never be stored locally
- All payment flows must use a certified payment processor

---

## Retention Policy

| Data Type | Retention | Deletion Method |
|-----------|-----------|----------------|
| Audit logs | 7 years | Automated purge via storage lifecycle policy |
| Application logs | 90 days | Log Analytics retention setting |
| User data | Per contract | Manual delete or data export API |

---

## Access Reviews

TODO: Schedule and process for quarterly access reviews.
