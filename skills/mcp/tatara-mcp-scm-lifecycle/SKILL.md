---
name: tatara-mcp-scm-lifecycle
description: >
  Prescriptive decision tables and call recipes for every SCM and lifecycle
  operator MCP tool (propose_issue, comment_on_issue, issue_outcome,
  decline_implementation, already_done, skip_research, review_verdict,
  change_summary, create/edit/list_issues, comment, close_issue). Use in any
  agent turn that must drive an issue, PR, or task through the tatara lifecycle
  - especially when choosing between competing terminal/outcome calls.
profiles: ["implement", "review", "clarify", "refine"]
---

# tatara-mcp-scm-lifecycle

TASK skill. Follow each section in order. Every decision point has a table;
use the first row whose condition matches. Do not improvise around a terminal
call - call the right one or the operator will re-prompt.

## 0. Env-fill gotcha - read first

`project` and `task` args are OPTIONAL on every operator tool. When omitted,
the cli fills them from environment variables injected by the wrapper pod:

| Arg omitted | Filled from |
|-------------|-------------|
| `project` | `TATARA_PROJECT` |
| `task` | `TATARA_TASK` |

Omit both in every tool call unless you are deliberately addressing a
different project or task. NEVER pass a guess - omit and let the env fill it.

There is NO `TATARA_SUBTASK` env. `subtask` IDs for `subtask_update` are
ephemeral; you must capture the `id` returned by `subtask_create` or
`subtask_list` and pass it explicitly.

## 1. Issue discovery - propose vs comment vs skip

These three tools cover the brainstorm profile end state. Exactly
one must be called before the turn finishes; a silent exit causes a re-prompt.

### Decision table

| Situation | Tool to call |
|-----------|-------------|
| You found a genuinely novel, standalone, shippable problem not tracked anywhere | `propose_issue` |
| Your idea duplicates, extends, or is a sub-aspect of an EXISTING open issue | `comment_on_issue` on that issue |
| After full investigation you have nothing novel or shippable to propose this cycle | `skip_research` |

### propose_issue recipe

```
propose_issue(
  repo="szymonrychu/<repo>",         # REQUIRED - repository slug
  title="<short imperative title>",  # REQUIRED
  body="<full description with context and rationale>",  # REQUIRED
  kind="improvement"|"bug",          # REQUIRED
  systemicId="<shared-id>"           # OPTIONAL - share across repos for one systemic improvement
)
```

