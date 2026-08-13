---
name: tatara-mcp-outcome
description: How to end your turn - submit_outcome, the one terminal tool. Use when you have finished the work your Task asked for and need to report the result, or when you are deciding whether you have finished.
profiles: ["*"]
---

# submit_outcome: the one terminal tool

You have exactly ONE outcome tool. It is called `submit_outcome`, and its shape
is chosen for you from your agent kind. You cannot call the wrong one, because
there is no other one.

**A Task that never receives an outcome does not quietly stop. It ages out at
`stageReason=no-outcome`, its pod is deleted, and the work is lost.** Submitting
an outcome is not optional and it is not the last thing you do if you have time.

## Your shape

### implement

```
submit_outcome(action="approved", reason, approving_maintainer, plan_note_id, approval_citations)
submit_outcome(action="discuss", reason)
submit_outcome(action="rejected", reason)
submit_outcome(action="submitted", title, body, change_significance, merge_order?)
submit_outcome(action="declined", decline_reason)
```

The first three are the GATE (see `tatara-implement-gate`); the last two are the
code (see `tatara-implement-workflow`). One agent, five actions, one turn each.

- `action="approved"` returns `{granted: true}` or
  `{granted: false, reason, declared}`. **`granted:false` is a normal result, not
  an error, and it does NOT stop you.** Post the reason in the thread and submit
  `action="discuss"`. Never write code on a `granted:false`.
- `reason` is required for `approved`, `discuss` and `rejected`. For `approved`,
  say in plain words WHO approved and WHY you read their comment as approval.
