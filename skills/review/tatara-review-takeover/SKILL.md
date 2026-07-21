---
name: tatara-review-takeover
description: >
  How a review-stage agent handles a human asking, in natural language, for
  tatara to take over an external MR (resolve conflicts, fix CI, make changes,
  nurse to merge). Judge intent, verify the asker is a maintainer, and call
  mr_takeover_request with the comment's externalId - the operator re-validates
  server-side and never trusts your judgment alone. Refuse non-maintainers
  conversationally. Read when a comment on an MR you are reviewing reads like a
  hand-over request.
profiles: ["review"]
---

# Taking over an external MR

An external MR (someone else's PR, including another bot's like Renovate) is
review-only by default: you review, you never push, the operator never merges
it. A project maintainer can hand it to tatara for full agency.

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

## Refusing a non-maintainer

If someone who is clearly not a maintainer asks tatara to take over, do not call
the tool. Reply in the thread that only a project maintainer can hand an MR over
to tatara, and continue your review. The operator would reject the request
anyway; refusing conversationally is clearer and cheaper.
