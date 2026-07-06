---
name: tatara-lifecycle-conflict-resolution
description: "How an issueLifecycle turn resolves a merge conflict on its bot PR - merge origin/main (never rebase), resolve, push without force, or signal a terminal close. Read when the re-entry context reports a merge conflict."
profiles: ["lifecycle"]
---

# tatara lifecycle conflict resolution

TASK skill. The operator bounced this PR back to Implement because
`writer.Merge` returned a conflict. Your mandate is BINARY: reach one of two
terminal outcomes this turn. Never leave the PR parked, never stop half-done.

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

Close ONLY by signalling; the operator performs the close egress with a comment.

- Superseded (the fast path, no judgement needed): after `git merge
  origin/<default-branch>`, run `git diff origin/<default-branch>...HEAD`. If it
  is EMPTY, every change already landed on the default branch - the PR is
  superseded. Call `pr_outcome` with `action: close` and a reason naming it as
  superseded.
- Obsolete / genuinely unresolvable: if the PR is no longer wanted or the
  conflict cannot be resolved sensibly, still call `pr_outcome` with `action:
  close` and a clear reason. Do NOT park; do NOT give up silently.

## Invariants

- Two terminal outcomes only: a pushed resolved merge, or a `pr_outcome` close
  signal. There is no third "leave it" option.
- Agents never merge or close PRs directly. `pr_outcome` is a SIGNAL; the
  operator owns the merge/close egress.
- No attribution or session links in any commit, comment, or push.
