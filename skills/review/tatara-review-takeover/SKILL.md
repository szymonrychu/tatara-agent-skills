---
name: tatara-review-takeover
description: >
  How a review-stage agent handles a human asking, in natural language, for
  tatara to take over an external MR (resolve conflicts, fix CI, make changes,
  nurse to merge). Judge intent, verify the asker is a maintainer, and call
  mr_takeover_request with the comment's externalId - the operator re-validates
  server-side and never trusts your judgment alone. Refuse non-maintainers
  conversationally. Read when a comment on an MR you are reviewing reads like a
  hand-over request - but never for a merge request the platform already adopted
  into an upgrade Task, where the hand-over has already happened.
profiles: ["review"]
---

# Taking over an external MR

An external MR - someone else's PR - is review-only by default: you review, you
never push, and the operator never merges it. A project maintainer can hand it to
tatara for full agency, and this skill is how that ask is honoured.

**One exception, and it arrives automatically rather than being asked for.** On a
project that enables adoption, a merge request opened by a dependency bot is
taken over by the platform at intake, into an `upgrade` Task - no comment, no
maintainer, no request. If your goal names an open merge request, you are on one
of those: it is already tatara's, your `approve` merges it, and there is nothing
here to request. This skill does not apply to it. See `tatara-review-checklist`
Step 5's ADOPTED row for what each verdict does there.

## When this applies

You are reviewing an MR and some comment in the thread - whether it arrived as
an `mr_comment` event this turn or was already sitting in the comment history
you're re-reading - reads as a request for tatara to take the MR over and
drive it: "can you fix the conflicts and merge", "take this over", "please get
this green and land it". It is natural language, not a fixed command, and it
does not matter whether it was the specific thing that triggered this turn.

## What to do

1. Judge intent. Only a genuine hand-over request qualifies. A question, a
   review nit, or "can you take a look" is NOT a takeover - reply normally.
2. Read the comment's externalId from `scm_read(kind="comments", is_pr=true)`.
3. Call `mr_takeover_request(repo=..., number=..., comment_external_id=<that id>)`.
4. The operator re-checks server-side that the comment exists and its author is
   an allowed maintainer, never the bot. You do not need to check membership
   yourself - but do not call the tool for a comment you did not judge to be a
   maintainer's genuine hand-over, because a rejected request just wastes a turn.

You are making a REQUEST. You never merge and never push here. If the takeover
is accepted, a separate implement turn does the work; your review job continues.

## Never on an adopted merge request

A maintainer can still comment "take this over" on a merge request the platform
adopted, and it reads exactly like every other hand-over request in the thread.
Do not call `mr_takeover_request` for it. **The trap is that the call is not
refused:** owning the merge request is the tool's PRECONDITION - the operator's
first gate asks whether the calling Task controls that merge request, and an
adopted Task does - so the call passes the gate you might expect to stop it.

At best it resolves as a no-op and costs you a turn, because the platform already
owns what you asked for. At worst it is honoured: a fresh `takeover` Task is
minted, control of the merge request moves to it, and that Task enters at
`refined` with no issue behind it - the one state a takeover Task has no way
forward out of. The merge request then belongs to a Task that cannot act, and the
Task that could act is no longer its owner. Nothing reports this; the merge
request simply stops moving.

Answer that comment in the thread instead: tatara already owns this merge
request, and the review in flight is what decides it.

## Refusing a non-maintainer

If someone who is clearly not a maintainer asks tatara to take over, do not call
the tool. Reply in the thread that only a project maintainer can hand an MR over
to tatara, and continue your review. The operator would reject the request
anyway; refusing conversationally is clearer and cheaper.
