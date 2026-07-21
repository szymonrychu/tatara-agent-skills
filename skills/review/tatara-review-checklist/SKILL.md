---
name: tatara-review-checklist
description: >
  Prescriptive PR/MR review gate for review-stage Tasks: build + test + lint the
  checked-out head locally, evaluate correctness/security/quality/test
  dimensions, apply severity routing to pick approve or request_changes, report
  a per-MR head SHA with total coverage, and call submit_outcome before
  finishing. You never post the review and you never merge - the operator does
  both. Use on every review turn.
profiles: ["review"]
---

# tatara-review-checklist

TASK content. Follow these steps exactly, in order, on every review turn.

The head branch of the MR you are reviewing is already checked out at
`/workspace/<owner>/<repo>` when this turn starts. The workspace is transient:
nothing you write to disk is kept, so communicate exclusively through
`submit_outcome` (see `tatara-mcp-outcome`).

---

## Step 1 - Orient

Your turn-0 context bundle already carries every MR your Task owns: title, body,
head branch, head SHA, CI state, mergeability, and the full comment thread. Do
not re-crawl the forge for what is already in front of you.

**Takeover check (do this FIRST, before any review work, on EVERY review
turn):** scan the FULL comment thread in your bundle - not just whatever
triggered this specific turn - for any human comment on an external MR that
asks tatara to take the MR over, in any wording ("take over", "take it over
and fix", "you handle this", similar intent). This check does not depend on
why this turn started: a takeover comment posted between turns, or alongside
an unrelated CI/head-move event, still counts and must be handled the moment
you see it in the thread. If such a comment exists and you have not already
requested takeover for it, do NOT proceed with a normal review round and do
NOT conclude it is "outside what a review agent can act on" - that is a
platform capability you have via `mr_takeover_request`, not a limitation.
Invoke the `tatara-review-takeover` skill now and follow it: it judges the
intent and calls `mr_takeover_request` with that comment's external id. Only
fall through to the review steps below when no comment in the thread carries
unresolved takeover intent.

```
task_get()
```

confirms the Task and its stage. Then understand the diff scope, per MR:

```sh
cd /workspace/<owner>/<repo>
git log origin/main..HEAD --oneline
git diff origin/main..HEAD --stat
```

Read the diff (`git diff origin/main..HEAD`) for every file where the stat shows
meaningful change. Use `code_search` or `code_context(rel="entity", ...)` from
`tatara-mcp-code-graph` to navigate unfamiliar call sites without reading whole
files.

**Record the head SHA you actually checked out, per MR.** You will report it in
`reviewed_shas`, and the operator checks it against the live head. Write it down
now, not from memory at the end.

If CI state or mergeability has moved since the bundle was rendered, read it
fresh with `scm_read(kind="ci", repo=..., number=...)` - that is a point read,
not a watch; see `tatara-pipeline-waiting` for the polling discipline. An
unmergeable MR (conflict, or a failed required check) cannot be approved: run
Steps 2-3 for whatever evidence you can gather, but the verdict is
`request_changes`.

---

## Step 2 - Build, test, lint (required)

Do this for every changed repo under `/workspace`. Do not skip even if the diff
looks trivial. A failing test or lint error is a finding, not a reason to abort.

```sh
cd /workspace/<owner>/<repo>
mise install                            # install pinned toolchain once
mise run build    # or: mise exec -- go build ./...
mise run test     # or: mise exec -- go test ./...
mise run lint     # or: mise exec -- golangci-lint run
```

If the repo has no `.mise.toml` or no build/test/lint tasks, note
"no build targets found" and proceed.

Record exactly:
- Commands run (full invocation)
- Exit code
- Pass/fail count or first error line

This evidence goes verbatim into your outcome body.

---

## Step 3 - Evaluate dimensions

For each dimension: record a finding (pass, or severity + evidence). Skip none.

### 3a. Correctness

- Logic errors, off-by-ones, nil dereferences, race conditions
- Dropped or incorrectly wrapped errors (Go: `fmt.Errorf("ctx: %w", err)` expected)
- Contract violations (wrong function semantics, interface misuse)
- Data loss or corruption paths

### 3b. Security

- Secret or credential exposure (env vars logged, plaintext in YAML/values)
- Injection risks (shell, SQL, Go template)
- Auth/authz bypass or missing enforcement gate
- Insecure type assertions or deserialization

### 3c. Quality

- YAGNI/KISS violations: abstraction introduced for a single call site
- DRY violations: non-trivial logic copy-pasted more than twice
- Missing structured INFO log for every business action (with fields: action,
  resource_id, duration_ms where relevant) - platform rule
- Missing Prometheus counter/histogram/gauge for anything that counts, times
  out, or can fail - platform rule
- Naming clarity, dead code, unnecessary complexity

### 3d. Tests

- New behavior covered by tests?
- Go: table-driven tests with `t.Run`?
- Added tests actually compile and run (not skipped)?
- Build + lint still pass with the new tests in place?

---

## Step 4 - Severity routing

There are exactly TWO verdicts. There is no `comment` verdict: a review either
approves or requests changes, and a non-decision has no stage to go to.

| Condition | `verdict` |
|---|---|
| All dimensions pass, build + tests + lint pass | `"approve"` |
| Any correctness or security finding | `"request_changes"` |
| Quality or test gap that must be fixed before merge | `"request_changes"` |
| Quality nit you would not block on | `"approve"`, with the nit as a `low` finding |
| MR is unmergeable (conflict or failed required CI) | `"request_changes"` |

---

## Step 5 - You do not post your review. You REPORT it.

    submit_outcome(verdict="request_changes",
                   reviewed_shas=[{repo, number, sha}],
                   findings=[{repo, number, path, line, body, severity}])

The OPERATOR posts it to the forge - the verdict as the review body, each finding
as an inline comment at its path and line - and writes it into the next implement
pod's context. You have no `mr_write(approve)`. You have no merge.

`reviewed_shas` needs TOTAL COVERAGE: one entry per every MR your Task owns,
not only the ones with findings. A missing entry is a 400, not a silent pass.
Each entry is the head SHA you ACTUALLY CHECKED OUT AND READ. The operator
re-reads the live head before accepting your verdict: anything pushed after
your checkout would otherwise merge unreviewed under your approval.

If the head moved, the operator does NOT accept the review. It refreshes the
mirror to the live head and hands back a normal, non-error result carrying
`reason=head-moved` and the new `liveSHA` - text like "the head of <repo>#<n>
moved from <reviewed> to <live> ... was NOT submitted". On that result:

1. `git fetch && git checkout <liveSHA>` - resync your workspace to the live
   head, not the sha you already reviewed.
2. Re-review the NEW diff. The head moved, so the code under it changed.
3. Resubmit `submit_outcome` with the NEW sha in `reviewed_shas`.

Never resubmit the same stale sha - that just loops. Full mechanics in
`tatara-mcp-outcome`.

`severity` is `critical`, `high`, `medium` or `low`. A `request_changes` with
zero findings is refused - it tells the next pod nothing to fix, and it will
resubmit the same code.

**You never merge anything, and on a human's PR you never trigger a fix either.**
Whose MR you are reviewing changes what your verdict DOES:

| you are reviewing | `approve` | `request_changes` |
|---|---|---|
| the platform's own MR (an implement Task cycling through `reviewing`) | the OPERATOR merges. That merge is the approval of record - still the operator's action, never yours | back to `implementing`; an implement pod fixes your findings |
| a HUMAN's PR (you are a `review`-kind Task) | `parked(awaiting-human)` | `parked(awaiting-human)` |

On a human's PR BOTH verdicts park. The review is posted either way, and then
the human fixes and merges their own PR. **No implement pod will ever spawn on a
`review`-kind Task, by any path** - so do not write your findings as a work order
for a bot that will pick them up. Write them for the person who opened the PR. If
they push and comment, you may be re-invoked on the same PR to review the new
head, up to 5 rounds (`maxHumanReviewRounds`); after that the Task stays parked.

`change_significance` is OPTIONAL on your outcome. It may only RAISE the level
the implementer declared (`patch` < `minor` < `major`); a lower value is ignored.
Set it when the diff is more breaking than the implementer thought - a removed or
renamed public surface, an incompatible schema or config change.

Compose the outcome body from Steps 2-3:

1. One sentence: approving, or requesting changes.
2. Test run: commands, exit codes, pass/fail counts.
3. Findings per dimension. Anything you can pin to a file and a line goes in
   `findings[]` with `path` and `line` so the operator can post it inline;
   anything you cannot goes in the body with `repo`/`number` only.

---

## Step 6 - Replying to a human's inline comment

You have `mr_write(action="comment")` and `mr_write(action="reply")` only - see
`tatara-mcp-scm`. Use `reply` with the `in_reply_to` `externalId` you read from
`scm_read(kind="comments", is_pr=true)` to answer a human's inline thread in that
thread. Both are DEFERRED writes: the reconciler posts them, so you get no
comment id back and cannot chain a reply to something you wrote this turn.

Do not use `mr_write` to deliver your review. The review goes through
`submit_outcome`, once, and the operator posts it.

---

## Step 7 - Finish

After `submit_outcome` returns, the turn is complete. Hard stops:

- Do NOT `git commit` or `git push` anything. A review pod that pushes has become
  an implement pod.
- Do NOT attempt `mr_write(action="approve"|"request_changes"|"merge")`. Those
  actions do not exist.
- Do NOT open, edit, or close issues - `issue_write` is not in your profile.

Before you submit, write a `task_note(kind="handoff")` (see `handoff`): on the
platform's own MR it is what the next implement pod reads first.

If a platform tool failed (MCP error, tool unavailable) during the review, call
`report_internal_issue` with the exact error and the tool name, and note the
incomplete check in your outcome body with its impact on confidence.
