# Assurance Baseline

> Audience: anyone, human or AI, doing design, implementation, or documentation work in this repo.
> Status: distributed from `a-repo-template`. Do not hand-edit. Fix the template and re-sync.

This document is the single place where external framework obligations enter this
repo. It is organized by **workflow phase**, not by framework, because you are
always at a phase and never at a framework. Each obligation carries the control
IDs it satisfies so the audit trace falls out of the work instead of being
reconstructed afterward.

Two rules govern everything below.

1. **Depth scales with impact tier.** Declare the tier in `_engineer/REQUIREMENTS.md`.
   A tier 0 repo owes the software practices and nothing about AI. A tier 3 repo
   owes all of it. Applying tier 3 ceremony to a tier 0 repo is how a baseline
   becomes noise that everyone learns to skip.
2. **Cite the pin, not the framework.** Every citation below refers to a specific
   pinned version in the register. Framework identifiers get reused across editions
   with different meanings. An unqualified citation is a future wrong answer.

---

## Framework register

These are pinned. The pin is the point: it is what makes a citation in this repo
mean the same thing in two years that it meant the day it was written.

| Key | Framework | Pinned version | Published | Notes |
|-----|-----------|----------------|-----------|-------|
| `AIRMF` | NIST AI 100-1, Artificial Intelligence Risk Management Framework | 1.0 | 2023-01-26 | Still the only published version. A revision is in progress under the July 2025 AI Action Plan. |
| `GAI` | NIST AI 600-1, Generative AI Profile | 1.0 | 2024-07-26 | Companion profile to AI RMF 1.0. |
| `SSDF` | NIST SP 800-218, Secure Software Development Framework | 1.1 | 2022-02 | `PW.3` is retired in 1.1. Do not cite it. |
| `SSDF-A` | NIST SP 800-218A, Generative AI and Dual-Use Foundation Models Community Profile | Final | 2024 | Augments SP 800-218. Not standalone. |
| `LLM` | OWASP Top 10 for LLM Applications | **2026** | 2026-08-03 | Supersedes 2025. Always write `LLM01:2026` and never bare `LLM01`. See warning below. |
| `WAF` | Azure Well-Architected Framework | Live service docs | continuous | Not versioned. Recommendation IDs shift. Re-verify at each review. |
| `ISO42001` | ISO/IEC 42001:2023, Information technology, Artificial intelligence, Management system | Edition 1 | 2023-12-18 | Adopted as a design input. **Management clauses 4 to 10 only.** No Annex A control tags appear in this document, by decision. See warning below. |

### Standing warnings

- **OWASP identifiers were renumbered in the 2026 edition.** Six of ten positions
  moved, `System Prompt Leakage` was removed, and `LLM08:2026 Hidden Context
  Exposure` took its place. A bare `LLM05` means `Improper Output Handling` in the
  2025 list and `Data and Model Poisoning` in the 2026 list. The OWASP website
  still served the 2025 list as current at the time of pinning while the 2026 PDF
  was authoritative, so trusting the landing page is not sufficient.
- **ISO/IEC 42001 Annex A control tags are deliberately absent from this document.**
  The Annex A group titles could not be confirmed against ISO's own text, which sits
  behind a paid license, and rested on secondary sources alone. Citations that look
  precise and are not are worse than no citation, so they were removed rather than
  shipped with a caveat nobody would read at the point of use. Only the management
  clauses 4 to 10, confirmed from the official contents page, are cited.
  Do not restore Annex A tags from a blog post, a vendor summary, or a model's
  recollection. If Annex A mappings are wanted, buy the standard and verify against
  the text first.
- **Azure WAF AI workload guidance has no control identifiers.** It is organized as
  ten named design areas with unnumbered prose recommendations. Reference it by
  article name. Do not invent `AI:01`-style codes; they do not exist.
