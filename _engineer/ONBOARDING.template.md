# Project Intake Survey

## 1. Project Identity

- **Name:**
- **Entity:**

## 2. AI Tooling

Which AI assistants will be used?

- `[ ]` Claude Code
- `[ ]` GitHub Copilot
- `[ ]` OpenAI Codex
- `[ ]` Google Gemini
- `[ ]` Other: ___________

## 3. Project Type

- `[ ]` Backend API
- `[ ]` Frontend Application
- `[ ]` Full Stack
- `[ ]` Infrastructure / DevOps
- `[ ]` Data Pipeline / ML
- `[ ]` Other: ___________

## 4. Tech Stack

- **Backend:** ___________
- **Frontend:** ___________
- **Database:** ___________
- **Cloud:** `[ ]` Azure  `[ ]` AWS

## 5. Compliance Requirements

- `[ ]` HIPAA
- `[ ]` SOC 2
- `[ ]` PCI DSS
- `[ ]` None

## 6. AI Impact Tier

Pick exactly one. Full definitions in `_engineer/ASSURANCE.md`. This drives how much
assurance work the project owes, so answer it honestly rather than aspirationally.

- `[ ]` **T0** No model inference anywhere in the system
- `[ ]` **T1** Assistive. Every AI output is reviewed by a human before it has any effect
- `[ ]` **T2** Consequential. AI output reaches a client system, a record of decision, or an external party
- `[ ]` **T3** Autonomous or rights-affecting. No human in the loop, or output affects a person's care, benefits, employment, or money

If the choice is close, take the higher tier and note why here:

- ___________

## 7. Log Destination
- `[ ]` Application Insights
- `[ ]` Log Analytics workspace
- `[ ]` File Path
- `[ ]` Other sink (DataDog, Splunk)

## 8. Auth Requirements

- `[ ]` No auth required
- `[ ]` Entra / OAuth (interactive login)
- `[ ]` API key / bearer token
- `[ ]` Local Credentials from Vault
- `[ ]` Other: ___________

## 9. Integration Points

List external systems this project will connect to:

- ___________
- ___________

## 10. Special Concerns

Any known constraints, risks, or non-standard requirements?

- ___________

## 11. AI Cost Tracking

Choose `none`, `development`, `application`, or `both`. Development means AI
assistants used to build the project. Application means AI calls made by the
delivered system. Use a stable project ID and environment when enabled.

<!-- AI_COST_TRACKING_START -->
```json
{
  "mode": "none",
  "project_id": "",
  "environment": "development"
}
```
<!-- AI_COST_TRACKING_END -->

- **Approved telemetry scope and destination:** ___________
- **Access and retention owner/policy:** ___________
- **Development collector, if selected:** ___________
- **Application provider-call integration, if selected:** ___________

After confirming this survey, apply the choice with
`python _engineer/ai-cost/configure.py`. See `_engineer/ai-cost/README.md`.
MCP registration enables collection; it does not automatically intercept
provider calls or calculate an assistant's hidden usage.
