---
name: tatara-triage-judgment
description: "REFERENCE - judgment rubric and hard rails for the tatara issueLifecycle agent during the Triage state. Defines how to classify an issue and which MCP action to take. Do not use as a procedure; use tatara-research-followup for the research workflow."
---

# tatara triage judgment

This is a REFERENCE skill. It defines the judgment rubric the lifecycle agent applies in the Triage state to classify an issue and select the correct `issue_outcome` action. The actual codebase research procedure lives in `tatara-research-followup`. This skill ADVISES; it does not drive.

## What the operator injects

The operator (`internal/controller/lifecycle.go: reconcileLifecycle` -> `buildTriagePromptFor` -> `turnloop.go: lifecycleTriageText / buildTriagePrompt`) injects a turn-0 prompt that:
- Identifies the issue by ref and URL.
- Supplies the issue title and body.
- Appends the most-recent conversation thread (capped to the last `triageCommentCap=20` comments and `triageCommentCharBudget=8000` characters, oldest first; truncated from the front so the most recent comments are always present).
- Requires the `tatara-research-followup` skill for codebase research.
- Requires a call to `issue_outcome` before finishing.

This prompt is for `issueLifecycle` tasks. The **lifecycle** profile (`profiles.go: lifecycle`) applies: `chat: true`; operator tools include `task_list`, `task_update`, `subtask_list`, `subtask_create`, `subtask_update`, `issue_outcome`, `comment`, `comment_on_issue`, `change_summary`, `decline_implementation`, `already_done`, `pr_outcome`, `review_verdict`, `submit_handover`; plus all 13 memory tools, all 19 code-graph tools, all 10 chat tools, and the 4 alwaysOn tools. The lifecycle profile spans all lifecycle states in one pod; only `issue_outcome`, `comment`, and `comment_on_issue` are relevant in the Triage state.

## The judgment rubric

Read the issue AND the full conversation thread before deciding. The thread is the authoritative record of human intent.

**action=implement** when a human has posted an explicit approval or go-ahead in the thread. Applies to both human-authored and tatara-authored issues. For tatara-authored issues (marked `<!-- tatara-authored -->`): require a positive human approval comment; ambiguous or absent comments do NOT satisfy this gate. When routing to implement, supply a `plan` arg (a short description of what will be implemented and how - key ideas, approach, flow); this is posted to the issue as the implementation-start message and seeds the implement agent's context.

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
Triage is a classification turn only. Do not open pull requests, push commits, or modify any code. The implement gate handles execution.

**tatara-authored gate.**
An issue opened by the bot carries the `<!-- tatara-authored -->` marker. Only implement it when a human has posted an approval comment. If no human has commented, emit `discuss` with `comment=""` and do NOT use the `comment` tool or `comment_on_issue` to post anything; the operator handles silence intentionally.

**`comment` field carries the human-visible rationale.**
For `close` and `discuss`, the `comment` field is what gets posted to the issue (if non-empty). Make it useful: name the duplicate ref, state why the issue is out of scope, or surface the specific questions you need answered. Do not post boilerplate or empty close reasons.

## Judgment anti-patterns

- Emitting `implement` on a tatara-authored issue that has no human approval comment.
- Emitting `discuss` when a human has clearly approved or declined.
- Emitting `close` as a shortcut when the issue is legitimately actionable but needs clarification.
- Calling the `comment` tool to post a comment when `action=discuss` and `comment=""` (tatara-authored, no human comment yet) - the operator intentionally stays silent.
- Completing the turn without calling `issue_outcome`.
- Making code changes or opening PRs in the triage turn.

## What belongs in tatara-research-followup vs here

`tatara-research-followup` describes how to research the codebase - which memory/code-graph tools to use, how to validate a claim, how to connect the issue to live code. This skill is the judgment layer: given research results, which `issue_outcome` action applies and why. Read both; let the rubric above decide the action after the research is done.
