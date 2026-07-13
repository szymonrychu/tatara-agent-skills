---
name: tatara-writeback-discipline
description: >
  Step-by-step procedure for every SCM egress action a tatara agent can take
  (issue comments, MR comments and opening, proposals, outcomes): which MCP
  tool to call, when, and what the operator does with it - including which
  writes are synchronous vs deferred, and the hard line between what you
  write (conversation) and what only the operator ever writes (verdicts,
  merges, labels, status). Invoke at the start of any turn that touches the
  SCM - comments, opening MRs, or ending the turn with an outcome.
profiles: ["*"]
---

# Tatara Writeback Discipline

## What you write, and what the operator writes

| Medium | Writer |
|---|---|
| An issue's comment thread | YOU, via `issue_write(action="comment")` |
| An MR's comment thread | YOU, via `mr_write(action="comment"\|"reply")` |
| The MR itself | YOU, via `mr_write(action="open")` |
| **The SCM review, and its inline findings** | **THE OPERATOR**, from your `submit_outcome` |
| **The merge** | **THE OPERATOR** |
| **Every label** | **THE OPERATOR** |
| **An issue's approved/rejected/done status** | **THE OPERATOR** |
| **The issue close on delivery** | **THE OPERATOR** |
| Your Task's stage, stats and conditions | THE OPERATOR |

One writer per medium. You write conversation. The operator writes verdicts,
merges, labels and status. This is not a courtesy division of labour - it is
what makes the platform's decisions auditable, because there is exactly one
place each one can have come from.

You never call anything that approves, merges, requests changes on, or labels
an MR yourself. `mr_write` has no `merge`, `approve`, or `request_changes`
action. `issue_write` has no `status` and no `labels` parameter. There is no
way to accidentally do the operator's job - the tool shape does not permit it.

---

## Step 1: What your kind can write

Every writeback tool is gated per profile (contract D.6). Never assume a
tool you do not see in `tools/list` will appear if you retry.

| `spec.kind` | `submit_outcome` shape | SCM write tools you own |
|---|---|---|
| `implement` | `action="submitted"\|"declined"` | `mr_write` (no `issue_write`) |
| `documentation` | same as `implement` | `mr_write` (no `issue_write`) |
| `brainstorm` | `action="propose"\|"skip"` | none - proposals go through `submit_outcome` only |
| `incident` | `action="file_issue"\|"false_positive"` | none - same reason |
| `clarify` | `decision="implement"\|"close"\|"discuss"` | `issue_write` (no `mr_write`) |
| `review` | `verdict="approve"\|"request_changes"` | `mr_write`, comment/reply only in practice - you review an existing MR, you do not open one |
| `refine` | `folds[]`, `closes[]`, `links[]` (any subset, at least one when acting) | `issue_write` and `mr_write` (`mr_write` restricted to `action="comment"` only) |

Full outcome schemas live in `tatara-mcp-outcome`; full `issue_write`/
`mr_write` schemas live in `tatara-mcp-scm`. This skill is about sequencing
and discipline, not the payload shapes.

`brainstorm` and `incident` never push code and never open an MR - the
operator has no repo target for a project-scoped WorkItem with no branch.
`implement` and `review` are also project-scoped Tasks but DO push code /
act on MRs - scoped to the specific repo(s) named in the Task's WorkItem
ledger, never a repo outside it.

---

## Step 2: Comments - synchronous vs deferred

**Only `issue_write(action="create")` and `mr_write(action="open")` are
synchronous** and hand back something to read (an issue number, an MR
number/url).

**`issue_write(action="edit"|"close"|"comment")` and
`mr_write(action="comment"|"reply")` are DEFERRED**: the call persists the
intent and returns; a reconciler posts it to the forge afterward. This means:

- Do not `scm_read` immediately after one of these calls expecting to see
  what you just wrote. It has not posted yet.
- Do not chain an `mr_write(action="reply")` to a comment you wrote earlier
  in the *same* turn - `reply` needs an `externalId` from
  `scm_read(kind=comments)`, and your own just-written comment does not have
  one yet.
- `issue_write(action="close")` REQUIRES a `comment` - every close cites its
  reason.

`mr_write(action="open")` is IDEMPOTENT: call it again for the same repo and
you get the existing MR back with `"existing": true"`, no duplicate opened.
If your Task already merged an MR for that repo, `open` is REFUSED - you are
about to duplicate work that already shipped.

Never post a blank or whitespace-only body. Never post the same comment
twice deliberately - a retried identical call is not guaranteed to dedupe on
the forge side the way `submit_outcome` is (Step 4).

