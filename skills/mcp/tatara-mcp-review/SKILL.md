---
name: tatara-mcp-review
description: >
  The review profile's tool-surface reference: what a kind=review Task may
  call (submit_outcome's review schema, scm_read, mr_write comment/reply,
  the code_* tools, memory_query/describe, plus the always-on set) and what
  it must never do (post a review, merge, or open an MR). Use whenever you
  are running as a kind=review task and must deliver a verdict on a PR/MR.
profiles: ["review"]
---

# tatara-mcp-review

You are in a `kind=review` task. The PR/MR head is checked out at
`/workspace/<owner>/<repo>`. This page lists every tool your profile has -
D.6 grants review 16 tools total (6 always-on + `submit_outcome` + 9 gated) - and nothing else
is available. Full schemas live in the cited skills; this page is the
review-specific index and workflow.

## Tool surface (complete)

Always-on (every profile): `task_get`, `task_context`, `task_note`,
`project_get`, `repo_list`, `report_internal_issue`. See
`tatara-mcp-platform`.

Gated to `review`:

| Tool | Use |
|------|-----|
| `submit_outcome` | Required, exactly once. Your review verdict. Schema below; full detail in `tatara-mcp-outcome`. |
| `scm_read` | Read issues, MR, comments, commits, CI. See `tatara-mcp-scm`. |
| `mr_write` | `action=comment` or `action=reply` ONLY - answering a human's inline thread. No `open`. See below and `tatara-mcp-scm`. |
| `mr_takeover_request` | Request to hand an external MR over to tatara for full agency. Maintainer-gated and re-validated server-side. Does not merge, approve, or push. See `tatara-mcp-scm`. |
| `code_search`, `code_context`, `code_graph`, `code_explain` | Full code-graph surface, all 4 tools. See `tatara-mcp-code-graph`. |
| `memory_query`, `memory_describe` | Read-only recall. See `tatara-mcp-memory`. |

**NOT available to `review`:** `task_list`, `issue_write`, `mr_write(action=open)`,
`memory_write`, `memory_entity`, `memory_edges`. Do not call them; they are
not registered for this profile and will fail.

## The key behaviour: you never post, you never merge

You form a verdict. The OPERATOR posts it and the OPERATOR merges. You have
no `mr_write(action="open"|"merge"|"approve"|"request_changes")` - those
actions do not exist on `mr_write` at all (D.2), and there is no merge tool
anywhere in your profile.

What the operator does with your verdict depends on whose PR you reviewed
(contract C.5, F.3):

- **The platform's own MR** (an implement Task cycling through `reviewing`):
  the operator posts a `COMMENT` review carrying your verdict, then merges on
  `approve` - **the merge is the approval of record**, not the review post.
  `request_changes` loops the Task back to `implementing`.
- **A human-authored PR** (you are a `review`-kind Task): the operator posts
  the `COMMENT` review either way, but **BOTH `approve` and `request_changes`
  end at `parked(awaiting-human)`.** A `review`-kind Task never spawns an
  implement pod, by any path - the human fixes their own PR and the human
  merges it. Write your findings for the person who opened the PR, not for a
  bot that will act on them. If they push and comment, you may be re-invoked
  on the new head, up to `maxHumanReviewRounds` (5).

`GitHub` 422s a self-approve and a self-request-changes; only `COMMENT` is
ever sent, on every verdict, on every PR. This is why there is no `approve`
tool for you to call - the "approval" your verdict produces is a stage
transition and, on the platform's own MRs, a merge - never a forge API call
you make yourself.

## Workflow

### Step 1 - Read and test the change

1. Read the diff: `git -C /workspace/<owner>/<repo> diff main...HEAD`.
2. Inspect changed files. Use `code_context`/`code_graph`/`code_explain`
   (`tatara-mcp-code-graph`) to trace impact before forming a verdict.
3. Build and run tests/linters if the repo supports it. Note what you ran
   and the exit code.
4. Check CI state with `scm_read(kind="ci", repo=..., number=...)` -
   `tatara-mcp-scm`. Do not approve an unmergeable or red-CI change.
5. Record the exact head SHA you checked out for every MR your Task owns -
   you need one entry per MR in `reviewed_shas` below.

Nothing you write to disk is kept. The workspace is transient.

### Step 2 - Call submit_outcome (required, exactly once)

The review schema (full detail in `tatara-mcp-outcome`):

```
submit_outcome(
  verdict="approve"|"request_changes",
  reviewed_shas=[{repo, number, sha}, ...],   # required, one per owned MR
  findings=[{repo, number, path, line, body, severity}, ...],  # required (>=1) when request_changes
  change_significance="major"|"minor"|"patch"  # optional, may only RAISE what the implementer declared
)
```

- `reviewed_shas` coverage is TOTAL - one entry per every MR your Task owns,
  not just the ones with findings. The operator re-reads the live head before
  accepting your verdict. If any MR moved since you checked it out, the
  operator does NOT accept the review: it refreshes the mirror to the live
  head and returns a normal, non-error result carrying `reason=head-moved`
  and the new `liveSHA`. On that result: `git fetch && git checkout
  <liveSHA>`, re-review the new diff, and resubmit `submit_outcome` with the
  NEW sha - never the same stale sha, that just loops. Full mechanics in
  `tatara-mcp-outcome`.
- `request_changes` needs at least one finding, or the human/implementer has
  nothing to act on.
- There is no `comment` verdict. Form a position: `approve` or
  `request_changes`.

### Step 3 - (Optional) task_note before you finish

If your context is growing large, or you want the next reviewer of this
same PR (a human-PR re-invoke) to have your notes, write
`task_note(kind="handoff", body=...)` before `submit_outcome`. See
`tatara-mcp-platform`.

## Replying to a human's inline comment

Use `mr_write(action="reply", repo, number, in_reply_to, body)` -
`in_reply_to` is the `externalId` from `scm_read(kind="comments")`. This is
the only write action review has besides a top-level `mr_write(action="comment")`.
Full semantics (deferred posting, no `open`) in `tatara-mcp-scm`.

## Anti-patterns

- Do NOT call `submit_outcome` more than once. The operator's writeback acts
  on the accepted call; a second call is not a retraction.
- Do NOT omit `reviewed_shas`, or omit an entry for any owned MR. A missing
  entry is a 400, not a silent skip.
- Do NOT resubmit the same stale sha after a `reason=head-moved` result -
  that loops forever. Fetch and check out the `liveSHA`, re-review the new
  diff, resubmit with the new sha.
- Do NOT call `submit_outcome(verdict="request_changes")` with an empty
  `findings` array.
- Do NOT call `mr_write(action="open")`. Your profile does not have it -
  opening MRs is `implement`'s job.
- Do NOT call `issue_write`, `memory_write`, `memory_entity`, `memory_edges`,
  or `task_list`. None are registered for `review`.
- Do NOT commit or push changes. The workspace is read-only for review; no
  changes are kept.
- Do NOT expect a merge, an approve, or a request-changes event to land on
  the forge. The operator sends `COMMENT` only, ever, on every verdict.
- Do NOT treat `approve` on a human PR as a green light to keep working the
  Task. It parks at `awaiting-human`, same as `request_changes` on a human
  PR. There is no fix-up round for you to drive.
- Do NOT finish without calling `submit_outcome`. A silent exit leaves the
  Task parked at `no-outcome`.
