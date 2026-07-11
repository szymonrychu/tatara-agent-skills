---
name: tatara-triage-judgment
description: "REFERENCE - judgment rubric and hard rails for the tatara clarify agent when deciding whether to keep an issue in conversation, close it, or hand it off to implement. Defines how to classify an issue and which MCP outcome to take. Do not use as a procedure; use tatara-clarify-conversation for the harness and tatara-research-followup for the research workflow."
profiles: ["clarify", "refine"]
---

# tatara triage judgment

This is a REFERENCE skill. It defines the judgment rubric the `clarify` agent
applies (on both the new-issue and existing-issue paths) to classify an issue
and select the correct outcome. The actual codebase research procedure lives
in `tatara-research-followup`; the outer procedure lives in
`tatara-clarify-conversation`. This skill ADVISES; it does not drive.

## What the operator injects

The operator injects a turn-0 prompt for every `clarify` task carrying: the
issue (or comment-thread) identity and URL, the issue title and body, and the
FULL conversation thread for this Task's umbrella (every linked issue and its
comments across every repo in the project scope - Decision 7 of the locked
design spec: the operator assembles this from live SCM state so you do not
need to re-crawl it). It requires the `tatara-research-followup` skill for
codebase research on the existing-issue path, and requires a terminal MCP
outcome call before finishing (see `tatara-clarify-conversation` and
`tatara-mcp-scm-lifecycle` for the exact tool). The `clarify` profile has
`chat: true` and the conversation/handoff toolset; consult
`tatara-mcp-scm-lifecycle`'s profile-availability table for the exact list.

## The judgment rubric

Read the issue AND the full conversation thread before deciding. The thread is the authoritative record of human intent.

**action=implement** when the issue carries the `tatara-approved` label,
applied by a maintainer (a login listed in the project's `MaintainerLogins`
config, bots excluded). Applies equally to human-authored and tatara-authored
issues - there is no separate comment-based path for either. The operator
verifies the label-adding actor against `MaintainerLogins` and only then
records `ApprovedByMaintainer`; a comment, however explicit ("go ahead",
"LGTM", "approved"), does NOT satisfy this gate, and a non-maintainer or bot
applying the label does NOT satisfy it either. If `MaintainerLogins` is
unset or empty for the project, this record can never be created and the
issue never advances (fail-closed) - treat that as a permanent hold, not
something to route around. When routing to implement, supply a `plan` arg (a
short description of what will be implemented and how - key ideas, approach,
flow); this is posted to the issue as the implementation-start message and
seeds the implement agent's context.

**action=close** when:
- A human has explicitly declined or closed the issue in the thread.
- The issue is a duplicate of an existing open issue (supply the duplicate ref in `comment`).
- The issue is out-of-scope, not actionable, or incompatible with the platform hard rules.

**action=discuss** when:
- The issue is still under active discussion and no clear human intent has been expressed.
- You need more information from the maintainer to decide.
- This is a tatara-authored issue and no human has commented yet. In this case supply `comment=""` (empty string). The operator will NOT post a comment; do NOT call the `comment` tool to post one either.

## Hard invariants

**MUST call `issue_outcome`.**
The turn is not complete until `issue_outcome` is called with one of `{implement, close, discuss}`. Missing this call is a protocol violation.

**No PRs, no code changes in this turn.**
The `clarify` kind is a classification/conversation turn only. Do not open pull requests, push commits, or modify any code. The implement gate handles execution.

**tatara-authored gate.**
An issue opened by the bot carries the `<!-- tatara-authored -->` marker. Only implement it once a maintainer has applied the `tatara-approved` label (same gate as any other issue - see the rubric above). If no human has commented and the label is absent, emit `discuss` with `comment=""` and do NOT use the `comment` tool or `comment_on_issue` to post anything; the operator handles silence intentionally.

**`comment` field carries the human-visible rationale.**
For `close` and `discuss`, the `comment` field is what gets posted to the issue (if non-empty). Make it useful: name the duplicate ref, state why the issue is out of scope, or surface the specific questions you need answered. Do not post boilerplate or empty close reasons.

## Judgment anti-patterns

- Emitting `implement` on any issue (tatara-authored or human-authored) that
  does not carry a maintainer-applied `tatara-approved` label - a comment,
  including an explicit approval comment, does not substitute.
- Emitting `discuss` when a maintainer has clearly applied the
  `tatara-approved` label, or when a human has clearly declined.
- Emitting `close` as a shortcut when the issue is legitimately actionable but needs clarification.
- Calling the `comment` tool to post a comment when `action=discuss` and `comment=""` (tatara-authored, no human comment yet) - the operator intentionally stays silent.
- Completing the turn without calling `issue_outcome`.
- Making code changes or opening PRs in the clarify turn.

## What belongs in tatara-research-followup vs here

`tatara-research-followup` describes how to research the codebase - which memory/code-graph tools to use, how to validate a claim, how to connect the issue to live code. This skill is the judgment layer: given research results, which `issue_outcome` action applies and why. Read both; let the rubric above decide the action after the research is done.