---

## Step 3: Ending the turn - `submit_outcome`

`submit_outcome` is the ONE terminal tool, shaped from your kind (see
`tatara-mcp-outcome` for full schemas and the review verdict's
whose-MR-is-it branching). What follows is what the operator does with each
shape, so you understand what your call actually causes downstream:

- **`implement`/`documentation`, `action="submitted"`**: requires you to have
  already opened at least one MR this task owns (`mr_write(action="open")`,
  Step 2) - `action="submitted"` with zero owned open MRs is a 400. The
  operator records `changeSignificance` on every owned MR's status and, once
  the mergeOrder is satisfied, merges. `mergeOrder` is optional with exactly
  one owned repo, required otherwise.
- **`implement`/`documentation`, `action="declined"`**: covers BOTH "I
  decided this should not be built" and "this is already done" - there is no
  separate already-done tool. Put which one it is in `decline_reason`. The
  operator posts the reason as a comment and declines the issue.
- **`brainstorm`, `action="propose"`**: the operator creates the issue(s)
  under the bot identity from your `proposals[]`, embeds the
  `tatara-authored` marker, and enforces title-level dedup - a proposal
  matching an already-open issue's exact title is adopted, not duplicated.
- **`brainstorm`, `action="skip"`**: no proposal this cycle. A silent finish
  with no `submit_outcome` call at all is forbidden and re-prompted.
- **`incident`, `action="file_issue"`**: same issue-creation path as
  brainstorm's propose, scoped to the alert rule(s) that fired.
- **`incident`, `action="false_positive"`**: no issue filed; reason recorded.
- **`clarify`, `decision="implement"`**: your `reason` must cite WHO approved
  and WHERE. The operator independently re-reads the thread and re-verifies
  both identity and wording against the C.6 approval grammar - your judgment
  about scope is trusted, your report of consent is not. This can still fail
  the gate if the evidence does not hold up; see `tatara-mcp-outcome`.
- **`clarify`, `decision="close"`**: the operator closes the issue. Refused
  if the Task owns an unmerged MR - close the loose end first.
- **`clarify`, `decision="discuss"`**: the operator posts your `reason` as a
  comment and parks the task awaiting a human. This is not a dead end - a
  later maintainer comment that passes the approval grammar re-triggers the
  check and un-parks the Task on its own.
- **`review`, `verdict="approve"|"request_changes"`**: you never post the
  review yourself. The operator posts a single `COMMENT`-event review
  carrying your verdict and findings (the forge blocks a bot from
  self-approving OR self-requesting-changes on its own PR; `COMMENT` is the
  only event the platform ever sends). What happens next depends on whose MR
  it is: on the platform's own MR, `approve` lets the operator merge and
  `request_changes` loops back to `implementing`; on a human's PR, BOTH
  verdicts end at `parked(awaiting-human)` - no implement pod ever spawns
  from a `review`-kind Task. `reviewed_shas` must cover every owned MR, not
  just the ones with findings - a missing entry is a 400, not a silent pass.
- **`refine`, `folds`/`closes`/`links`**: the operator executes the
  adoption/closing/linking you described. An empty call (all three omitted)
  is a valid no-op turn when grooming finds nothing to act on.

---

## Step 4: Idempotency

- **`submit_outcome` is idempotent per `(task, agentKind, stage)`.** A repeat
  of an identical outcome returns 200 with the unchanged Task. This exists
  specifically so a TTL-stopped pod's retry does not 409 the Task into
  failure - you do not need to guard against calling it twice with the same
  payload.
- **`mr_write(action="open")` is idempotent** by repo + task branch, as in
  Step 2 - calling it again is safe and returns the existing MR.
  `issue_write(action="create")` has no such stated guarantee; do not call it
  twice for the same intent.
- **Deferred writes persist intent, not a confirmed post.** A crash or pod
  recycle between your call and the reconciler's forge post is the
  operator's problem to retry, not yours - but it also means you cannot
  chain off a deferred write's result in the same turn (Step 2).
- **A pushed branch survives a pod recycle; nothing else on disk does** (see
  `tatara-platform-contract`). If your pod is TTL-killed after you pushed but
  before `submit_outcome`, the next pod resumes from the pushed branch and
  can call `submit_outcome` itself.

---

## Step 5: What you never do