- **The pending AI RMF revision is directed to remove references to misinformation,
  DEI, and climate change.** `MEASURE 2.11` on fairness and bias is the citation in
  this document most likely to move. Expect to re-pin.

---

## AI impact tier

Declare exactly one tier in `_engineer/REQUIREMENTS.md` under Entity and
Environment. The tier is a property of what the system *does to people*, not of how
sophisticated the model is. A small model making consequential decisions outranks a
large model drafting internal text.

| Tier | Definition | Test | Examples |
|------|------------|------|----------|
| **T0** | No model inference anywhere in the system. | Would the system behave identically with every AI dependency removed? | Static sites, infrastructure modules, ETL with deterministic rules. |
| **T1** | Assistive. Every AI output is reviewed by a competent human before it has any effect outside the tool. | Can a wrong output reach anything without a person choosing to let it? If no, T1. | Drafting aids, internal summarizers, code assistants, developer tooling. |
| **T2** | Consequential. AI output reaches a client system, a record of decision, or an external party. Human review exists but is not line by line. | Does a wrong output create rework, a bad record, or an external correction? | Document classification into a system of record, client-facing summarization, extraction feeding downstream processing. |
| **T3** | Autonomous or rights-affecting. The system acts without a human in the loop, or its output materially affects a person's care, benefits, employment, or money. | Could a wrong output harm a specific identifiable person before anyone notices? | Clinical summarization, claims handling, eligibility, anything touching PHI where output shapes a decision. |

When genuinely torn between two tiers, take the higher one and write one sentence
in the MAP record explaining why it was close. That sentence is worth more later
than the tier itself.

Tier is not permanent. Adding autonomy or removing a review step raises it, and
raising the tier re-opens the design gate.

---

## Phase 1: intake and design

Applies before any code is written. This is the phase with the highest leverage and
the one most often skipped.

**All tiers**

- [ ] Security requirements are defined and recorded in `REQUIREMENTS.md` alongside
      functional requirements, not appended later. `SSDF PW.1`
- [ ] Threat model the design: what an attacker would target, what they would gain,
      what stops them. Record it. `SSDF PW.1` · `WAF SE:02`
- [ ] Data sensitivity is classified and labeled before storage design is fixed.
      `WAF SE:03` · `SSDF PW.1`
- [ ] Identity and access approach is decided at design time, not retrofitted.
      `WAF SE:05`
- [ ] Third-party components and services are assessed before adoption, including
      license and provenance. `SSDF PW.4` · `AIRMF GOVERN 6.1`

**T1 and above, additionally**

- [ ] **The AI system is recorded in the Aptica AI inventory** before first
      deployment. The inventory is the `a-governance` registry: add an `ai:` block
      to this artifact's registry entry declaring tier, models, human oversight, and
      the location of the MAP record. There is no second inventory. This is the one
      obligation with no tier exemption above T0 and no substitute.
      `AIRMF GOVERN 1.6`
- [ ] A **MAP record** exists in `docs/GOVERNANCE.md` covering intended purpose,
      context of use, and foreseeable misuse. Template below.
      `AIRMF MAP 1.1`
- [ ] Human oversight is defined explicitly: who reviews what, at which point, with
      what authority to override. "A person looks at it" is not a definition.
      `AIRMF MAP 3.5`
- [ ] Model and data provenance are recorded: which model, which version, which
      training or grounding data, sourced from where. `AIRMF MAP 2.3`

**T2 and above, additionally**

- [ ] Impacts are assessed for likelihood and magnitude, including impacts on people
      who are not users of the system. `AIRMF MAP 5.1`
- [ ] Excessive agency is bounded at design time. Enumerate what the system is
      permitted to do, and give it the narrowest tool and permission set that
      satisfies the requirement. `LLM03:2026` · `AIRMF MAP 3.5`
- [ ] A decommission and rollback path is designed, not assumed.
      `AIRMF MANAGE 2.4`

**T3 only, additionally**

