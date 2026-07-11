---
name: tatara-implement-conflict-resolution
description: "How an implement turn resolves a merge conflict on its bot PR - merge origin/main (never rebase), resolve, push without force, or signal already-done/decline, when review has bounced the Task back for an unmergeable MR. Read when the re-entry context reports a merge conflict."
profiles: ["implement"]
---

# tatara implement conflict resolution

TASK skill. `review` withheld approval and re-added `tatara-implementation`
because your PR is unmergeable (Decision 2 of the locked task-kind design:
any unmergeable MR under the Task routes back to `implement`). Your mandate
is BINARY: reach one of two terminal outcomes this turn. Never leave the PR
parked, never stop half-done.

## Never rebase

`git push --force` and `--force-with-lease` are hard-denied in this pod. A
rebase rewrites history and requires a force-push, so it CANNOT work here.
Always MERGE, never rebase.

## Path 1 - resolve and let the operator merge

1. `git fetch origin`
2. `git merge origin/<default-branch>` on the PR branch (the re-entry context
   names the branch and default branch).
3. Resolve each conflicting file guided by the originating issue intent (the
   re-entry context carries the issue scope). Keep the change minimal and
   faithful to the issue.
4. Commit the merge and `git push` (no `--force`, no `--force-with-lease`).
5. Stop. The operator re-attempts the merge (or native auto-merge fires) once
   your turn ends. You never merge the PR yourself.

## Path 2 - close

Close ONLY by signalling; the operator performs the close egress with a
comment. `implement` does not have a `pr_outcome` tool - use the two
`implement` terminal calls that already model these two cases:

- Superseded (the fast path, no judgement needed): after `git merge
  origin/<default-branch>`, run `git diff origin/<default-branch>...HEAD`. If
  it is EMPTY, every change already landed on the default branch - the fix
  is already present. Call `already_done` with a reason naming the commit(s)
  that already deliver it.
- Obsolete / genuinely unresolvable: if the PR is no longer wanted or the
  conflict cannot be resolved sensibly, call `decline_implementation` with a
  clear reason (this is the "should NOT be implemented" case, not the
  "insufficient context" case Phase 5 Step 4 forbids - a genuinely
  unresolvable conflict after a real attempt is a valid decline reason). Do
  NOT park; do NOT give up silently.

## Invariants

- Two terminal outcomes only: a pushed resolved merge (leading to
  `change_summary` on your next normal turn), or an `already_done` /
  `decline_implementation` signal. There is no third "leave it" option.
- Agents never merge or close PRs directly. `pr_outcome` is a SIGNAL; the
  operator owns the merge/close egress via whichever terminal tool you called.
- No attribution or session links in any commit, comment, or push.
