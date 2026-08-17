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

**Not on an ADOPTED merge request.** If your goal names an open merge request
that the platform already took over into this Task (Step 5's adopted row), the
hand-over has already happened and there is nothing to request. Do NOT call
`mr_takeover_request` there whatever the thread says - it is not refused on an
adopted merge request, because owning the merge request is that tool's
precondition rather than its blocker, and the damage is described in
`tatara-review-takeover`. Reply in the thread that tatara already owns the merge
request, and carry on with your review.

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
- **Register and humor** (Markdown changes only). Does the page sit in the
  right register per `tatara-writing-voice` - warm for `docs/index.md`,
  `docs/concepts/**`, `docs/getting-started/**`, `docs/explainers/**` and
  section index pages; clinical for `docs/reference/**`, `docs/workflows/**`,
  `docs/architecture/**`, `docs/components/**` and `docs/operations/**`
  including runbooks; `docs/appendix/**` never edited at all? **A warmed-up
  clinical page is the failure mode to watch for**, and it is now more likely
  than it used to be: the documentation pod's Phase 2 sorts the whole surface
  by staleness, so it lands on `components/` and `architecture/` pages far
  more often than on the newcomer path, and Vale is path-scoped to the warm
  half so it never runs on them. Second person, contractions, or a lead
  rewritten to "what you get" on a reference page is a finding even when every
  sentence is true. Then: is the prose CLEARER than what it replaced, not
  merely compliant with the banned list - a Vale-clean rewrite that explains
  less is a regression, and Vale cannot see that either. If a line attempts a
  joke and you are unsure it lands, say so: the humor gate is the one tone
  rule no tool checks, and this checklist is where it gets checked. Severity
  routing: `low` unless the register is flatly wrong for the path (a runbook
  step written in second-person banter), which is `medium`.

### 3d. Tests

- New behavior covered by tests?
- Go: table-driven tests with `t.Run`?
- Added tests actually compile and run (not skipped)?
- Build + lint still pass with the new tests in place?

### 3e. The merge request description (on a dependency MR, this IS the review)

Every dimension above is diff-shaped. On a merge request opened by a dependency
bot the diff is not the change: the description carries the changelog and release
notes for the bump, and **that text exists in no other artifact this platform
produces** - a dry-run discovery pass never fetches release notes at all. Judge
it against one question: does it name a breaking change, a renamed or removed
configuration key, a required migration, a raised minimum version, or a mandatory
intermediate release?

If it does, `request_changes` and name the key, the migration or the manifest.
Your findings are the upgrade agent's work order, and "read the release notes" is
not a work order. If it does not, approve - that is the common answer on a
dependency bump and it is the correct one.

The body is the bot's summary of what it fetched, not the upstream source. Follow
`sourceUrl` and read the release pages yourself before you conclude nothing
breaks: a changelog that mentions nothing breaking is weak evidence, not
clearance.

**An empty `<body>` in your bundle usually means elided, not absent.** When the
bundle runs out of byte budget it truncates bodies, and its last-resort step
drops them to nothing, leaving `<body truncated="true">` with nothing inside.
Re-read it with `scm_read(kind="mr", repo=..., number=...)`, which returns the
full mirrored body, before concluding the changelog said nothing.

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
| the platform's own MR (an implement Task cycling through `awaiting-review`) | the OPERATOR merges. That merge is the approval of record - still the operator's action, never yours | back to the implement agent, which fixes your findings and pushes again |
| an ADOPTED third-party dependency MR (a bot opened it; the platform took it over into an `upgrade` Task) | the OPERATOR merges, exactly as on the platform's own MR. This is the COMMON and correct answer: most dependency bumps oblige nothing beyond the pin | back to the UPGRADE agent, which pushes complementary commits onto that same branch |
| a HUMAN's PR (you are a `review`-kind Task) | `parked(awaiting-human)` | `parked(awaiting-human)` |

Tell an adopted MR apart by its goal: it names the merge request number, its
title and its branch, and it says that branch is your `TASK_BRANCH`. An ordinary
`review`-kind Task's goal names none of those. **If your goal names an open merge
request you are on the adopted row, not the human row** - and the middle row is
where a third party's merge request gets merged on your approve. Reason "this is
not the platform's own MR, so both verdicts just park" there and you have
approved a merge, not parked one. Approve on the evidence in front of you
(Step 3e), never on the assumption that somebody downstream looks again.

On a human's PR BOTH verdicts park. The review is posted either way, and then
the human fixes and merges their own PR. **No implement agent will ever run on a
`review`-kind Task, by any path** - so do not write your findings as a work order
for a bot that will pick them up. Write them for the person who opened the PR. If
they push and comment, you may be re-invoked on the same PR to review the new
head, up to 5 rounds (`MaxHumanReviewRounds`); after that the Task stays parked.

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

**A verdict does not end you.** Your pod stays live after `submit_outcome`. If
the head moves and you are asked to review again, you are the SAME agent with
the same notes - diff the new head against your PRIOR findings note rather than
re-reviewing from scratch, and say in your findings which of your earlier points
were addressed. Repeating a finding the implementer already fixed is how a
review loop becomes a ping-pong.

Concretely, on every round after the first:

1. Read your own prior `task_note(kind="handoff")` and the findings you already
   submitted. They are in your bundle; they are not something to re-derive.
2. `git diff <the sha you last reviewed>..<the new head>` - that is the review
   surface for this round, not `origin/main..HEAD`. Read the whole diff against
   `origin/main` only if the branch was rewritten under you.
3. Verdict on the WHOLE MR as it now stands, but write the findings as a delta:
   what your last round asked for and did not get, plus anything the new commits
   introduced.

You live until the MR is merged or the Task ends. A new comment on the thread, a
new push, or a CI state change arrives as a NEW TURN on this same pod - there is
no polling loop to run and no wall-clock wait to sit through. Stop the turn, and
the next event wakes you with your context intact.

After `submit_outcome` returns, the turn is complete. Hard stops:

- Do NOT `git commit` or `git push` anything. A review pod that pushes has become
  an implement pod.
- Do NOT attempt `mr_write(action="approve"|"request_changes"|"merge")`. Those
  actions do not exist.
- Do NOT open, edit, or close issues - `issue_write` is not in your profile.

Before you submit, write a `task_note(kind="handoff")` (see `handoff`): on the
platform's own MR it is what the implement agent reads first, and on a later
round it is what YOU diff against.

If a platform tool failed (MCP error, tool unavailable) during the review, call
`report_internal_issue` with the exact error and the tool name, and note the
incomplete check in your outcome body with its impact on confidence.