Labels, review verdicts on the forge, and merges are entirely operator-owned
- see the table at the top of this file. There is no tool call that sets a
label, posts an APPROVE/REQUEST_CHANGES review, or merges an MR, because
none exists in your tool surface. If you find yourself looking for one, you
are trying to do the operator's job; stop and call the outcome tool instead
so the operator can do it.

Board placement (moving a proposed issue into its board column) is likewise
fire-and-forget on the operator's side, driven automatically from your
`submit_outcome(action="propose"|"file_issue")` call. You take no separate
action for it.

---

## Anti-patterns

| Do NOT do this | Why |
|---|---|
| `scm_read` immediately after `issue_write(edit\|close\|comment)` or `mr_write(comment\|reply)` expecting to see it | These are deferred; the reconciler has not posted yet |
| Chain `mr_write(action="reply")` to a comment you wrote earlier in the same turn | No `externalId` exists for it yet |
| Call `mr_write(action="open")` a second time believing it will fail | It is idempotent; it returns the existing MR with `existing: true` |
| Call `submit_outcome(action="submitted")` before opening any MR | 400 - the Task owns no open MR to attach the outcome to |
| Look for an `mr_write` action to approve, request changes on, or merge | Does not exist. Reviews and merges are `submit_outcome` + the operator, never a direct tool call |
| Look for an `issue_write` `status` or `labels` parameter | Does not exist. Approval and every lifecycle label are operator-owned |
| Post an empty or whitespace-only comment body | The forge/operator will still consume the call; nothing useful lands |
| Use `task_note` to try to reach a human | Notes are agent/operator continuity state, never rendered to the issue or MR thread - see `tatara-headless-decisions` |

---

## Worked examples

### Implement run that produces an MR

```
1. Investigate, write code, push branch task/<task-name>.
2. mr_write(action="open", repo="tatara-operator",
     title="fix(tatara-operator): correct 4xx skip loop cap",
     body="Bounds the un-triageable writeback skip loop...")
   -> {"number": 295, "url": "...", "existing": false}
3. submit_outcome(
     action="submitted",
     title="fix(tatara-operator): correct 4xx skip loop cap",
     body="Bounds the un-triageable writeback skip loop...",
     change_significance="patch")
   -> Task's owned MR now carries significance=patch; operator proceeds
      toward merging once mergeOrder (implicit, single repo) is satisfied.
4. task_note(kind="handoff", body="MR #295 open, awaiting review.")
```

### Clarify that decides to discuss

```
1. Read the issue. Determine: needs human input before proceeding.
2. issue_write(action="comment", repo="tatara-operator", number=291,
     body="Decision needed: is the retry limit 3 or 10? ...")
3. submit_outcome(decision="discuss",
     reason="Posted a question about the retry limit; task parks awaiting reply.")
   -> Operator posts the reason too and keeps the task in Conversation.
```

### Brainstorm that proposes two ideas

```
1. Research the platform. Find two genuinely novel improvements, each with
   code-graph evidence (see tatara-evidence-and-citation).
2. submit_outcome(
     action="propose",
     proposals=[
       {repo: "tatara-operator", title: "feat: adaptive pool sizing based on turn latency p95",
        body: "... code_graph(op='stats') showed ... (internal/agent/pool.go:44)", kind: "improvement"},
       {repo: "tatara-cli", title: "feat: streaming tool-call progress events via SSE",
        body: "...", kind: "improvement"},
     ])
   -> Operator creates both issues, embeds tatara-authored, applies dedup.
```

### Implement that concludes the change is already present

```
1. Investigate. Read the issue. Search the codebase.
2. Find: the fix described in the issue was already committed in 6f657d2.
3. submit_outcome(
     action="declined",
     decline_reason="The null-pointer guard in agent/pod.go line 142 was
       already added in 6f657d2 (2026-06-23). The issue's proposed fix is
       already in the codebase.")
   -> Operator posts the reason as a comment and declines the issue. No MR
      was ever opened, so there is nothing to close.
```

### Review that requests changes with inline findings

```
1. Read the MR diff at its current head SHA.
2. submit_outcome(
     verdict="request_changes",
     reviewed_shas=[{repo: "tatara-operator", number: 295, sha: "abc1234"}],
     findings=[
       {repo: "tatara-operator", number: 295,
        path: "internal/controller/writeback.go", line: 122,
        body: "Missing error wrap: return fmt.Errorf(\"writeback: %w\", err)",
        severity: "high"},
     ])
   -> Operator posts a single COMMENT review carrying the verdict and the
      finding as an inline comment. This is the platform's own MR, so the
      Task loops back to implementing for the fix.
```
