---
name: tatara-implement-conflict-resolution
description: "How an implement turn resolves a merge conflict on its MR - merge the default branch (never rebase), resolve, push without force, or decline - when the Task has been routed back to implementing with an unmergeable MR. Read when your context reports a merge conflict."
profiles: ["implement"]
---

# tatara implement conflict resolution

TASK skill. The review verdict was `request_changes` (or the merge attempt found
a moved head), and the operator routed your Task back to `implementing` because
an MR under it is unmergeable. Your mandate is BINARY: reach one of two terminal
outcomes this turn. Never leave the MR parked, never stop half-done.

## Never rebase

`git push --force` and `--force-with-lease` are hard-denied in this pod. A
rebase rewrites history and requires a force-push, so it CANNOT work here.
Always MERGE, never rebase.

## Path 1 - resolve and let the operator merge

1. `git fetch origin`
2. `git merge origin/<default-branch>` on the task branch (your bundle names the
   MR's head branch; `repo_list` names the repo's default branch).
3. Resolve each conflicting file guided by the originating issue intent - your
   bundle carries every Issue this Task owns and its full thread. Keep the change
   minimal and faithful to the issue.
4. Commit the merge and `git push` (no `--force`, no `--force-with-lease`).
5. Call `submit_outcome(action="submitted", ...)` per `tatara-implement-workflow`
   section 5, and stop. Your MR is already open - `mr_write(action="open")` is
   idempotent and returns it with `"existing": true` if you call it again. The
   operator re-attempts the merge once your Task is approved at review. **You
   never merge the MR yourself.**

## Path 2 - decline

Close ONLY by signalling; the operator performs the close egress with a comment.
There is no `mr_write(merge)`, no `mr_write(approve)`, and no close action at
all. The one terminal you have is `submit_outcome(action="declined")`.

- **Superseded (the fast path, no judgement needed):** after `git merge
  origin/<default-branch>`, run `git diff origin/<default-branch>...HEAD`. If it
  is EMPTY, every change already landed on the default branch - the fix is
  already present. Call
  `submit_outcome(action="declined", decline_reason="already delivered in <sha>")`,
  naming the commit(s).
- **Obsolete or genuinely unresolvable:** if the change is no longer wanted, or
  the conflict cannot be resolved sensibly, call
  `submit_outcome(action="declined", decline_reason="<why>")`. A genuinely
  unresolvable conflict after a real attempt IS a valid decline reason - unlike
  "insufficient context", which `tatara-implement-workflow` section 6a forbids.
  Do NOT stop silently.

## Invariants

- Two terminal outcomes only: a pushed resolved merge followed by
  `submit_outcome(action="submitted")`, or `submit_outcome(action="declined")`.
  There is no third "leave it" option - a Task that gets no outcome ages out at
  `no-outcome` and the work is lost.
- Agents never merge and never close MRs. Your outcome is a SIGNAL; the operator
  owns the merge and close egress.
- No attribution or session links in any commit, comment, or push.
- Before you stop, write `task_note(kind="handoff", body=...)` - see `handoff`.
