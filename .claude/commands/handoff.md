Write a session handoff note and prepare for context reset. Follow these steps in order.

---

## Step 1 — Read Current State

Read these files before writing anything:
- `AI-TASKS.md` — note which tasks changed status this session (look for [~] and recent [x])
- `CONTEXT.md` — acknowledge any prior handoff that was in effect

---

## Step 2 — Draft Handoff Note

Compose a structured handoff using this exact format:

```
# Session Handoff — [YYYY-MM-DD]

## Accomplished This Session
- [bullet per completed or meaningfully advanced item]

## In Progress — Pick Up Here
[~] [task name or description]
State: [describe exactly where this is — e.g., "file X is done, file Y still needs the Y section"]
Next action: [single sentence — the first thing to do to resume this task]

## Decisions Made
- [decision]: [reason — one line each, only decisions that would surprise a fresh session]

## Open Blockers
- [anything unresolved, waiting on user input, or deferred]
  (write "None" if clear)

## Next Step
> [One sentence. The exact first action for the next session.]

## Files Touched (non-obvious only)
- [path] — [why it matters]
```

Keep it compact — the goal is a cold-start brief, not a full log. Omit sections that are empty except Blockers (write "None" there explicitly).

---

## Step 3 — Write to CONTEXT.md

Write the completed handoff note to `CONTEXT.md`, replacing any prior content.

---

## Step 4 — Confirm and Hand Off

Show the written handoff to the user. Then output exactly:

```
Handoff written to CONTEXT.md.
Run /clear to reset the session. The next session will read this note automatically.
```

If the user asks to revise the handoff, update `CONTEXT.md` and confirm again.

---

## Notes

- Do not commit `CONTEXT.md` — it is session state, not source
- If AI-TASKS.md has changed tasks, ensure it is saved before writing the handoff
- The handoff replaces the session checkpoint signal — use /handoff instead of printing the checkpoint block when resetting mid-PBI
