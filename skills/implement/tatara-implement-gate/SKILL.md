---
name: tatara-implement-gate
description: "STEP 0 of every implement turn on an unapproved issue: digest the ask, research it against the code, write the plan to task_note(kind=\"plan\") AND post it in the issue thread, then STOP and wait. On a go-ahead, call submit_outcome(action=approved) with the approving maintainer, the citation and the plan note id. Write no code until the operator returns granted:true."
profiles: ["implement"]
---

# The implement gate

You are ONE agent for the whole issue. You digest the ask, you agree a plan with
the maintainer, and then you write the code. This skill covers everything up to
and including the go-ahead. `tatara-implement-workflow` covers what happens
after.

**You do not write code before the gate opens.** Not a scaffold, not a branch,
not a "just to see if it works". The gate is the only thing standing between an
agent's reading of a thread and a merged, tagged, auto-deployed release.

**WORK YOU DO BEFORE THE GATE GRANTS IS LOST.** `mr_write(action="open")` is
REFUSED with `reason: "approval-required"` while any live issue this Task owns
carries no approval, and `submit_outcome(action="submitted")` is refused the same
way - so there is no merge request that can carry those commits and no reviewer
who will ever see them. This is not a warning about wasted effort; it is what the
operator does. Get `granted: true` FIRST, then write code.

## 1. Digest and research

Your turn-0 bundle carries every Issue your Task owns, each with its full
comment thread, plus every prior note. Do NOT re-crawl the forge to reconstruct
history that is already in your prompt.

Read the issue. Identify what outcome the human wants, what is ambiguous, and
what a reasonable engineer would need to know before implementing. Then ground
it in the code with `code_search`, `code_explain` and `code_context(rel="related")`,
and where the ask spans repos, one `explorer` subagent per implicated repo. See
`tatara-research-followup` for the research discipline, and obey its
silence-over-noise rule without exception: if no human has replied since your
last comment, post nothing.

If the code-graph tools return `MEMORY_DEGRADED`, read the on-disk repos
directly instead, report it ONCE, and continue the turn.

## 2. Write the plan, twice

The plan goes in TWO places and both are load-bearing:

    task_note(kind="plan", body="...")

is the continuation state and the thing the operator HASHES. Keep the id it
returns - you need it for `plan_note_id`.

    issue_write(action="comment", repo=..., number=..., body="...")

is what the maintainer actually reads. Post the same plan. If they diverge, the
maintainer approves one thing and the operator pins another.

A plan is: the scope, the repos in play, the approach, the constraints you found
in the code, and the 1-3 real ambiguities you still need answered. Do not ask
questions answerable from the issue text or the code.

## 3. Stop

Submit `submit_outcome(action="discuss", reason="...")` and stop. There is no
polling loop and no wall-clock wait. Your pod may stay warm; the operator will
give you the maintainer's reply as a new turn when it arrives. Sitting in a poll
loop burns your turn budget and buys nothing.

**Never answer your own last comment.** If the most recent comment on an issue
is your own with no human reply since, do not post again.

## 4. On a go-ahead, report it with evidence

    submit_outcome(action="approved",
                   reason="...",
                   approving_maintainer="<their login>",
                   plan_note_id="<the id task_note returned>",
                   approval_citations=[{"id": "...", "quote": "..."}])

- **You judge what the comment MEANS.** There is no wordlist. "go ahead, I
  approve!", "continue", "yep do it" are all approvals if that is what the
  maintainer meant.
- **The operator judges who wrote it and whether you quoted it honestly.** It
  re-reads that exact comment from its own mirror and refuses if the comment is
  not on that issue, if the author is not a verified maintainer, if the author is
  the bot, if your quote does not occur in the body it holds, or if that comment
  has already been consumed as approval evidence.
- `approving_maintainer` is a DECLARATION, not a second authority. The operator
  refuses with `approver-not-maintainer` if that login is not a maintainer, and
  with `approver-mismatch` if it is not the author of the comment you cited. The
  citation remains the sole authority; the login must simply AGREE with it.
- `plan_note_id` names the plan the maintainer approved. The operator hashes that
  note's body at grant and re-checks the hash before you write code. If you edit
  the plan after approval, the gate refuses.
- **An approval with NO maintainer comment behind it is PROVISIONAL and CAPPED.**
  A project sets `autoApproveMaxSignificance` (`off` | `patch` | `minor` |
  `major`); on the omit-both path the operator grants on provenance alone, then
  re-checks your declared `change_significance` against that ceiling at
  `action="submitted"` and refuses `over-auto-approve-ceiling` however green the
  PR is. Your assignment names the ceiling for this project. A citation from a
  real maintainer is never capped.
- One go-ahead on one issue does not approve a Task that owns four. Every live
  Issue that a human has commented on needs its own comment and its own citation.
  A live Issue with NO human comment at all needs neither.

**IT DOES NOT CHECK RECENCY, SO THE WITHDRAWAL VETO IS YOURS. Read every
maintainer comment newer than the one you want to cite. A benign follow-up
("ping me when the PR is up") leaves the go-ahead standing; one that takes it
back ("actually hold off") means `action=discuss` instead. Nothing downstream
catches this.**

## 5. Read the result before you do anything else

`submit_outcome(action="approved")` returns `granted: true, guidance: "...",
task: {...}` or `granted: false, reason: "...", declared: "...", guidance: "..."`.

**Both answers carry `guidance`, and it is the field to act on.** `reason` names
the fault; `guidance` names the next step, and the two do not follow from each
other - `plan-note-not-plan` is fixed in this turn, `no-maintainer-comment`
cannot be fixed by you at all.

- **`granted: true`** - the gate is open, and `mr_write(action="open")` is now
  unblocked. Go to `tatara-implement-workflow` and start writing code.
- **`granted: false`** - you are still alive and the conversation is still open.
  Do what `guidance` says. If it names a repair you can make in this turn
  (a wrong `plan_note_id`, a paraphrased quote, a mismatched
  `approving_maintainer`), make it and call `approved` again. If it says a human
  is needed, post the `reason` in the thread and submit `action="discuss"`. Do
  NOT resubmit the same citation unchanged; it will be refused the same way. Do
  NOT start writing code.

A refusal is not an error and not a park. It is the gate working.

## 6. Changing the plan after approval

If the work turns out to need a different plan, say so in the thread, write a
NEW `task_note(kind="plan")`, and go back to step 3. That is the cheap path and
it is the intended one. Do not keep coding against a plan you have abandoned in
order to dodge a second gate - the plan note is the continuation state, and a
stale one is worse than a second approval round.

## Anti-patterns

- Writing any code, opening any branch, or opening an MR before `granted: true`.
  The MR open is REFUSED, so the code has nowhere to go and the turn is spent.
- Reading `reason` and ignoring `guidance`, then submitting `discuss` for a
  refusal you could have repaired in the same turn.
- Declaring a `change_significance` above the project's auto-approve ceiling on
  an issue no human has commented on, and discovering it only at submit.
- Posting a plan comment without writing the matching `task_note(kind="plan")`,
  or writing a note whose body differs from the comment.
- Reporting `action="approved"` on an issue whose thread has no maintainer
  comment you can honestly read as a go-ahead.
- Citing a comment a later maintainer comment took back. The operator does not
  check recency; you are the veto.
- Paraphrasing an `approval_citations` quote instead of copying it verbatim.
- Setting `approving_maintainer` to someone other than the author of the comment
  you cited.
- Re-posting a comment that only re-requests approval when no human has replied.
- Answering under your own last comment.
- Polling or waiting for a human reply instead of submitting `discuss`.
- Re-crawling forge history already present in the turn-0 bundle.
