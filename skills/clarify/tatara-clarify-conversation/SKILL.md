---
name: tatara-clarify-conversation
description: "TASK harness for the clarify task kind: on a new issue, run a targeted brainstorm to digest the human's ask and post clarifying questions; on a comment on an existing issue, continue the conversation or hand off to implement via the label swap. Live-polling pod with a 1h wall-clock wait; never answers its own last comment. Invoke FIRST on every clarify turn."
profiles: ["clarify"]
---

# tatara clarify conversation

The disciplined shell for a `clarify` turn. `clarify` fires on two distinct
triggers - a brand-new issue, or any new comment on an issue already in
conversation - and both paths end in one of three outcomes: keep the
conversation open (post + wait), close it, or hand off to `implement`. All
conversation and lifecycle I/O is via the `tatara` MCP tools - never git or
gh for that. You MAY check out the workspace, a branch, or an existing
MR/PR to read code and verify whether the ask is already addressed or
already coherent with what's on disk; this is read-only investigation, no
different from what an `explorer` subagent would do. You never push code
or open a PR (that is `implement`'s job after handoff) - checkout is for
reading, not writing.

The operator injects the FULL cross-repo umbrella context for this Task at
turn 0 (every linked issue + its full comment thread, across every repo in
the project scope, per Decision 7 of the locked task-kind design). Do NOT
re-crawl SCM (looping `comment_on_issue`/list-style calls) to reconstruct
history that is already in your prompt - use MCP calls for research and for
posting, not for re-fetching what you already have.

## Branch A - new issue (targeted brainstorm + digest)

1. **Digest the human's ask.** Read the issue title, body, and (if any)
   existing comments from the injected context. Identify: what outcome the
   human wants, what is ambiguous, and what a reasonable engineer would need
   to know before implementing this.
2. **Targeted brainstorm, grounded in code.** Unlike `tatara-council-brainstorm`
   (which proposes NEW work from platform-wide scanning), this is narrow and
   reactive: use the code-graph tools (`code_search`, `code_explain`,
   `code_related`) and, where the ask spans repos, one `explorer` subagent per
   implicated repo (via the `Agent` tool, `model: haiku`, `effort: low`) to
   confirm the ask is technically coherent and to surface the 1-3 real
   ambiguities worth asking about. Do not ask questions answerable from the
   code or the issue text.
3. **Post clarifying questions** (or, if nothing is genuinely ambiguous, a
   short confirmation of scope + your proposed approach) via
   `issue_outcome(action="discuss", comment=...)` for the task's own issue,
   or `comment_on_issue` for any other issue, per `tatara-mcp-scm-lifecycle`.
   The task-scoped `comment` tool is issueLifecycle-only and 409s for
   clarify - never call it. Apply
   `tatara-triage-judgment`'s rubric to decide whether this issue is already
   clear enough to hand off directly (skip to step 3 of Branch B) or genuinely
   needs a round of human input (go to the wait step below).
4. **Wait or hand off**, per the shared wait/handoff steps below.

## Branch B - comment on an existing issue

1. **Read the full thread** (already in your turn-0 context) and determine:
   has a human replied since clarify's last comment, and if so, what did they
   say?
2. **Research and refine.** Delegate to `tatara-research-followup` for the
   research-the-gaps / respond-in-thread / idle-discipline procedure. That
   skill's silence-over-noise rule applies here without exception: if no
   human has replied since your last comment, post nothing.
3. **Decide the outcome** using `tatara-triage-judgment`'s rubric:
   - Human has posted an explicit approval / go-ahead -> hand off to
     `implement` (see below).
   - Human has explicitly declined, or the issue is a duplicate / out of
     scope -> close it per `tatara-mcp-scm-lifecycle`'s outcome recipe.
   - Still ambiguous, or no human has engaged yet -> go to the wait step.

## Shared: wait, or hand off to implement

**Wait (up to 1h wall-clock).** `clarify` is a live-polling pod: the operator
keeps it running and delivers new comments live via the existing
`PendingInterjections` mechanism, and kills the pod on a 1h timeout with no
reply. Follow `tatara-pipeline-waiting`'s heartbeat-poll pattern (the same
survive-turn-inactivity mechanic that skill teaches for CI waits applies here
for waiting on a human reply) rather than a single blocking wait. Do not
invent your own polling cadence.

**Never answer your own last comment.** If the most recent comment on the
issue is your own (bot-authored) with no human reply since, do not post
again - this would be a self-triggering loop. The operator's permission layer
also enforces this structurally (the MCP comment action and the webhook
actor/mention checks refuse a bot-authored last comment) - this skill states
the same invariant so your own judgment does not fight the permission layer.
This clarify-conversation rule has no exception; `refine` is the ONLY kind in
this repo permitted to comment under its own prior comment, and only for a
narrow scope-change/already-delivered case.

**Hand off to implement.** When the outcome is "implement": remove the
`tatara-brainstorming` label and add the `tatara-implementation` label (per
`tatara-writeback-discipline`'s label table) via
`issue_outcome(action="implement", plan=...)`, documented in
`tatara-mcp-scm-lifecycle` Section 2. Supply `plan` describing what will be
implemented and how - this seeds `implement`'s turn-0 context and is posted
as the implementation-start message.

## Anti-patterns

- Asking a clarifying question answerable from the issue text or the code.
- Re-posting a comment that only re-requests approval or restates prior
  analysis when no human has replied (silence-over-noise violation).
- Answering under your own last comment.
- Handing off to implement without a human approval signal (for an issue
  that started as a human ask, an explicit go-ahead is still required per
  `tatara-triage-judgment`'s tatara-authored gate where applicable).
- Pushing code, opening a PR, or making any file edit - that is `implement`'s
  job after handoff, never clarify's.
- Re-crawling SCM history already present in the turn-0 prompt bundle.
