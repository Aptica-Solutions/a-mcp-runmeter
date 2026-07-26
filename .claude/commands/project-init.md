Follow these steps in order. Do not skip ahead or begin coding. This is an initialization and discovery flow.

---

## Step 1 — Load Context

Read these files before doing anything else:

1. `CLAUDE.md` (project root)
2. `_engineer/ENGINEER-README.md`
3. `_engineer/ENGINEER-FLOW.md`
4. `_engineer/ONBOARDING.template.md`
5. `_engineer/REQUIREMENTS.template.md`

---

## Step 2 — Prove Understanding

After reading, output a brief confirmation (8–12 bullet points) covering:

- The non-negotiable guardrails: secrets, PHI, destructive commands
- The "no code before approved survey" rule — state it explicitly
- The engineer flow sequence (ONBOARDING → REQUIREMENTS → Plan → Code → Tests)
- The task tracking convention: file, status symbols, PBI markers
- The commit convention (PBI boundary, format, co-author line)
- The session checkpoint signal and when to use it
- The ADO sync trigger and command
- Any files that are missing or unreadable (flag now, before proceeding)

Then ask the user: **"Do you confirm I have correctly understood the project rules? (yes / correct me)"**

Wait for the user's response. If they correct you, update your understanding and re-confirm before continuing.

---

## Step 3 — Interactive Survey

Ask each section of the survey one at a time. Do not present all questions at once.

Walk through these sections in order, waiting for the user's answer before moving to the next:

1. Project Identity (name, entity)
2. AI Tooling (which AI assistants will be used)
3. Project Type (backend, frontend, full stack, infra, etc.)
4. Tech Stack (backend language/framework, frontend, database, cloud)
5. Compliance Requirements (HIPAA, SOC 2, PCI DSS, None)
6. Log Destination (Application Insights, Log Analytics, file, other)
7. Auth Requirements (none, Entra/OAuth, API key, other)
8. Integration Points (external systems this project will connect to)
9. Special Concerns (constraints, risks, non-standard requirements)

After all sections are answered:

- Present the complete filled-in survey for the user to review
- Ask: **"Is this survey accurate? (yes to confirm / tell me what to change)"**
- Apply any corrections
- Write the completed survey to `ONBOARDING.md` in the project root
- Record sign-off by creating the marker `_engineer/.onboarding-complete`. This retires the onboarding gate for the repo — the survey-gate hook stops running once the marker exists. Commit the marker so the whole team skips the gate, or add it to `.gitignore` to keep sign-off per-developer.
- Confirm: "ONBOARDING.md written and onboarding signed off."

---

## Step 4 — Tooling Setup

Tell the user: "I will now run the init script to install and verify required tooling (gitleaks, Python venv, Node.js deps)."

Ask: **"Ready to run the setup script? (yes to continue)"**

On confirmation, run:

```
pwsh -NoProfile -File "_engineer/dev-env/init-repo-tooling.ps1"
```

If `pwsh` is not installed, tell the user: "PowerShell Core is required. Install it from https://aka.ms/powershell and re-run."

Run the script and report the output verbatim. Note any PASS / WARN / FAIL lines clearly.

If the script reports failures, help the user resolve them before proceeding to Step 5.

---

## Step 5 — Handoff

Output a ready summary table:

| Check | Status |
|-------|--------|
| Rules read and confirmed | ✓ / ✗ |
| ONBOARDING.md written | ✓ / ✗ |
| gitleaks installed | ✓ / ✗ |
| gitleaks scan clean | ✓ / ✗ |
| Python venv ready | ✓ / ✗ |
| pip deps installed | ✓ / ✗ |
| Node.js available | ✓ / ✗ (if applicable) |

Then output:

---

**Initialization complete.**

Next steps (in order):

1. Open `_engineer/REQUIREMENTS.template.md`, copy it to `REQUIREMENTS.md`, and fill it in based on the survey answers.
2. Start a new Claude Code session.
3. Paste this at the start: *"Do not write code. Review REQUIREMENTS.md and AI-TASKS.md, refine and prioritize the task list only."*
4. Have the AI build `AI-TASKS.md` from the approved requirements.
5. Confirm the task list, then switch to Code mode.

---

Do not begin planning or coding tasks during this session. This session's only output is `ONBOARDING.md` and a verified environment.