- `approval_citations` is required for `action="approved"` whenever a human has
  commented: ONE entry per LIVE issue this task owns THAT HAS A MAINTAINER
  COMMENT, each `{id, quote}`. A live issue no human has commented on at all
  needs no entry, so a task owning one commented and one uncommented issue
  submits exactly one entry.
  - `id` is the `external_id` of the maintainer comment you are citing as the
    go-ahead. It is already in your turn-0 bundle, on the
    `<comment external_id="...">` attribute. Copy it. Do not re-crawl to find it.
  - `quote` is a VERBATIM substring of that same comment's body. Copy it
    exactly, including punctuation and case.
  - YOU judge whether the comment approves. The operator does not read intent
    and has no wordlist. It re-reads the comment itself and REFUSES if that
    comment is not on that issue, if the author is not a verified maintainer, if
    the author is the bot, if your quote does not occur in the body it holds, or
    if that comment has already been consumed as approval evidence.
  - **The cited comment does NOT have to be the newest one, and the operator
    does not check that it is.** Withdrawal is YOUR call: if any maintainer
    comment newer than the one you cite takes the go-ahead back ("actually hold
    off"), submit `action="discuss"` instead. A benign newer comment ("thanks -
    ping me when the PR is up") leaves the approval standing.
  - Omit it only when NO human has commented at all - that is the auto-approve
    carve-out for tatara's own proposals, and there is no comment to cite.
- `approving_maintainer` must be the author of the comment you cited.
  A mismatch is refused with `approver-mismatch`; a non-maintainer login is
  refused with `approver-not-maintainer`.
- `plan_note_id` is the id `task_note(kind="plan")` returned. The operator hashes
  that note at grant and re-checks it before you write code.
- `change_significance` is `major` / `minor` / `patch`. YOU own this level. A
  reviewer may raise it. Nobody can lower it. It becomes the release tag.
- `merge_order` is REQUIRED the moment your change spans more than one repo:
  the Repository CR names, first-merged first. There is no default. Get it
  wrong and a downstream repo ships against an API that has not merged yet.
  With exactly one repo you may omit it.
- `action=declined` needs a real reason. "Not doing this" is not one.

### documentation

```
submit_outcome(action="submitted", title, body, change_significance, merge_order?)
submit_outcome(action="declined", decline_reason)
```

Same two fields and the same rules as implement's `submitted`/`declined` above.
Documentation deliberately has NO gate: it has no issue conversation to run and
no approval to report, so `approved`, `discuss` and `rejected` are not in its
schema at all and a call carrying one is refused before it leaves your pod.

### upgrade

```
submit_outcome(action="submitted", title, body, change_significance, merge_order?)
submit_outcome(action="declined", decline_reason)
```

The same two shapes and the same rules as documentation's above. Upgrade has no
gate either: a cron tick minted your Task, nobody filed an issue, and there is
no maintainer comment to cite, so `approved`, `discuss` and `rejected` are not
in its schema. `merge_order` matters more here than anywhere else - an upgrade
routinely spans `containers -> charts -> helmfile` and the order is the publish
dependency. `action="declined"` is a normal, common answer for this kind: no
eligible candidate, or every one already claimed by a live sibling Task. See
`tatara-upgrade-workflow`.

### review

```
submit_outcome(verdict="approve"|"request_changes", reviewed_shas[], findings[], change_significance?)
```

- `reviewed_shas` is REQUIRED, and coverage is TOTAL: one entry per EVERY MR
  your Task owns, not just the ones you found something wrong with. A missing
  entry is a 400, not a silent pass - a partial review that quietly approves an
  MR you never read is exactly the hole this field exists to close. Each entry
  is the head SHA you ACTUALLY CHECKED OUT AND READ. The operator re-reads the
  live head of every MR before accepting your verdict.

  If any MR moved since you checked it out, the operator does NOT accept the
  review. It refreshes the mirror to the new (live) head and returns a
  normal, non-error tool result carrying `reason=head-moved` and the new
  `liveSHA` - text like "the head of <repo>#<n> moved from <reviewed> to
  <live> since you checked out. Your review was of stale code and was NOT
  submitted; the mirror is refreshed to the new head." **That is not a
  failure, it is the gate working** - but you must act on it, not just retry
  the same call:
  1. `git fetch && git checkout <liveSHA>` - resync your workspace to the
     `liveSHA` in the result, not the sha you already reviewed.
  2. Re-review the new diff. The head moved, so the code under it changed;
     old findings may no longer apply and new ones may exist.
  3. Call `submit_outcome` again with the NEW sha in `reviewed_shas`.
  Never resubmit the same stale sha - the operator refuses it again for the
  same reason and you loop forever.
- `verdict=request_changes` needs at least one finding. A verdict with no
  findings tells the next implement pod nothing to fix, and it will resubmit
  the same code.
- **You do not post the review, and neither verdict is a merge.** The platform
  has one bot identity, so the forge refuses a self-approve. The OPERATOR posts
  a `COMMENT` review carrying your verdict and your findings as inline comments,
  on BOTH verdicts. **What happens after that depends entirely on whose MR you
  reviewed:**

  **The platform's own MR** (an implement Task cycling through `reviewing`):
  `approve` lets the operator merge - **the merge is the approval of record.**
  `request_changes` loops the Task back to `implementing` and an implement pod
  fixes your findings.

  **A HUMAN's PR** (you are a `review`-kind Task): BOTH verdicts end at
  `parked(awaiting-human)`. The review is posted either way; the human fixes
  their own PR; the human merges it. **There is no fix-up round for you to
  drive** - no implement pod will ever spawn on a `review`-kind Task, by any
  path. Do not write findings as if you are briefing a bot that will act on
  them; write them for the person who opened the PR. If they push and comment,
  you may be re-invoked on the same PR to review the new head - up to 5 times
  (`maxHumanReviewRounds`), after which the Task stays parked for a human.

  Either way you have no `mr_write(approve)` and no merge action; do not go
  looking for one.

### brainstorm

```
submit_outcome(action="propose", proposals=[{repo, title, body, kind}])   # 1..5
submit_outcome(action="skip", reason)
submit_outcome(action="exhausted", reason)
```

- `action="skip"` is transient: nothing THIS cycle, no lasting consequence.
- `action="exhausted"` means nothing worth proposing until the project itself
  changes. It **pauses brainstorming for the project** until a real change
  lands - a non-tatara commit to the default branch, a tatara commit from real
  task work, or a maintainer acting on an issue/MR. One report is enough;
  there is no threshold. Both `skip` and `exhausted` need a non-empty `reason`.

### incident

```
submit_outcome(action="file_issue", alert_rules[], reason, issue={repo,title,body,parent?})
submit_outcome(action="comment_issue", alert_rules[], reason, comment={repo,number,body})
submit_outcome(action="false_positive", alert_rules[], reason)
```

- `issue.parent={repo,number}` is optional: set it when your finding is
  genuinely-new-but-RELATED to an open tracker you surveyed. The operator
  links the new issue as a GitHub sub-issue under it.
- `action="comment_issue"` appends fresh evidence to an open incident tracker
  issue for the SAME incident instead of filing a near-duplicate - gated
  server-side to incident tracker issues only. See `tatara-incident-sre` /
  `tatara-incident-investigation` for the survey-then-decide protocol.

### refine

```
submit_outcome(folds[], closes[], links[])   # at least one non-empty
```

## Before you submit

- Have you written a `task_note(kind=handoff)`? Your outcome ends this stage; the
  note is what survives into the next one.
- Did you push? `submit_outcome(action=submitted)` with nothing pushed opens an
  MR against an empty branch.