- [ ] A **documented go or no-go decision** is recorded before build starts,
      naming the accountable owner. AI RMF explicitly contemplates deciding not to
      build. Exercising that option is a successful outcome, not a failure.
      `AIRMF GOVERN 4.1` · `AIRMF MAP 5.1`
- [ ] Affected-party recourse is designed: how a person contests or appeals an
      output that affects them. `AIRMF MANAGE 4.1`

---

## Phase 2: implementation

**All tiers**

- [ ] Secure coding practices followed; no secrets in source, config from
      environment. `SSDF PW.5`
- [ ] Secure settings by default. The out-of-box configuration is the safe one.
      `SSDF PW.9`
- [ ] Source integrity protected: branch protection on `main`, signed commits,
      no force push. `SSDF PS.1`
- [ ] Development environment is separated from production and access is controlled.
      `SSDF PO.5`
- [ ] Build and dependency resolution are pinned and reproducible. `SSDF PW.6`

**T1 and above, additionally**

- [ ] **All model output is treated as untrusted input.** Validate, encode, and
      bound it before it reaches a shell, a query, a filesystem, a browser, or
      another model. This is the single highest-value AI control in this document.
      `LLM10:2026` · `AIRMF MEASURE 2.7`
- [ ] Prompt injection is assumed, not defended against once. Any content the model
      reads that the operator did not write is an injection vector, including
      retrieved documents, tool results, and file contents.
      `LLM01:2026` · `AIRMF MEASURE 2.7`
- [ ] Sensitive data is kept out of prompts, logs, and telemetry unless there is a
      recorded reason it must be there. `LLM02:2026` · `WAF SE:03`
- [ ] Context that must not leak is not placed in a context window and trusted to
      stay there. `LLM08:2026`

**T2 and above, additionally**

- [ ] Retrieval and embedding sources are access-controlled per requesting
      principal. A shared index that ignores caller identity leaks across tenants
      by construction. `LLM09:2026` · `WAF SE:05`
- [ ] Grounding and training data integrity is protected against poisoning.
      `LLM05:2026`
- [ ] Consumption is bounded: token, cost, rate, and recursion limits are enforced
      server side. `LLM06:2026` · `WAF CO:01`
- [ ] Every AI-influenced action writes an audit record carrying model version,
      input reference, output, and the reviewing human where applicable.
      `AIRMF MEASURE 3.1` · `WAF SE:10`

---

## Phase 3: testing and evaluation

**All tiers**

- [ ] Human review of code for security defects, not only for correctness.
      `SSDF PW.7`
- [ ] Automated security testing in CI, and secret scanning on every push.
      `SSDF PW.8` · `SSDF PW.7`
- [ ] Design reviewed against the security requirements recorded in phase 1.
      `SSDF PW.2`

**T1 and above, additionally**

- [ ] An evaluation set exists that is separate from any development examples, and
      it is version controlled alongside the code. `AIRMF MAP 2.3`
- [ ] Evaluation covers the trustworthiness characteristics identified as material
      during MAP, not only accuracy. `AIRMF MEASURE 2.7`

**T2 and above, additionally**

- [ ] Adversarial testing against the current OWASP LLM list, minimally prompt
      injection and improper output handling.
      `LLM01:2026` · `LLM10:2026` · `AIRMF MEASURE 2.7`
- [ ] Failure modes are characterized and documented, not just pass rates. What does
      it get wrong, in what direction, and who absorbs that error?
      `AIRMF MEASURE 3.1`
- [ ] Evaluation approach was informed by someone with actual domain expertise in
      the deployment context. `AIRMF MEASURE 4.1`

**T3 only, additionally**

- [ ] Fairness and harmful bias evaluated and results documented, including
      performance across the subpopulations the system will actually encounter.
      `AIRMF MEASURE 2.11`
- [ ] Results reviewed by someone who did not build the system.
      `AIRMF GOVERN 4.1`

---

## Phase 4: pre-production

