---
name: tatara-writeback-discipline
description: >
  Step-by-step procedure for every SCM egress action a tatara agent can take
  (comments, PR/MR opening, label management, board moves, proposals, triage
  outcomes, review verdicts): which MCP tool to call, when, and in what order,
  with idempotency invariants and terminal-CRD survival rules. Invoke at the
  start of any turn that touches the SCM - comments, opening PRs, closing
  issues, posting verdicts, or filing proposals.
profiles: ["*"]
---

# Tatara Writeback Discipline

## Overview

All SCM egress flows through the operator's writeback reconciler. The agent
never calls the SCM API directly; it calls MCP tools that set operator status
fields, and the operator materialises them idempotently. This means:

- Calling a tool twice with the same arguments is always safe.
- The operator may requeue and re-run any step; it guards against re-posting
  with idempotency checks on `Status.PrURL`, `Status.PendingComments`, and the
  `WritebackPending` condition.
- A status write that fails (RetryOnConflict exhausted) means the step will
  retry on the next reconcile - the SCM verb has NOT been applied yet.
- For non-idempotent verbs (`approve`, `request_changes`): the operator clears
  `WritebackPending` even when the subsequent persistence step fails, to avoid
  re-posting on requeue.

---

## Step 1: Identify the task kind

The correct writeback path is determined by `spec.kind`. Never invoke a tool
for the wrong kind.

| `spec.kind`      | Allowed writeback tools                                                           | Notes                                              |
|------------------|-----------------------------------------------------------------------------------|----------------------------------------------------|
| `implement`      | `change_summary`, `decline_implementation`, `already_done`                        | Operator opens PR via `OpenChange`; agent does not |
| `brainstorm`     | `propose_issue`, `skip_research`, `comment_on_issue`                              | Must call one of the first two; silent finish forbidden |
| `clarify`        | `issue_outcome`, `comment_on_issue`                                               | Operator posts comment; implement handoff swaps the label. Task-scoped `comment` is issueLifecycle-only (409 for clarify) - use `issue_outcome(action="discuss", comment=...)` instead |
| `review`         | `review_verdict`                                                                  | Operator posts approve/request_changes/comment; approve = label + native review, never a merge |
| `incident`       | `propose_issue`, `comment_on_issue`, `change_summary`, `decline_implementation`   | Project-scoped; never opens its own PR             |
| `documentation`  | `change_summary` (doc-relevant) or no tool call at all (no-op finish)             | Repo-scoped (docs repo); scheduled trigger          |
| `refine`         | `list_issues`, `list_commits`, `close_issue`, `edit_issue`, `create_issue`, `comment_on_issue` | Project-scoped; grooms existing backlog only |

`brainstorm`, `incident`, `clarify`, and `refine` never push code and never
call a tool that implies opening a PR - the operator would error-loop on
`writeBackOpenChange` for a WorkItem with no repo target. `implement` and
`review` are also project-scoped Tasks (Decision 3 of the locked task-kind
design: every kind operates under one project-level umbrella Task) but DO
push code / act on PRs - scoped to the specific repo(s) named in the Task's
WorkItem ledger, never a repo outside it.

---

## Step 2: Choose the right tool

### Posting a comment on the task's linked issue

Use `comment`. The body goes into `Status.PendingComments` and is drained by
the operator's lifecycle reconciler in order.

```
comment(body="...")
```

Rules:
- Never post a blank or whitespace-only body. The operator skips it (422 guard)
  but the slot is consumed, so subsequent comments may be reordered.
- Do not use `comment` to set an outcome (triage result, refusal). Use the
  appropriate outcome tool instead.

### Posting on an existing issue by repo + number

Use `comment_on_issue` when you want to extend or deduplicate an issue you did
not open in this task.

```
comment_on_issue(repo="owner/repo", number=42, body="...")
```

### Proposing a new issue (brainstorm / incident)

Use `propose_issue`. The operator creates the issue under the bot identity,
places it in the "Proposed" board column, and records `Spec.Source`.

