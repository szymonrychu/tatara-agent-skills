---
name: tatara-triage-judgment
description: "REFERENCE - judgment rubric and hard rails for the tatara implement and refine agents when deciding whether to keep an issue in conversation, reject it, or report that a maintainer approved the plan. Defines how to classify an issue and which submit_outcome shape carries the decision. Do not use as a procedure; use tatara-implement-gate for the implement approval harness, tatara-backlog-groomer for the refine harness, and tatara-research-followup for the research workflow."
profiles: ["implement", "refine"]
---

# tatara triage judgment

This is a REFERENCE skill. It defines the judgment rubric for classifying an
issue and selecting the correct outcome. The codebase research procedure lives in
`tatara-research-followup`; the outer procedures live in
`tatara-implement-gate` (implement) and `tatara-backlog-groomer` (refine).
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
| `implement` | `submit_outcome(action="approved"\|"rejected"\|"discuss", reason, approving_maintainer, plan_note_id, approval_citations)` |
| `refine` | `submit_outcome(folds=[...], closes=[...], links=[...])` - a close is an entry in `closes[]`, with its `reason` |

The implement kind is ONE agent for the whole issue: it conducts the
conversation, runs the gate above, and - once the gate opens - writes the code
and submits it with `action="submitted"`. There is no separate clarify kind and
no handoff between pods at approval time.

## The judgment rubric

Read the issue AND the full conversation thread before deciding. The thread is
the authoritative record of human intent.

**approved** (implement only) when, in YOUR reading, a maintainer has commented
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

`approved` also carries two fields the other actions do not:
`approving_maintainer`, the login of the maintainer whose comment you cited, and
`plan_note_id`, the id returned by the `task_note(kind="plan")` call that wrote
the plan they approved. Both are required. See `tatara-implement-gate`.

**The operator judges WHO, never WHAT IT MEANT.** For each citation it re-reads
that comment from its own mirror and refuses if the comment is not on that
issue, if the author is not a verified maintainer, if the author is the bot, if
your quote does not occur in the body it holds, or if that comment has already
been consumed as approval evidence. That is the whole check: structural facts,
no intent.

**Two refusals are about the declared login, not the citation.** The operator
returns `approver-not-maintainer` when `approving_maintainer` is not a verified
maintainer - this is the reporter-self-approval case, and the fix is not to
retry with a different login but to get a real maintainer to say go ahead in the
thread. It returns `approver-mismatch` when the login you declared is not the
author of the comment you cited - the fix there is yours and mechanical: set
`approving_maintainer` to that comment's author, because the citation is the
sole authority and the login must simply AGREE with it. Neither refusal is a
reason to change which comment you cite.

**The veto is YOURS, because the operator does not check recency.** The comment
you cite does not have to be the newest one on the thread. Requiring that would
deadlock an ordinary conversation: a maintainer who writes "go ahead, I approve!"
and then "thanks - ping me when the PR is up" has plainly consented, but their
newest comment is not itself a go-ahead, so a recency rule would leave nothing
citable and stall the Task forever. So YOU are the one who has to notice a
withdrawal: read every maintainer comment newer than the one you want to cite,
and if any of them takes the go-ahead back, submit `discuss`, not `approved`.
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
nothing to cite. Never invent an entry. That grant is PROVISIONAL: it ships only
up to the project's `autoApproveMaxSignificance` ceiling, checked against your
declared `change_significance` at `action="submitted"`.

If your report fails the operator's check, it returns `granted:false` with a
`reason`, a `guidance` string naming your next step, and you keep talking. Act on
`guidance`: some refusals are repairs you can make in this same turn. The refusal does NOT stop you and does NOT park
the Task: you are the same live agent, on the same open conversation. Post that
`reason` in the thread so the maintainer can see what was missing, submit
`action="discuss"`, and wait for their reply as a new turn. Do not resubmit the
same citation - it will be refused the same way. If you are not confident in a
citation in the first place, submit `discuss` rather than spending a round on it.

**rejected** (implement only) / **close** (refine, as an entry in `closes[]`)
when:
- A human has explicitly declined or closed the issue in the thread.
- The issue is a duplicate of an existing open issue (name the duplicate ref in
  your `reason`).
- The issue is out of scope, not actionable, or incompatible with the platform
  hard rules.

**discuss** (implement only) when:
- The issue is still under active discussion and no clear human intent has been
  expressed.
- You need more information from the maintainer to decide.
- This is a bot-proposed issue and no human has commented yet. Post nothing;
  submit `discuss` with a `reason` saying you are holding for a human. The next
  human comment reaches you as a new turn.

## Hard invariants

**MUST call `submit_outcome`.** A turn that ends without one does not quietly
stop: the Task ages out at `no-outcome`, the pod is deleted, and the work is
lost.

**You cannot approve, label, or set a status.** `issue_write` has no `status`
parameter and no `labels` parameter. Approval and every lifecycle label are
operator-owned. There is no label you can apply that advances an issue, and
applying one is not a thing you can do.

**No MRs, no code changes before the gate opens.** The rubric above governs the
pre-approval half of an implement turn and the whole of a refine turn. On
implement you may write code only after `submit_outcome(action="approved")`
returned `granted: true`; then `tatara-implement-workflow` takes over. refine
never writes code at all.

**The rationale is a comment you post, not a field on the outcome.** For a
rejection or a hold, whatever the humans need to read goes to the thread through
`issue_write(action="comment")` (or `issue_write(action="close", comment=...)`,
which REQUIRES its comment) BEFORE you submit. Make it useful: name the duplicate
ref, state why the issue is out of scope, or surface the specific questions you
need answered.

## Judgment anti-patterns

- Reporting `approved` on an issue whose thread has no maintainer comment you
  can honestly read as a go-ahead, or reporting it without citing that comment.
- Citing a comment that hedges, defers, or declines, or one a later maintainer
  comment took back. The operator does not check recency; you are the veto.
- Paraphrasing an `approval_citations` quote instead of copying it verbatim.
- Setting `approving_maintainer` to anyone other than the author of the comment
  you cited - that is `approver-mismatch`, and it costs a round.
- Reporting `approved` when only SOME of the Task's live Issues are approved.
- Reporting `discuss` when a maintainer has clearly approved, or when a human has
  clearly declined.
- Reporting `rejected` as a shortcut when the issue is legitimately actionable
  but needs clarification.
- Treating a `granted:false` as terminal. It is a normal result on a live
  conversation; post the reason and keep talking.
- Posting a comment on a bot-proposed issue that no human has engaged with yet -
  the silence is intentional.
- Closing an issue without a citing comment. `issue_write(action="close")`
  requires one; a close in `submit_outcome(closes=[...])` requires its `reason`.
- Completing the turn without calling `submit_outcome`.
- Making code changes or opening MRs before the gate returned `granted: true`.

## What belongs in tatara-research-followup vs here

`tatara-research-followup` describes how to research the codebase - which memory
and code-graph tools to use, how to validate a claim, how to connect the issue to
live code. This skill is the judgment layer: given research results, which
decision applies and why. Read both; let the rubric above decide the action after
the research is done.
