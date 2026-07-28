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
there, and `issue_write` for posting. The `external_id` you need for
`approval_citations` is already in your bundle - every `<comment>` element
carries it as an attribute. There is nothing to fetch.

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
   or the issue text. If the code-graph tools return `MEMORY_DEGRADED`, read the
   on-disk repos directly instead, report it ONCE, and continue the turn (see
   `tatara-mcp-memory`).
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
   - A maintainer's comment reads, to you, as a go-ahead, and nothing later in
     the thread took it back -> `decision="implement"`, citing that comment (see
     the approval section below).
   - The human has explicitly declined, or the issue is a duplicate or out of
     scope -> `decision="close"`.
   - Still ambiguous, or no approval yet -> `decision="discuss"`.

## Every Issue your Task owns, not just the one you were woken for

A Task can own several Issues across several repos. The approval gate is scoped
to ALL of them: the operator approves your Task only when EVERY live Issue it
owns (state `open`, status not `done` or `rejected`) carries its own cited
approval evidence. One go-ahead on one issue does not approve a Task spanning
four repos, and one citation does not cover four issues.

So before you report `decision="implement"`, walk every `<issue>` in your bundle
and check three things: that each has its own maintainer comment you read as
approval, that no later maintainer comment on that issue took it back, and that
you have an `approval_citations` entry for each. If any is still open, say
so in the thread - name the specific `<repo>#<number>` so the human knows where
the remaining go-ahead has to be posted - and submit `decision="discuss"`
instead.

The reverse also holds: acquiring a NEW issue after approval (via
`issue_write(action="create")`) resets the Task out of `approved` and back to
`clarifying`, because the gate's scope clause no longer holds. You cannot widen
your own mandate by adopting work after the gate.

## Shared: submit exactly one outcome

    submit_outcome(decision="implement"|"close"|"discuss", reason="...",
                   approval_citations=[{"id": "...", "quote": "..."}])

`reason` is REQUIRED on all three. `approval_citations` is required for
`decision="implement"` whenever a human has commented (see the approval gate
section below). There is no `comment` field on the outcome:
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

## The approval gate: a comment you judge, a citation the operator verifies

Your `decision="implement"` does NOT approve the work. It reports YOUR reading of
a maintainer's comment, and you must CITE that comment.

The split is: **you judge what the comment MEANS. The operator judges who wrote
it and whether you quoted it honestly.** There is no wordlist. "go ahead, I
approve!", "continue", "yep do it" - all of these are approvals if that is what
the maintainer meant, and you are the one who decides.

You carry the citation in `approval_citations`: one `{id, quote}` per live issue
the Task owns, where `id` is the `external_id` of the maintainer comment you are
citing as the go-ahead and `quote` is a verbatim substring of that same comment's
body. The `external_id` you need for `approval_citations` is already in your
bundle - every `<comment>` element carries it as an attribute. There is nothing
to fetch. Full schema in `tatara-mcp-outcome`.

The operator then re-reads that exact comment from its own mirror and refuses if:

- the comment is not on that issue;
- the author is not a verified maintainer, or is the bot;
- your `quote` does not occur in the body it holds;
- that comment has already been consumed as approval evidence.

That is the whole check. Four structural facts, no intent, and - this is the
part that matters most to you - **no recency check**.

### The veto is yours

The comment you cite does NOT have to be the newest one on the thread, and
nothing downstream will notice if a later comment took the approval back. That
is deliberate. Requiring the newest comment deadlocks an ordinary thread:

    maintainer: "go ahead, I approve!"
    maintainer: "thanks - ping me when the PR is up"

Consent there is unambiguous, but the newest maintainer comment is not itself a
go-ahead. Under a recency rule you could never cite anything, would submit
`discuss` every turn, and the Task would sit at `awaiting-human` forever with
nobody able to see why.

So the withdrawal check is YOUR job. Read every maintainer comment newer than
the one you want to cite and ask: does this take the go-ahead back?

- **Benign follow-up - approval stands, cite it.** "thanks - ping me when the PR
  is up". "one more thing, the tests are flaky on main."
- **Withdrawal - approval does NOT stand, submit `discuss`.** "actually hold
  off". "wait, let me think about this." "stop, I misread the scope."

"Is this later comment a withdrawal?" is an intent question, and intent is
always yours under this design. Get it wrong in the permissive direction and you
have started work a maintainer told you to stop.

So: read the whole thread, decide, then cite. If the operator's check disagrees,
the task parks at `identity-unverified` and a human is told what was missing.
That is not a dead end - a later comment from a verified maintainer, cited by a
later clarify turn, clears the gate - but do not resubmit the same citation.

**Do not paraphrase the quote.** Copy the substring exactly. A paraphrase is
indistinguishable from a fabrication and will be refused.

**Do not cite a comment that declines.** You are the only reader of intent in
this loop; a maintainer writing "not until the tests pass" is a refusal, and
citing it anyway - because it is the only maintainer comment on the thread, or
because it contains agreeable-sounding words - is the single worst thing you can
do here.

Omit `approval_citations` only when NO human has ever commented on the issue -
tatara's own auto-approved proposals have no maintainer comment, so there is
nothing to cite. Never invent a citation to fill the field.

You cannot set an issue's status. `issue_write` has no `status` parameter and no
`labels` parameter. That is the gate, not an oversight.

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
  maintainer approval comment of its own, or no citation for it.
- Paraphrasing the `quote` instead of copying the substring verbatim.
- Citing a comment that declines, defers, or makes the go-ahead conditional on
  something that has not happened yet. A go-ahead that merely carries a scope
  note ("yes, but keep it to one package") IS an approval; "not until the tests
  pass" is not. Read what it MEANS.
- Citing an approval a LATER maintainer comment took back. The operator does not
  check recency - if you do not catch the withdrawal, nothing does.
- Inventing an `approval_citations` entry for an issue no human has commented on.
- Telling the thread that a go-ahead has to be worded a particular way, or posted
  on a line of its own. It does not. There is no wordlist.
- Polling or waiting for a human reply instead of submitting `discuss` and
  stopping.
- Pushing code, opening an MR, or making any file edit - that is `implement`'s
  job, never clarify's.
- Re-crawling forge history already present in the turn-0 bundle. The
  `external_id` for a citation is an attribute on the `<comment>` element you
  were already given; there is nothing to fetch.
