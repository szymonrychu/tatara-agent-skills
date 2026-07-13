---
name: tatara-triage-judgment
description: "REFERENCE - judgment rubric and hard rails for the tatara clarify and refine agents when deciding whether to keep an issue in conversation, close it, or report that a maintainer approved it. Defines how to classify an issue and which submit_outcome shape carries the decision. Do not use as a procedure; use tatara-clarify-conversation for the clarify harness, tatara-backlog-groomer for the refine harness, and tatara-research-followup for the research workflow."
profiles: ["clarify", "refine"]
---

# tatara triage judgment

This is a REFERENCE skill. It defines the judgment rubric for classifying an
issue and selecting the correct outcome. The codebase research procedure lives in
`tatara-research-followup`; the outer procedures live in
`tatara-clarify-conversation` (clarify) and `tatara-backlog-groomer` (refine).
This skill ADVISES; it does not drive.

## What you already have

Your turn-0 bundle carries every Issue your Task owns - title, body, author, and
the full comment thread, per repo - plus every prior note on the Task. The
operator assembles it from tatara's own mirror of the forge, so you do not need
to re-crawl anything to read the conversation. Use `scm_read` for what is NOT in
the bundle, and `issue_write` to post.

Every turn must end with exactly one `submit_outcome` (see `tatara-mcp-outcome`).
The shape depends on your kind:

| your kind | the outcome |
|---|---|
| `clarify` | `submit_outcome(decision="implement"\|"close"\|"discuss", reason)` |
| `refine` | `submit_outcome(folds=[...], closes=[...], links=[...])` - a close is an entry in `closes[]`, with its `reason` |

## The judgment rubric

Read the issue AND the full conversation thread before deciding. The thread is
the authoritative record of human intent.

**implement** (clarify only) when a maintainer has posted a comment that CONSISTS
OF an approval phrase - a whole line matching one of the project's
`approvalPhrases` (default: `lgtm`, `approve`, `approved`, `ship it`, `go ahead`,
`go`, `implement it`), from a login the operator can verify as a maintainer, and
never the bot.

**Your decision is a REPORT, not the approval.** The operator independently
re-reads the thread and re-runs the same check on EVERY live Issue the Task owns.
So cite WHO approved and WHERE in your `reason`. Two ways to get this wrong:

- A comment that CONTAINS an approval word but does not CONSIST of one ("I can't
  approve this until the tests pass") is NOT approval. The match is anchored to a
  whole line.
- One approval on one issue does not approve a Task that owns four. Every live
  Issue (state `open`, status not `done`/`rejected`) needs its own.

If your report fails the operator's check, the Task parks at
`identity-unverified`. That is not terminal: the next comment from a verified
maintainer that passes the grammar un-parks it automatically.

**close** when:
- A human has explicitly declined or closed the issue in the thread.
- The issue is a duplicate of an existing open issue (name the duplicate ref in
  your `reason`).
- The issue is out of scope, not actionable, or incompatible with the platform
  hard rules.

**discuss** (clarify only) when:
- The issue is still under active discussion and no clear human intent has been
  expressed.
- You need more information from the maintainer to decide.
- This is a bot-proposed issue and no human has commented yet. Post nothing;
  submit `discuss` with a `reason` saying you are holding for a human. The
  operator parks the Task at `awaiting-human` and the next human comment wakes it.

## Hard invariants

**MUST call `submit_outcome`.** A turn that ends without one does not quietly
stop: the Task ages out at `stageReason=no-outcome`, the pod is deleted, and the
work is lost.

**You cannot approve, label, or set a status.** `issue_write` has no `status`
parameter and no `labels` parameter. Approval and every lifecycle label are
operator-owned. There is no label you can apply that advances an issue, and
applying one is not a thing you can do.

**No MRs, no code changes in this turn.** clarify and refine are
classification/conversation kinds. Do not open merge requests, push commits, or
modify code. The implement stage handles execution.

**The rationale is a comment you post, not a field on the outcome.** For a close
or a hold, whatever the humans need to read goes to the thread through
`issue_write(action="comment")` (or `issue_write(action="close", comment=...)`,
which REQUIRES its comment) BEFORE you submit. Make it useful: name the duplicate
ref, state why the issue is out of scope, or surface the specific questions you
need answered.

## Judgment anti-patterns

- Reporting `implement` on an issue whose thread has no whole-line approval
  phrase from a verified maintainer - a discursive comment that merely mentions
  approval does not substitute.
- Reporting `implement` when only SOME of the Task's live Issues are approved.
- Reporting `discuss` when a maintainer has clearly approved, or when a human has
  clearly declined.
- Reporting `close` as a shortcut when the issue is legitimately actionable but
  needs clarification.
- Posting a comment on a bot-proposed issue that no human has engaged with yet -
  the silence is intentional.
- Closing an issue without a citing comment. `issue_write(action="close")`
  requires one; a close in `submit_outcome(closes=[...])` requires its `reason`.
- Completing the turn without calling `submit_outcome`.
- Making code changes or opening MRs.

## What belongs in tatara-research-followup vs here

`tatara-research-followup` describes how to research the codebase - which memory
and code-graph tools to use, how to validate a claim, how to connect the issue to
live code. This skill is the judgment layer: given research results, which
decision applies and why. Read both; let the rubric above decide the action after
the research is done.