```
propose_issue(
  repo="owner/repo",                    # repository slug, e.g. szymonrychu/tatara-operator
  title="...",
  body="... <!-- tatara-authored -->",  # embed the marker
  kind="improvement"|"bug",            # required: bug or improvement
  systemicId="..."                      # optional, shared id for systemic cross-repo group
)
```

Rules:
- Always embed `<!-- tatara-authored -->` in the body. The operator appends
  it automatically, but including it yourself makes the intent explicit.
- The operator enforces title-level dedup (C-guard): if an open issue with the
  same exact title exists it is adopted instead of duplicated.
- After `propose_issue` succeeds, `Spec.Source.URL` is set. Calling it again
  on the same task is a no-op (A-guard).

### Ending brainstorm with no proposal

Use `skip_research` when, after genuine investigation, there is nothing novel
to propose this cycle.

```
skip_research(reason="...")
```

A silent finish with no `propose_issue` and no `skip_research` is forbidden;
the operator re-prompts or parks as `refused-no-explanation`.

### Recording a clarify outcome (clarify kind)

Use `issue_outcome`. The operator posts the comment and transitions state.

```
issue_outcome(action="implement"|"close"|"discuss", comment="...")
```

- `implement`: operator swaps `tatara-brainstorming` for `tatara-implementation`
  and hands the Task to `implement`. This transition requires the operator to
  already hold a verified `ApprovedByMaintainer` record for the issue - a
  maintainer (a login listed in the project's `MaintainerLogins` config,
  bots excluded) applied the `tatara-approved` label directly on the issue,
  and the operator verified the label-event actor against that list. A
  comment never satisfies this, including from the reporter or from a
  non-maintainer, and a non-maintainer/bot applying the label does not
  either. If `MaintainerLogins` is unset or empty for the project, this
  record can never be created and the issue never advances (fail-closed).
  For systemic-group siblings, each sibling needs its own
  `ApprovedByMaintainer` record; an unapproved or declined sibling is not
  force-closed by the group's lead implement PR - see
  `tatara-implement-workflow` Section 3 for the `Closes #N` / `refs #N`
  distinction.
- `close`: operator calls `CloseIssue`. Forbidden when `Status.PrURL != ""`
  (unmerged change guard).
- `discuss`: operator posts the comment and keeps the clarify pod in
  conversation (live-polling, up to 1h wall-clock).
- A nil or whitespace comment for `discuss` is silently dropped (blank-body guard).

### Declaring implementation refusal

Use `decline_implementation` when you investigated and decided the change
SHOULD NOT be made.

```
decline_implementation(reason="...")
```

Use `already_done` when the change IS ALREADY PRESENT (another task committed
it, the fix is already in the codebase).

```
already_done(reason="...")
```

Both: operator posts the reason as a comment, applies the `declined` label, and
parks the task. A silent finish with no PR and neither tool called is
forbidden. The operator re-prompts up to 2 times, then parks as
`refused-no-explanation`.

### Describing the change being opened (implement kind)

Use `change_summary` to provide the PR title, body, and scopes. Call it before
the turn ends; the operator uses it for `OpenChange`.

```
change_summary(
  pr_title="feat(scope): imperative summary",   # strong title, no passive voice
  pr_body="...",                                 # markdown body
  delivered_scope="...",                         # what is in this PR
  remaining_scope="...",                         # optional follow-up scope
  most_problematic="..."                         # optional
)
```

PR title derivation priority (operator, from `derivePRTitle`):
1. `change_summary.pr_title` (when not weak per `titlecheck.Weak`).
2. `Source.Title` (the originating issue title).
3. First 72 characters of `Spec.Goal`.
4. Fallback: `"tatara automated change"`.

Always call `change_summary` with a non-weak title to guarantee the PR title
is correct.

### Posting a review verdict (review kind)

Use `review_verdict`. The operator posts it to the PR/MR via the SCM driver.

```
review_verdict(
  decision="approve"|"request_changes"|"comment",
  body="...",
  suggestions=[]  # optional inline suggestions: [{path, line, body}]
)
```

