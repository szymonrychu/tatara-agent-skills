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
the bundle, and `issue_write` to post. Every `<comment>` element carries an
`external_id` attribute - that is the id you cite when you report an approval,
and it is already in front of you.

Every turn must end with exactly one `submit_outcome` (see `tatara-mcp-outcome`).
The shape depends on your kind:

| your kind | the outcome |
|---|---|
| `clarify` | `submit_outcome(decision="implement"\|"close"\|"discuss", reason, approval_citations)` |
| `refine` | `submit_outcome(folds=[...], closes=[...], links=[...])` - a close is an entry in `closes[]`, with its `reason` |

## The judgment rubric

Read the issue AND the full conversation thread before deciding. The thread is
the authoritative record of human intent.

**implement** (clarify only) when, in YOUR reading, a maintainer has commented
something you can honestly read as a go-ahead, and nothing later in the thread
takes it back. There is no wordlist and no required form of words. "go ahead, I
approve!", "continue", "yep, do it" all approve; "hold on, this is wrong" and
"not until the tests pass" do not. You are the only reader of intent in this
loop, so read the comment, not a pattern.

**Your decision is a REPORT, and it must carry evidence.** Along with `reason`,
submit `approval_citations`: one `{id, quote}` per live Issue the Task owns THAT
A HUMAN HAS COMMENTED ON, where `id` is the `external_id` of the maintainer
comment you are citing as the go-ahead (an attribute in your bundle) and `quote`
is a VERBATIM substring of that comment's body. A live Issue with no human
comment at all needs no entry.

**The operator judges WHO, never WHAT IT MEANT.** For each citation it re-reads
that comment from its own mirror and refuses if the comment is not on that
issue, if the author is not a verified maintainer, if the author is the bot, if
your quote does not occur in the body it holds, or if that comment has already
been consumed as approval evidence. That is the whole check: four structural
facts, no intent.

**The veto is YOURS, because the operator does not check recency.** The comment
you cite does not have to be the newest one on the thread. Requiring that would
deadlock an ordinary conversation: a maintainer who writes "go ahead, I approve!"
and then "thanks - ping me when the PR is up" has plainly consented, but their
newest comment is not itself a go-ahead, so a recency rule would leave nothing
citable and park the Task forever. So YOU are the one who has to notice a
withdrawal: read every maintainer comment newer than the one you want to cite,
and if any of them takes the go-ahead back, submit `discuss`, not `implement`.
Nothing downstream will catch this for you.

- Approval STANDS (cite it): "thanks - ping me when the PR is up", "one more
  thing, the tests are flaky on main". Benign follow-up, not a reversal.
- Approval does NOT stand (submit `discuss`): "actually hold off", "wait, let me
  think about this", "stop, I misread the scope".

Three more ways to get this wrong:

- Paraphrasing the quote. It is substring-matched; a paraphrase is
  indistinguishable from a fabrication and is refused.
- Citing a comment that declines or defers, or one whose approval a later
  maintainer comment already withdrew.
- One approval on one issue does not approve a Task that owns four. Every live
  Issue (state `open`, status not `done`/`rejected`) that a human has commented
  on needs its own comment and its own citation. A live Issue with NO human
  comment at all needs neither - that is the carve-out below, not a gap, so a
  Task owning one commented and one uncommented issue cites exactly once.

Omit `approval_citations` only when NO human has commented on the issue at all -
that is the auto-approve carve-out for tatara's own proposals, and there is
nothing to cite. Never invent an entry.

If your report fails the operator's check, the Task parks at
`identity-unverified` (an HTTP 200, not an error). The refusal is visible to the
operator in its logs and metrics, but nothing useful reaches the issue thread -
a parked Task draws a forge notice only after a week, and it names the stage,
never what was missing. The maintainer just sees the Task stop, so a refusal is
silent rather than self-correcting. If you are not confident in a citation,
submit `discuss` instead. Not terminal, though: a fresh clarify turn can cite a
later maintainer comment. Do not resubmit the same citation.

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

- Reporting `implement` on an issue whose thread has no maintainer comment you
  can honestly read as a go-ahead, or reporting it without citing that comment.
- Citing a comment that hedges, defers, or declines, or one a later maintainer
  comment took back. The operator does not check recency; you are the veto.
- Paraphrasing an `approval_citations` quote instead of copying it verbatim.
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
