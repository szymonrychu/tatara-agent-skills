---
name: tatara-platform-contract
description: Hard constraints and anti-patterns for every tatara agent - headless operation, KISS, zero tech-debt, GitOps-only deploys, and report_internal_issue as the sole platform-failure channel. Load this as inline reference before any task-scoped work.
profiles: ["*"]
---

# Tatara Platform Contract

This is **reference content**. It does not drive a procedure. It advises your reasoning inline.
Read it, internalize the hard rails, then exercise your own judgment on everything else.

---

## Hard rails (non-negotiable)

### Headless - no interactive prompts

You run in a pod. No human is at the terminal.

`AskUserQuestion`, `ExitPlanMode`, and `EnterPlanMode` are **denied** in `settings.json` and
will error if called. Do not call them. Do not enter plan mode.

When you need a decision, options weighed, or any clarification:
- Post it as a comment via `comment_on_issue` - lay out the options and your recommendation,
  then continue with your best judgment.
- If a blocker makes **any** progress impossible, call `decline_implementation` with the reason.

The issue thread is your only channel to a human. Use it for communication, not for stalling.

### Platform failures go to report_internal_issue only

If you are blocked by a platform or tooling failure - an MCP server returning an error
(e.g. grafana 401/unreachable), missing access or credentials, a tatara tool failing, or a
required dependency you cannot reach - call `report_internal_issue` with the concrete details
(which tool, the exact error, what you were attempting).

That self-report is the **only** correct channel for platform/tooling failures: it raises
operator telemetry and an alert.

**Do NOT** open, propose, or comment on a tracker issue asking a human to fix the platform.
**Do NOT** treat a blocked tool as a reason to file your normal output.
Report it and stop.

*Source: `platformProblemGuidance` constant in `tatara-operator/internal/controller/turnloop.go`,
appended to every turn-0 directive.*

### KISS - always

Prefer simplicity over cleverness. Three similar lines are better than a premature abstraction.
Do not introduce tech-debt. If a thing is genuinely complex, record why in `MEMORY.md` with the
rationale. Never defer cleanup to "later".

### Deploy only via GitOps

Never `kubectl set image`, `kubectl patch`, `kubectl edit`, or `helm upgrade` by hand to ship
code or images. The deploy path is always:

1. Merge to the component repo's `main` (CI builds + pushes image/chart).
2. Open a `tatara-helmfile` MR bumping **both** the chart version and the pinned `image.tag`.
3. The pipeline applies it.

`kubectl patch` is allowed only for incident response (unblocking a down service), and must be
immediately re-asserted through `tatara-helmfile` so live state matches the repo.

---

## Tool surface - what you have and don't have

Your MCP tool set is gated by `TATARA_TOOL_PROFILE` (set per-kind by the operator). The gate is
enforced in `tatara-cli/internal/mcp/profiles.go`. Unknown or empty profiles fail open (full set).

**Always available** (every profile): `report_internal_issue`, `project_get`, `repo_list`,
`task_get`, plus all `groupMemory` (13 tools) and `groupCodeGraph` (19 `code_*` tools).

**`chat_*` tools** (10 tools): present in `brainstorm`, `clarify`, `incident` profiles only.

**Profile-specific operator tools** (examples):
- `implement`: `task_update`, `subtask_*`, `change_summary`, `decline_implementation`,
  `already_done`, `submit_handover`.
- `clarify`: `issue_outcome`, `comment_on_issue`. Task-scoped `comment` is
  issueLifecycle-only (409 for clarify) - use `issue_outcome(action="discuss",
  comment=...)` for task conversation instead.
- `incident`: `propose_issue`, `comment_on_issue`, `change_summary`, `decline_implementation`.
- `brainstorm`: `propose_issue`, `comment_on_issue`, `skip_research`.
- `review`: `review_verdict`, `submit_handover`.
- `refine`: `list_issues`, `list_commits`, `close_issue`, `edit_issue`, `create_issue`, `comment_on_issue`.

**What this means in practice**: if a tool call returns "unknown tool" or is absent from
`tools/list`, you are not in a profile that includes it. Do not retry. Adjust your approach
within the tools you have, or call `report_internal_issue` if the missing tool is genuinely
required for the task.

---

## Workspace and durability

The workspace is transient - rebuilt by git clone + checkout on every run. What survives:

- **Conversation kinds** (`clarify`, `brainstorm`, `incident`, `refine`): only what you post to the
  issue/MR conversation (comments, outcome decisions). File edits on disk are discarded.
- **Implementation kind** (`implement`): changes committed and pushed to the task branch are
  restored on the next run. Uncommitted edits are discarded. `review` reads the pushed branch
  read-only and never commits.

Never assume local disk state from a prior turn is still there unless you pushed it.

---

## Turn-0 context bundle (project-scoped kinds)

For every project-scoped kind (`brainstorm`, `incident`, `clarify`,
`implement`, `review`, `refine`), the operator assembles the FULL cross-repo
umbrella context into your turn-0 prompt: every linked issue's body and
comment thread, every open PR/MR's description, branch, and CI/mergeability
state, across every repo in the project's scope (Decision 7 of the locked
task-kind design). This is everything a human maintainer following the Task
would see. Do NOT re-crawl SCM (looping `list_issues`/comment-fetch calls) to
reconstruct history that is already in your prompt - spend MCP/SCM calls on
things not already there: fresh code investigation, dedup checks against
state that may have changed since the bundle was assembled, and posting.

---

## Code conventions (heuristics, not a checklist)

- JSON logs only: stdlib `log/slog` in Go. Structured fields everywhere
  (`request_id`, `user`, `action`, `resource_id`, `duration_ms` where relevant).
- Metrics for everything that counts, times out, or can fail. Expose `/metrics`
  Prometheus endpoint on every service.
- Charts are cluster-agnostic: no baked `imagePullSecrets`, node affinity, ingress
  host/class, storage class, or replicated-secret names in `values.yaml`.
  Cluster-specific config comes from `tatara-helmfile`.
- No plain ENVs or lists in `values.yaml`. camelCase scalar -> kebab-case ConfigMap/Secret
  key -> workload consumes via `envFrom`.

These are conventions that should shape your decisions. They are not a compliance checklist
to run through mechanically.

---

## What is left open to your judgment

The contract deliberately does not specify:
- How to decompose a problem or what subtasks to create.
- What to comment on an issue and when.
- How to balance depth vs. speed in investigation.
- Whether a situation warrants `decline_implementation` or a continued partial attempt.
- How to structure code within the platform conventions above.

Those are judgment calls. The rails above define the boundary; inside it, use your reasoning.
