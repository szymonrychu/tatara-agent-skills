---
name: tatara-implement-takeover
description: >
  Extra discipline for an implement turn that is nursing a taken-over MR (one the
  platform took ownership of from a human or another bot). Before you push,
  confirm the branch head still matches what tatara last pushed; if a foreign
  commit landed, stop and report rather than fighting it. Never force-push, never
  rebase. Read at the start of an implement turn on a takeover MR.
profiles: ["implement"]
---

# Implementing on a taken-over MR

Your task took over an MR that started outside tatara. You have full agency:
resolve conflicts, fix CI, make the requested changes, and get it to a clean
review. The head branch is the MR's own branch (it may not be a tatara/* name);
that is expected - push to it as usual.

## The pre-push guard

A human can push to this branch at any time. tatara must never clobber their
work, and a non-force push onto a diverged branch fails at the git level anyway.

Before you push:

1. Get the platform's last-recorded bot-push head from one of two surfaces:
   - `task_context()`: its `<merge_request>` element carries a `last_bot_head_sha`
     attribute (present only when the platform has recorded a bot push/takeover).
   - `scm_read(kind="mr", repo, number)`: returns the same value as
     `lastBotHeadSHA`.
   Compare the remote branch head (`git ls-remote origin <branch>`, returns the
   commit SHA) against that value.
2. If they match, push normally (see tatara-implement-conflict-resolution:
   merge the default branch to resolve conflicts, never rebase, never
   force-push).
3. If the branch head has moved to a commit tatara did not push, STOP. Do not
   push. A human took the branch back. Write a handoff note summarizing the
   divergence, then decline the task:
   - `task_note(kind="handoff", body="branch diverged: remote head no longer
     matches last_bot_head_sha - ownership flipped to external")`
   - `submit_outcome(action="declined", decline_reason="branch diverged: remote
     head no longer matches last_bot_head_sha - ownership flipped to external")`
   Do NOT retry with action=submitted (nothing was pushed) or force the change
   through.

**Fallback:** if `last_bot_head_sha` is absent or you are in any doubt, attempt a
normal (non-force) `git push` anyway. A non-fast-forward rejection from the git
server IS the divergence signal - treat it the same way as the check above. Then
run the same handoff/decline sequence.

## Hard rules (unchanged)

- Never `git push --force` or `--force-with-lease` (the pod denies it).
- Never rebase to resolve conflicts; merge origin/<default-branch> instead.
- You never merge and never close the MR - the operator merges on an approved
  review once tatara owns the MR.