The operator opens the issue under the bot identity with an `idea` label and
holds it in discovery indefinitely. The ONLY way it advances into
implement->review->merge->deploy is a maintainer (a login listed in the
project's `MaintainerLogins` config, bots excluded) applying the
`tatara-approved` label directly on the issue - the operator verifies the
label-event actor against `MaintainerLogins` and records that as
`ApprovedByMaintainer` before `clarify` is allowed to hand off to implement
(Section 2). A comment - including from the reporter, from a non-maintainer,
or from a bot - does NOT approve, and a non-maintainer or bot applying the
label does NOT approve either. If `MaintainerLogins` is unset or empty for
the project, this record can never be created, so the issue never advances
(fail-closed). Embed `<!-- tatara-authored -->` in the body so the operator
keeps it in discovery. `project` defaults to `TATARA_PROJECT`.

For cross-repo systemic improvements: call `propose_issue` once per affected
repo with the SAME `systemicId` string. The operator stamps
`tatara/systemic-<id>` on each and counts the group as ONE against the
proposal cap.

### comment_on_issue recipe

```
comment_on_issue(
  repo="szymonrychu/<repo>",  # REQUIRED
  number=<issue_number>,      # REQUIRED - positive integer
  body="<comment text>"       # REQUIRED
)
```

Use when your finding is a sub-aspect or extension of an existing issue. Do
not open a new issue in this case; comment instead.

### skip_research recipe

```
skip_research(
  reason="<what you surveyed and why nothing is novel/shippable/in-scope>"
  # REQUIRED - non-empty; posted as the brainstorm no-yield outcome
)
```

Call after investigation when you have nothing to propose. A blank reason is
rejected. `task` defaults to `TATARA_TASK`.

## 2. Clarify outcome

Called at the end of a `clarify` turn to record the outcome and drive the
next transition: stay in conversation (`discuss`), close the issue
(`close`), or hand off to `implement` (`implement` - swaps the
`tatara-brainstorming` label for `tatara-implementation` per
`tatara-writeback-discipline`'s label table). The tool is `issue_outcome`;
this is settled by the cross-repo contract, not a placeholder.

### Decision table

| Condition | action | Additional args |
|-----------|--------|----------------|
| Issue is clear, scoped, approved for implementation | `"implement"` | `plan` (required: describe WHAT and HOW) |
| Issue needs closing (duplicate, won't fix, already done) | `"close"` | `comment` (required: reason for close) |
| Issue needs more discussion, design, or human input | `"discuss"` | `comment` (required: the questions or design notes to post) |

A nil outcome (agent finishes without calling `issue_outcome`) defaults
internally to awaiting human input - the operator does NOT silently proceed to
implement. Always call explicitly.

`action="implement"` only advances the issue when the operator already holds
a verified `ApprovedByMaintainer` record for it - i.e. a `MaintainerLogins`
login applied the `tatara-approved` label directly on the issue (Section 1).
Calling `issue_outcome(action="implement")` on an issue that has not cleared
that gate does not bypass it; only call `"implement"` when you have confirmed
the label is present and was applied by a maintainer, never on the strength
of a comment alone.

### issue_outcome recipes

```
# Approve for implementation:
issue_outcome(
  action="implement",
  plan="<what will be implemented and how - flow, key ideas, approach>"
)

# Close:
issue_outcome(
  action="close",
  comment="<reason - cite duplicate #N or commit SHA>"
)

# Request more discussion:
issue_outcome(
  action="discuss",
  comment="<questions or design notes to post on the issue>"
)
```

`task` defaults to `TATARA_TASK`.

## 3. Implementation terminal calls

At the end of an implement turn, you MUST call exactly one of:

- Open a PR and call `change_summary` (the normal path)
- Call `decline_implementation` (if no code SHOULD be written)
- Call `already_done` (if the fix is ALREADY PRESENT)

A silent exit with no PR and no terminal call is NOT allowed. The operator
will re-prompt, then mark the task `refused-no-explanation`.

### Decision table

| Situation | Call |
|-----------|------|
| You opened a PR with actual code changes | `change_summary` |
| After investigation the issue should NOT be implemented (wrong approach, out of scope, harmful, blocked) | `decline_implementation` |
| The fix is already present in the codebase or was committed by another agent | `already_done` |

### change_summary recipe

```
change_summary(
  pr_title="<imperative PR title>",         # REQUIRED
  pr_body="<full PR description>",           # REQUIRED
  delivered_scope="<what was implemented>",  # REQUIRED
  remaining_scope="<any out-of-scope items>",# OPTIONAL
  most_problematic="<biggest gotcha or tricky integration point>"  # OPTIONAL
)
```

The operator uses `pr_title` and `pr_body` as the MR title and body. The
`most_problematic` field is surfaced in the MR body and persisted to docs.
`task` defaults to `TATARA_TASK`.

### decline_implementation recipe

```
decline_implementation(
  reason="<why this should NOT be implemented: what you considered, why it is wrong/out-of-scope/blocked>"
  # REQUIRED - non-empty
)
```

Posts `reason` as an issue comment and parks the task. This is a REFUSAL.
If the code already exists, use `already_done` instead.

### already_done recipe

```
already_done(
  reason="<what already-present change satisfies the issue: commit/branch/PR where the fix already lives>"
  # REQUIRED - non-empty
)
```

Posts `reason` as an issue comment and parks the task. This is NOT a refusal.
Use only when you have confirmed the fix exists in the codebase.

## 4. Review verdict (review profile)

### Decision table

| Condition | decision |
|-----------|---------|
| PR is correct, safe to merge | `"approve"` |
| PR has issues that MUST be fixed before merge | `"request_changes"` |
| You have questions or non-blocking comments only | `"comment"` |

### review_verdict recipe

```
review_verdict(
  decision="approve"|"request_changes"|"comment",
  body="<overall review summary>",   # OPTIONAL but strongly recommended
  suggestions=[                       # OPTIONAL - inline code suggestions
    {"path": "path/to/file.go", "line": 42, "body": "<suggestion text>"},
    ...
  ]
)
```

`task` defaults to `TATARA_TASK`.

## 5. Free-form comment during a turn

Use `comment` to post a message on the task's linked issue WITHOUT changing
the lifecycle state. Use it for mid-turn updates or design notes that do
not constitute a final outcome.

```
comment(
  body="<non-empty comment text>"  # REQUIRED
)
```

`task` defaults to `TATARA_TASK`. This does NOT replace `issue_outcome` or
any terminal call. Always call the appropriate outcome tool at turn end.

**Not available to `clarify`.** The task-scoped `comment` endpoint
(`/tasks/{t}/comment`) is gated issueLifecycle-only by the operator - a
`clarify` agent calling it 409s. Clarify's conversation path is
`issue_outcome(action="discuss", comment="...")` for the task's own issue,
plus `comment_on_issue` for any other issue.

## 6. Issue CRUD (refine profile)

### list_issues recipe

```
list_issues(
  state="open"|"all",         # OPTIONAL; default "open"
  closedSinceDays=<integer>   # OPTIONAL; default 30; only relevant when state="all"
)
```

`project` defaults to `TATARA_PROJECT`. PRs are excluded from results.

### list_commits recipe

```
list_commits(
  sinceDays=<integer>  # OPTIONAL; default 30
)
```

`project` defaults to `TATARA_PROJECT`.

### close_issue recipe

```
close_issue(
  repo="szymonrychu/<repo>",   # REQUIRED
  number=<issue_number>,       # REQUIRED - positive integer
  comment="<reason>"           # REQUIRED - every close must cite its reason
)
```

`project` defaults to `TATARA_PROJECT`. Always explain: duplicate of #N,
already implemented in commit SHA, out of scope because X.

### edit_issue recipe

```
edit_issue(
  repo="szymonrychu/<repo>",  # REQUIRED
  number=<issue_number>,      # REQUIRED
  title="<new title>",        # OPTIONAL - omit to leave unchanged
  body="<new body>",          # OPTIONAL - omit to leave unchanged
  labels=["label-a", "..."]   # OPTIONAL - omit to leave unchanged; this REPLACES the label set
)
```

At least one of `title`, `body`, `labels` must be supplied. `project`
defaults to `TATARA_PROJECT`.

### create_issue recipe

```
create_issue(
  repo="szymonrychu/<repo>",   # REQUIRED
  title="<title>",             # REQUIRED
  body="<body>",               # REQUIRED - must link originating issue or commit and state why filed
  labels=["label-a", "..."]    # OPTIONAL
)
```

`project` defaults to `TATARA_PROJECT`. Use for issue splits and followups.
This bypasses the proposal/approval flow (no `idea` label, no human gate).
For new autonomous proposals use `propose_issue` instead.

## 7. Handover

Call before context runs out or when handing off to a parallel/next agent.

```
submit_handover(
  handover="<full context: what was done, what is pending, where to resume>"
  # REQUIRED - non-empty
)
```

`task` defaults to `TATARA_TASK`. Post this before any context-limit stop.

## 8. Profile availability reference

Not all tools are available in every profile. The table below shows which
terminal/outcome tools are present per profile.

| Profile | Available terminal/outcome tools |
|---------|--------------------------------|
| `brainstorm` | `propose_issue`, `comment_on_issue`, `skip_research` |
| `clarify` | `issue_outcome`, `comment_on_issue` |
| `implement` | `change_summary`, `decline_implementation`, `already_done`, `submit_handover` |
| `review` | `review_verdict`, `submit_handover` |
| `incident` | `propose_issue`, `comment_on_issue`, `change_summary`, `decline_implementation`, `submit_handover` |
| `refine` | `list_issues`, `list_commits`, `close_issue`, `edit_issue`, `create_issue`, `comment_on_issue` |

`project_get`, `repo_list`, `task_get`, `report_internal_issue` are present
in every profile (alwaysOn). Memory and code-graph tools are always included.

## 9. Anti-patterns

- Do NOT pass `project` or `task` explicitly unless addressing a different
  project/task than the injected env. Let the env fill it.
- Do NOT call `create_issue` for autonomous proposals. Use `propose_issue`
  so the operator applies the bot identity and `idea` label with the approval
  gate. `create_issue` is for agent-filed splits/followups only.
- Do NOT finish a turn silently without a terminal call. Every agent turn that
  reaches its goal must call the matching outcome tool or the operator
  re-prompts repeatedly before parking as `refused-no-explanation`.
- Do NOT call `decline_implementation` when the fix is already present; call
  `already_done`. They have different semantics and different operator flows.
- Do NOT set `labels` in `edit_issue` unless you intend to REPLACE the
  entire label set. Omit `labels` to leave existing labels unchanged.
- Do NOT use `comment` (free-form) as a substitute for `issue_outcome`.
  `comment` does not set a lifecycle outcome; it only posts a message.
- Do NOT pass a constructed or guessed `subtask` ID to `subtask_update`.
  Always capture the `id` from `subtask_create` or `subtask_list` first.
