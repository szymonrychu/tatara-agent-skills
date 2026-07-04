---
name: handoff
description: Resume prior work via get_handoff at turn start and checkpoint via write_handoff before finishing, keyed by the wrapper's continuation-key preamble.
profiles: ["implement", "lifecycle", "incident", "brainstorm", "refine"]
---

# /handoff

Chat-backed continuation. Pods boot fresh with no conversation restore; the
only carried state is a compact handoff you read and write yourself via MCP.

## At start (resuming)

The wrapper prepends a continuation key to your first goal:
`Continuation key: <key>`.

1. Call `get_handoff{handoff_key: <that key>}`.
2. Present: load the returned `body` as your working context (current state,
   what's done, what's next, open questions, file/PR refs). Resume from there.
3. Absent (404): start fresh, no prior context to load.

## At end (checkpoint)

Before finishing the turn, call `write_handoff{handoff_key, project, repo,
kind, body}` with a COMPACT markdown summary:

- Current state (one line).
- What's done.
- What's next.
- Open questions.
- Key file/PR refs.

Keep it a summary an agent can act on in one read, not a log of everything you
did. Upsert overwrites the prior handoff for this key - write the whole
current picture, not a delta.

## refine only: grooming

`refine` additionally has `list_handoffs` and `delete_handoff`. When grooming
a project, list its handoffs and delete ones that are stale or done (issue
closed/resolved, clearly superseded, or aged with no matching open work).
Leave the rest - live handoffs are how `brainstorm` finds work to continue.

## Notes

- No `handoff_key` in the goal preamble (e.g. a healthCheck or one-off task):
  skip this skill, there is nothing to key a handoff to.
- Do not fall back to `/workspace/handoff.md` or any local file - the handoff
  lives in chat, not on disk, so the next pod (which may not share a
  filesystem) can read it.