For `request_changes`: operator posts the verdict AND inline suggestions in
one pass. For `comment`: operator uses the PR ref (not the issue ref) so the
note lands on the MR, not on the issue.

`pr_outcome` has no live caller under this design: `selfImprove` is retired,
and merge/close now flow through `implement`'s `already_done` /
`decline_implementation` (conflict-resolution path) or the operator's deploy
supervisor (the sole merge caller, gated on green CI + `review` approval).

---

## Step 3: Idempotency invariants

These are not style preferences - violating them causes duplicate posts or
stuck loops.

1. **Check `Status.PrURL` before pushing code.** If it is already set, the
   operator has already opened a PR on a prior reconcile. Do not push to the
   same branch again; the operator will recover the existing PR via
   `recoverExistingPRURL` on a 422 "already exists".

2. **`WritebackPending=False` is the idempotency gate.** The operator checks
   `task.Status.PrURL != ""` at the top of `doWriteBack`; clearing that
   condition is safe to repeat but never skip.

3. **Do not post the same comment twice.** The `PendingComments` queue is
   drained in order. If the reconciler requeues after posting comment N-1,
   comment N is posted next - not N-1 again. But if you call `comment` twice
   with the same body, both are enqueued and both will be posted.

4. **RetryOnConflict wraps every status write in the operator.** You do not
   need to retry tool calls; the operator handles CAS conflicts. If a tool
   call returns success, the intent was recorded - even if a subsequent status
   persistence fails, it will be retried.

5. **Clear WritebackPending after, not before.** The operator always sets
   `WritebackPending=False` after the SCM verb lands (or is determined to be
   a no-op), not before. If your code clears it before the verb, a requeue
   will not retry the verb.

---

## Step 4: Label management

Labels are managed exclusively by the operator via `setLifecycleLabel`. Agents
MUST NOT call any label-setting tool directly; the operator sets the correct
label automatically when state transitions occur.

Managed labels (defaults; overridable in `ScmSpec`):

| Label name               | Meaning                        | Set on transition to...          |
|--------------------------|--------------------------------|----------------------------------|
| `tatara-brainstorming`   | Discovery / awaiting maintainer approval | brainstorm proposal, clarify discuss arm |
| `tatara-approved`        | Maintainer approved (issue) / review approved (PR) | On the issue: applied directly by a maintainer (per `MaintainerLogins`, bots excluded) - NOT by the operator or by clarify - and is the precondition for the clarify implement arm, not a result of it. On the PR: applied by the operator when `review` calls `decision="approve"`. |
| `tatara-implementation`  | Implementation in progress     | clarify/review handoff to implement |
| `tatara-declined`        | Refused / not implemented      | decline_implementation, already_done |
| `tatara-incident`        | Incident-originated proposal   | Operator sets automatically on proposals from `incident` kind tasks |

Rules for `setLifecycleLabel`:
- Sets EXACTLY ONE managed label and removes all others, EXCEPT `tatara-approved`
  on an issue: that is maintainer-applied, not operator-managed, and is not
  cleared by `setLifecycleLabel`'s single-label invariant.
- `AddLabel` failure returns an error (requeue); `RemoveLabel` failure is
  logged but tolerated.
- Never set labels manually via git or direct SCM API calls. Agents never
  apply `tatara-approved` to an issue themselves - only a maintainer's
  label-apply, verified against `MaintainerLogins`, counts.

---

## Step 5: Board operations

Board moves are fire-and-forget after `propose_issue`. The operator calls
`AddBoardItem` then `SetBoardColumn("Proposed")` automatically. Both failures
are non-fatal and logged; do not retry them manually.

---

## Step 6: Terminal-CRD survival

When a Task CR is garbage-collected (owner deleted), the operator stops
reconciling it. Partial writebacks may be orphaned. To survive:

- Always call `change_summary` before pushing code. If the task is GC'd mid-
  writeback, `Status.ChangeSummary` is already recorded.
- Always use the atomic PR URL persist: after the first `OpenChange` succeeds,
  the operator immediately writes `Status.PrURL` under `RetryOnConflict`
  before processing other repos. A crash between repos does not lose the
  primary PR.
