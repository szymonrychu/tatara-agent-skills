---
name: tatara-mcp-scm
description: Reading and writing the forge - issues, merge requests, comment threads, commits, CI. Use when you need to see an issue or MR, read a review thread, check whether CI is green, open an MR, or comment on one.
profiles: ["implement", "review", "clarify", "refine", "brainstorm", "incident", "documentation"]
---

# The forge, through three tools

Your pod has NO forge token. `gh` and `glab` are not available to you and will
not be. These three tools are your entire view of, and voice on, the forge.

## `scm_read` - and where the data actually comes from

    scm_read(kind="issues"|"mr"|"comments"|"commits"|"ci", repo, ...)

`repo` is a **Repository CR name** (`tatara-operator`), never an `owner/repo`
slug. `repo_list` gives you the names. `repo` is REQUIRED on every kind.

**`issues`, `mr`, `comments` and `commits` are served from tatara's own mirror of
the forge.** They are free, they are fast, and they are at most one sweep stale -
the response carries `lastSyncedAt` so you can see exactly how stale. Read them
as often as you like.

**`ci` is the ONE kind that leaves the cluster.** It is a POINT READ, not a
blocking watch, and the operator paces it to one real fetch per 20 seconds per
PR - a call inside that window is served from cache and marked `"cached": true`.
It returns the head SHA, the check list, mergeability, and - only for a check
that actually FAILED - the last 4000 bytes of its log. See
`tatara-pipeline-waiting` for how to poll it without killing your turn.

`number` is required for `kind=ci` and `kind=comments`. `is_pr` (kind=comments
only) reads the MR thread instead of the issue thread.

## `issue_write`

    issue_write(action="create"|"edit"|"close"|"comment", repo, number?, title?, body?, comment?)

- `close` REQUIRES a `comment`. Every close cites its reason.
- **Only `create` is synchronous** and hands back the issue `number`. `edit`,
  `close` and `comment` are DEFERRED: the call persists the intent and returns,
  and a reconciler posts it to the forge. You get nothing back to read from
  those three - do not immediately `scm_read` for what you just wrote and
  expect to find it.
- **There is no `status` parameter and no `labels` parameter.** Approval and
  every lifecycle label are operator-owned. You cannot mark an issue approved,
  and you cannot stamp the trigger label on one. This is not an oversight to be
  worked around; it is the gate.
- You may only write to an issue your Task controller-owns. Anything else is a
  409, and it is protecting a human's thread from two agents talking to each
  other on it.

## `mr_write`

    mr_write(action="open"|"comment"|"reply", repo, number?, title?, body?, in_reply_to?)

- **Three actions. There is no `merge`, no `approve`, no `request_changes`.**
  Merge is operator-only. Reviews are posted by the OPERATOR from your
  `submit_outcome` - see `tatara-mcp-outcome`. A hallucinated merge call has
  nowhere to land.
- `open` is IDEMPOTENT: if your Task already has an open MR for that repo on
  `task/<task-name>`, you get that MR back with `"existing": true` and the forge
  is not called. If your Task already MERGED an MR for that repo, `open` is
  REFUSED - you are about to open a duplicate PR for work that already shipped.
- **Only `open` is synchronous** and hands back a `number`/`url`. `comment` and
  `reply` are DEFERRED: the call writes the intent and returns; a RECONCILER
  posts it to the forge and appends the resulting comment by `externalId`. **You
  do not get a comment id back from this call**, and `scm_read(kind=comments)`
  will not show it back to you either until the reconciler has posted it - do
  not chain a `reply` to a comment you just wrote in the same turn.
- `reply` needs `in_reply_to`, which is an `externalId` you read from
  `scm_read(kind=comments)`. That is how you answer a human's inline review
  comment in its own thread instead of shouting into the PR's top level.
- `refine` may only use `action=comment`.

## Anti-patterns

- Do NOT invoke `gh` or `glab`. They are not available to you and never will
  be; these three tools are the entire forge surface.
- Do NOT `scm_read` immediately after a deferred write (`issue_write(edit|close|comment)`,
  `mr_write(comment|reply)`) expecting to see what you just wrote. It has not
  posted yet.
- Do NOT chain an `mr_write(reply)` to a comment you wrote earlier in the same
  turn - it has no `externalId` yet.
- Do NOT call `mr_write(open)` a second time for a repo your Task already has
  an open MR on; read the `existing: true` response from the first call instead.
- Do NOT attempt `mr_write(action="approve"|"request_changes"|"merge")`. These
  actions do not exist. A review verdict goes through `submit_outcome`, not
  through this tool.
