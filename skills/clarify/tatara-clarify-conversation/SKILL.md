---
name: tatara-clarify-conversation
description: "TASK harness for the clarify task kind: on a new issue, run a targeted brainstorm to digest the human's ask and post clarifying questions; on a comment on an existing issue, continue the conversation, close it, or report that a maintainer approved it. Ends every turn with submit_outcome(decision=...). Invoke FIRST on every clarify turn."
profiles: ["clarify"]
---

# tatara clarify conversation

The disciplined shell for a `clarify` turn. `clarify` fires on two distinct
triggers - a brand-new issue, or a new comment on an issue already in
conversation - and both paths end in exactly one `submit_outcome`: keep the
conversation open (`discuss`), close it (`close`), or report that a maintainer
approved it (`implement`). All conversation I/O is via the `tatara` MCP tools -
never git or gh for that. You MAY check out the workspace, a branch, or an
existing MR to read code and verify whether the ask is already addressed or
already coherent with what is on disk; this is read-only investigation, no
different from what an `explorer` subagent would do. You never push code or open
an MR (that is `implement`'s job) - checkout is for reading, not writing.

Your turn-0 bundle carries every Issue your Task owns, each with its full
comment thread, plus every prior note. Do NOT re-crawl the forge to reconstruct
history that is already in your prompt - reserve `scm_read` for what is not
there, and `issue_write` for posting.

## Branch A - new issue (targeted brainstorm + digest)

1. **Digest the human's ask.** Read the issue title, body, and any existing
   comments from the bundle. Identify: what outcome the human wants, what is
   ambiguous, and what a reasonable engineer would need to know before
   implementing this.
2. **Targeted brainstorm, grounded in code.** Unlike `tatara-council-brainstorm`
   (which proposes NEW work from platform-wide scanning), this is narrow and
   reactive: use the code-graph tools (`code_search`, `code_explain`,
   `code_context(rel="related")`) and, where the ask spans repos, one `explorer`
   subagent per implicated repo (via the `Agent` tool, `model: haiku`, `effort:
   low`) to confirm the ask is technically coherent and to surface the 1-3 real
   ambiguities worth asking about. Do not ask questions answerable from the code
   or the issue text.
3. **Post clarifying questions** (or, if nothing is genuinely ambiguous, a short
   confirmation of scope plus your proposed approach) with
   `issue_write(action="comment", repo=..., number=..., body=...)`, per
   `tatara-mcp-scm`. Then apply `tatara-triage-judgment`'s rubric: is this issue
   already clear enough and already approved (Branch B step 3), or does it
   genuinely need a round of human input?
4. **Submit your outcome**, per the shared section below.

## Branch B - comment on an existing issue

1. **Read the full thread** (already in your bundle) and determine: has a human
   replied since your last comment, and if so, what did they say?
2. **Research and refine.** Delegate to `tatara-research-followup` for the
   research-the-gaps / respond-in-thread / idle-discipline procedure. Its
   silence-over-noise rule applies here without exception: if no human has
   replied since your last comment, post nothing.
3. **Decide the outcome** using `tatara-triage-judgment`'s rubric:
   - A maintainer has posted a comment that CONSISTS OF an approval phrase ->
     `decision="implement"` (see the approval section below).
   - The human has explicitly declined, or the issue is a duplicate or out of
     scope -> `decision="close"`.
   - Still ambiguous, or no approval yet -> `decision="discuss"`.

## Every Issue your Task owns, not just the one you were woken for

A Task can own several Issues across several repos. The approval gate is scoped
to ALL of them: the operator approves your Task only when EVERY live Issue it
owns (state `open`, status not `done` or `rejected`) carries its own approval
evidence. One `lgtm` on one issue does not approve a Task spanning four repos.

So before you report `decision="implement"`, walk every `<issue>` in your bundle
and check that each has its own maintainer approval comment. If any is still
open, say so in the thread - name the specific `<repo>#<number>` so the human
knows where the remaining go-ahead has to be posted - and submit
`decision="discuss"` instead.

The reverse also holds: acquiring a NEW issue after approval (via
`issue_write(action="create")`) resets the Task out of `approved` and back to
`clarifying`, because the gate's scope clause no longer holds. You cannot widen
your own mandate by adopting work after the gate.

## Shared: submit exactly one outcome

    submit_outcome(decision="implement"|"close"|"discuss", reason="...")

`reason` is REQUIRED on all three. There is no `comment` field on the outcome:
anything you want the humans to read, you post yourself with
`issue_write(action="comment")` BEFORE you submit.

**You do not wait.** There is no polling loop and no wall-clock wait for a human
reply. `decision="discuss"` parks the Task at `awaiting-human` and your pod
stops. When a human comments, the operator un-parks the Task and spawns a fresh
clarify pod with the new comment in its bundle. Sitting in a poll loop burns your
turn budget and buys nothing.

**Never answer your own last comment.** If the most recent comment on an issue is
your own (bot-authored) with no human reply since, do not post again - that is a
self-triggering loop. The operator enforces the same invariant structurally: bot
events are never enqueued, so your own comment can never wake your own Task.
`refine` is the ONLY kind in this repo permitted to comment under its own prior
comment, and only for a narrow scope-change / already-delivered case.

## The approval gate: a comment, verified by the operator

Your `decision="implement"` does NOT approve the work. It reports YOUR judgement
that a maintainer approved it. The operator then independently re-reads the
thread and checks BOTH the identity (a verified maintainer, never the bot) AND
the wording (a whole line that CONSISTS of an approval phrase - "go ahead", not
"I can't approve this until the tests pass") on EVERY issue the Task owns.

So cite WHO and WHERE in your `reason`. If the operator's check disagrees with
your report, the Task parks at `identity-unverified` and a human is told what was
missing. This is not a dead end: a later comment from a verified maintainer that
passes the same anchored whole-line grammar re-triggers the check and un-parks
the Task on its own - nobody has to resubmit an outcome for it.

You cannot set an issue's status. `issue_write` has no `status` parameter and no
`labels` parameter. That is the gate, not an oversight.

The phrases are the project's `approvalPhrases` (default: `lgtm`, `approve`,
`approved`, `ship it`, `go ahead`, `go`, `implement it`), matched anchored
against a whole normalised line - so when you ask for a go-ahead, ask for it as
a line on its own, and never tell the thread that a discursive "sounds good to
me, but check the tests first" is sufficient. It is not.

## Seed the implement pod with a note

Before `submit_outcome(decision="implement")`, write what you settled -
`task_note(kind="handoff", body=...)`. Notes ARE the continuation state (see
`handoff`); the implement pod that picks this Task up reads them in its bundle.
Scope, the repos in play, the approach you agreed in-thread, the constraints the
human named: that goes in the note, not in a `plan` argument (there is none).

## Anti-patterns

- Asking a clarifying question answerable from the issue text or the code.
- Re-posting a comment that only re-requests approval or restates prior analysis
  when no human has replied (silence-over-noise violation).
- Answering under your own last comment.
- Reporting `decision="implement"` when some live Issue your Task owns has no
  maintainer approval comment of its own.
- Treating a discursive comment that merely mentions approval as approval, or
  telling the thread that it unblocks the pipeline. Only a whole-line approval
  phrase from a verified maintainer does.
- Polling or waiting for a human reply instead of submitting `discuss` and
  stopping.
- Pushing code, opening an MR, or making any file edit - that is `implement`'s
  job, never clarify's.
- Re-crawling forge history already present in the turn-0 bundle.