**All tiers**

- [ ] Release integrity is verifiable: tagged, signed, and reproducible.
      `SSDF PS.2` · `SSDF PS.3`
- [ ] Monitoring and observability configured before go-live, not after the first
      incident. `WAF OE:07` · `WAF RE:10`
- [ ] Security threat monitoring configured. `WAF SE:10`
- [ ] Safe deployment practice defined: staged rollout with a rollback that has been
      tested rather than assumed. `WAF OE:11`
- [ ] Vulnerability intake path exists and an owner is named. `SSDF RV.1`

**T1 and above, additionally**

- [ ] AI-specific monitoring is live: output quality, refusal and error rates, cost
      and token consumption, and drift indicators. `AIRMF MANAGE 4.1`
- [ ] The disengage path is tested. Confirm the system can actually be turned off or
      reverted to the non-AI path without a deployment.
      `AIRMF MANAGE 2.4` · `WAF OE:11`

**T2 and above, additionally**

- [ ] Users are informed they are interacting with an AI system and told what it can
      and cannot be relied on for. `AIRMF MAP 3.5`
- [ ] Incident response covers AI-specific failure, including how to respond to a
      confidently wrong output that has already reached a client.
      `AIRMF MANAGE 4.1` · `WAF OE:08`

---

## Phase 5: operations

**All tiers**

- [ ] Vulnerabilities assessed, prioritized, and remediated on an ongoing basis.
      `SSDF RV.2`
- [ ] Root cause analysis feeds back into practice rather than stopping at the fix.
      `SSDF RV.3` · `ISO42001 10`

**T1 and above, additionally**

- [ ] Post-deployment monitoring is reviewed on a defined cadence by a named owner.
      An unreviewed dashboard is not monitoring. `AIRMF MANAGE 4.1`
- [ ] Model or provider version changes are treated as changes requiring
      re-evaluation, not as transparent upgrades. A silently updated model is an
      unevaluated system. `AIRMF MEASURE 3.1`

**T2 and above, additionally**

- [ ] User feedback and override events are captured and periodically analyzed.
      Override rate is the most honest quality signal available.
      `AIRMF MEASURE 4.1` · `AIRMF MANAGE 4.1`
- [ ] Tier is re-confirmed at each significant change. Autonomy tends to increase
      quietly. `AIRMF MAP 1.1`

---

## MAP record template

Lives in `docs/GOVERNANCE.md`. Ten minutes for T1. Longer for T3, and worth it.

```markdown
## AI System Record

- **System:**
- **Impact tier:** T0 / T1 / T2 / T3
- **Tier rationale:** (one sentence, especially if the call was close)
- **Owner:**
- **Model and version:**
- **Grounding or training data:**

### Intended purpose
What it is for, who uses it, in what context.

### Out of scope
What it must not be used for. Be specific; this is the section that gets cited later.

### Foreseeable misuse
How a reasonable person could use it wrongly without malice.

### Human oversight
Who reviews what, at which point, with what authority to override.

### Impacts
Who is affected if it is wrong, how likely, how severe, and who absorbs the cost.

### Known limitations
What it is bad at. Stated plainly.

### Disengage path
How to turn it off or revert to the non-AI path, and who is authorized to do so.
```

---

## Maintenance

This baseline rots if nothing forces a look. Three triggers:

1. **Scheduled review each half year.** Re-verify the register against published
   sources and re-pin. Azure WAF and OWASP move without notice; OWASP renumbered
   inside a single year.
2. **On publication of a pinned framework's next version.** Specifically: the AI RMF
   revision now in progress, and any OWASP LLM edition after 2026.
3. **On tier change in any repo.** A repo crossing from T1 to T2 acquires
   obligations it did not previously owe.

Changes are made in `a-repo-template` and distributed by
`_engineer/dev-env/template_sync.py`. A downstream edit to this file will be
overwritten at the next sync and will not reach any other repo.