- Terminal conditions (`WritebackFailed`) are sticky: once `failWritebackSkip4xx`
  sets `WritebackFailed=True`, it persists even if `WritebackPending` is
  re-armed. This means a task that hit the 4xx-skip cap (3 attempts) will NOT
  be retried even after a re-activation. Escalate to a human.

---

## Anti-patterns

| Do NOT do this                                   | Why                                                                                  |
|--------------------------------------------------|--------------------------------------------------------------------------------------|
| Call `comment` with an empty or whitespace body  | Operator silently drops it; the comment slot is consumed and later comments shift    |
| Post a comment then call `issue_outcome("close")`| The close may trigger before the comment drains; close and comment are separate paths |
| Call `propose_issue` more than once per task     | Operator enforces A-guard (Source.URL set) and C-guard (title dedup); second call is a no-op but logs ambiguity |
| Push code and then call `decline_implementation` | The operator will see a pushed branch in `Status.HeadBranch` and refuse to close the issue via `hasUnmergedChange` guard |
| Call `issue_outcome("close")` when there is a `Status.PrURL` | The operator's `hasUnmergedChange` guard blocks the close; the task parks in Conversation |
| Rely on the `<!-- tatara-authored -->` marker absence to detect human issues | The marker is appended by the operator; authored status is read via `Source.AuthorLogin` vs `BotLogin` |
| Call `review_verdict(decision="approve")` on an unmergeable PR/MR | Approve never merges; it only applies `tatara-approved` + a native review. Mergeability must be checked first (see `tatara-review-checklist`) |

---

## Worked examples

### Implement run that produces a PR

```
1. Investigate, write code, push branch tatara/task-<task-name>.
2. Call change_summary(
     pr_title="fix(tatara-operator): correct 4xx skip loop cap",
     pr_body="Bounds the un-triageable writeback skip loop...",
     delivered_scope="writebackSkip4xxCap = 3 constant + recordSkip4xxAttempt",
   ).
3. Finish the turn (no further action needed).
   Operator: WritebackPending triggers doWriteBack -> writeBackOpenChange ->
   OpenChange (one per repo with the branch) -> Status.PrURL written ->
   comment "Done - opened PR/MR: https://..." on issue.
```

### Clarify that decides to discuss

```
1. Read the issue. Determine: needs human input before proceeding.
2. Call issue_outcome(
     action="discuss",
     comment="The scope of this change is ambiguous. Is the goal X or Y?..."
   ).
3. Operator: posts comment on issue, transitions task to Conversation idle.
```

### Brainstorm that proposes two ideas

```
1. Research the platform. Find two genuinely novel improvements.
2. Call propose_issue(
     repo="szymonrychu/tatara-operator",
     title="feat: add adaptive pool sizing based on turn latency p95",
     body="... <!-- tatara-authored -->",
     kind="improvement",
   ) for the first idea.
3. Call propose_issue(
     repo="szymonrychu/tatara-cli",
     title="feat: streaming tool-call progress events via SSE",
     body="... <!-- tatara-authored -->",
     kind="improvement",
   ) for the second.
4. Finish the turn.
   Operator: WritebackPending clears as BrainstormProposed (brainstormHasProposal=true).
```

### Implement that concludes the change is already present

```
1. Investigate. Read the issue. Search the codebase.
2. Find: the fix described in the issue was already committed in 6f657d2.
3. Call already_done(
     reason="The null-pointer guard in agent/pod.go line 142 was added in 6f657d2 (2026-06-23). The issue's proposed fix is already in the codebase."
   ).
   Operator: posts comment, applies tatara-declined label, parks task.
```

### Review that requests changes with inline suggestions

```
1. Read the PR diff.
2. Call review_verdict(
     decision="request_changes",
     body="Two blocking issues found:\n1. Missing error wrap...",
     suggestions=[
       {path: "internal/controller/writeback.go", line: 122, body: "return fmt.Errorf(\"writeback: %w\", err)"},
     ]
   ).
   Operator: calls RequestChanges + Suggest on SCM in sequence.
```
