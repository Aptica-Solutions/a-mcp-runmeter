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

## AI System Record

> *(Include if: AI impact tier is T1 or above per REQUIREMENTS.md. Delete this entire
> section at T0.)*
>
> This is the MAP record required by `_engineer/ASSURANCE.md` phase 1. It is the
> artifact an auditor, a client, or a future maintainer will actually read. Ten
> minutes of work at T1. Longer at T3, and worth it.

- **System:** TODO
- **AI impact tier:** TODO — T0 / T1 / T2 / T3
- **Tier rationale:** TODO — one sentence, required when the call was close
- **Owner:** TODO
- **Model and version:** TODO
- **Grounding or training data:** TODO — source and provenance

### Intended purpose

TODO: What it is for, who uses it, in what context, and what decision it informs.

### Out of scope

TODO: What it must not be used for. Be specific. This is the section that gets
cited when someone asks why the system was used the way it was.

### Foreseeable misuse

TODO: How a reasonable person could use it wrongly without any malice.

### Human oversight

TODO: Who reviews what, at which point, with what authority to override.
"A person looks at it" is not a definition.

### Impacts

TODO: Who is affected if it is wrong, how likely, how severe, and who absorbs the
cost of the error. Include people affected by the system who do not use it.

### Known limitations

TODO: What it is bad at. Stated plainly, without hedging.

### Disengage path

TODO: How to turn it off or revert to the non-AI path, who is authorized to do so,
and confirmation that this has been tested rather than assumed.

---

## Explainability

> *(Include if: AI/ML models are used. Delete if not applicable.)*
> TODO: Describe how an output can be explained to an affected individual and to a
> regulator, and what evidence is retained to support that explanation.

> *(Include if: AI impact tier is T3. Delete if not applicable.)*
> TODO: Describe how a person contests or appeals an output that affects them, who
> handles the appeal, and the expected turnaround.

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
