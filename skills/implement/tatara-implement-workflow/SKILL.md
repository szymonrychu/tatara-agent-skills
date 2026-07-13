---
name: tatara-implement-workflow
description: "Prescriptive implement-stage procedure for tatara agents: planning notes, per-turn commit discipline, opening the MR with mr_write, the submit_outcome shape (including merge_order), and the mandatory terminal escapes. Use at the start of every implement turn."
profiles: ["implement"]
---

# Tatara Implement Workflow

TASK content. Follow these steps in order. Do not skip or reorder.

---

## 0. Understand your context

At turn 0 you receive:

- The Task and project. Every `tatara` tool auto-scopes to them from the pod
  environment - omit the `task`/`project` args and the tool fills them in.
- Your assignment, rendered by the operator.
- The task branch (`task/<task-name>`). All your pushes target it. It is created
  from the default branch for you. **Never commit or push to the default branch.**
- Workspace root: `/workspace/<owner>/<repo>` - every repo in scope, cloned under
  its own `owner/repo` subdirectory. Changes you commit and push to the task
  branch are restored on the next run; uncommitted edits are discarded.

The bundle carries the FULL cross-repo context for this Task: every Issue it owns
with its comment thread, every MR it owns with its body, branch, head SHA, CI
state and mergeability, and every prior `<note>` - including the handoff note from
whichever pod ran before you. **Read the notes first.** They are the continuation
state; there is nothing else (see `handoff`). This is everything a human
maintainer would see. Do not re-crawl the forge to reconstruct history already in
your prompt; reserve `scm_read` for what is genuinely not there (fresh CI state,
a comment thread on an issue you do not own).

If the `<notes>` element reports a nonzero `elided` count, pull the rest with
`task_context(notes="all")`.

---

## 1. Plan, then work the plan

**Criterion:** if the objective fits comfortably in one turn (a single focused
change, no multi-step sequencing), implement it directly. Otherwise decompose.

There is no subtask CRD and no subtask tool. Decompose with your own TodoWrite
list for the turn, and persist the plan across turns with a note:

```
task_note(kind="plan", body="1. operator: guard the reaper on podStartedAt. 2. cli: ...")
```

Notes are the ONLY thing that survives your pod. A plan you keep in your head is
lost the moment your pod is stopped. Update the note as steps land, and read the
prior notes out of your bundle at the start of every turn rather than re-deriving
the plan.

Each turn ends with a git push; the branch is restored on the next turn.

---

## 1a. Dispatch through typed subagents (mandatory)

You are the Opus surface for this Task; do the mechanical and read-only work
through the typed subagents shipped in this plugin's `.claude/agents/`, not
inline, so your own context stays lean across a multi-turn implementation.
Dispatch by task shape:

| Task shape | Dispatch to | Baked model/effort |
|---|---|---|
| Locate where code/config/behavior lives; map blast radius; read-only investigation | `explorer` | haiku, low |
| Write or run tests for an already-decided change | `tester` | haiku, low (re-dispatch with a `sonnet` model override for cross-file integration test design) |
| Mechanical edit to 1-3 files from an already-decided spec | `builder` | sonnet, medium |
| Ambiguous scope, a decision between competing approaches, cross-repo integration judgment, or anything a builder/tester/explorer would have to guess on | `architect` | opus, high |

Launch independent subagents (e.g. explorer calls into two unrelated repos in
the same Task) in a single message so they run concurrently - do not
serialize what can fan out. A subagent that reports back ambiguity is a
signal to re-dispatch to `architect`, not to guess and proceed with `builder`.

---

## 2. Multi-repo work

Every repo your Task's Issues span has a clone at `/workspace/<owner>/<repo>`.
Edit and push every repo you change. Each repo with a committed change gets its
own MR. If a repo in scope genuinely needs no change, say so explicitly in your
outcome body.

---

## 3. Several issues under one Task

A Task can own several Issues, across several repos. They were approved together
and they ship together: resolve all of them in this Task's MRs. Do not open a
separate Task or a separate stream per issue.

The issue-closing directive in your MR body is filtered by an operator-side
ALLOWLIST: `Closes #N` survives only for an Issue this Task actually owns. Write
`Closes #N` for an owned issue and `refs #N` for anything else - a directive that
would close an issue outside your Task's mandate is stripped, and writing it
anyway just produces a body that does not say what you think it says.

You do not decide which issues are approved. The operator ran the approval gate
on EVERY live Issue this Task owns before your pod was admitted; if it is your
Task, it is approved.

---

## 4. Commit discipline

- Commit and push to the task branch at the end of each turn (the harness does
  this via a post-turn hook, but make sure your changes are staged).
- Commits must not go to the default branch. The task branch was created for you.
- Each repo with a change gets its own push and its own MR.
- `git push --force` and `--force-with-lease` are hard-denied in this pod.

---

## 5. Open the MR, then submit the outcome (happy path)

When the FULL agreed scope is implemented, pushed, and green, open one MR per
changed repo:

```
mr_write(action="open", repo="tatara-operator", title="...", body="...")
```

`open` is IDEMPOTENT - if your Task already has an open MR for that repo on
`task/<task-name>`, you get it back with `"existing": true` and the forge is not
called. If your Task already MERGED an MR for that repo, `open` is REFUSED: you
are about to open a duplicate MR for work that already shipped. See
`tatara-mcp-scm`.

Then end the turn:

```
submit_outcome(
  action="submitted",
  title="<concise imperative title>",     # required
  body="<markdown body>",                 # required
  change_significance="major"|"minor"|"patch",   # required
  merge_order=["tatara-operator", "tatara-cli"] # required when >1 repo
)
```

| Field | What to write |
|---|---|
| `title` | Short imperative: `fix: <thing>`, `feat: <thing>`. No trailing period. |
| `body` | Motivation, approach, and what was delivered. Enough for a reviewer to understand without reading the code. Name the gotchas: the dead-end you explored, the tricky integration point, the non-obvious constraint. |
| `change_significance` | `major` = backward-incompatible, `minor` = backward-compatible feature, `patch` = fix. **YOU own this level.** A reviewer may RAISE it; nobody can lower it. It becomes the release tag. |
| `merge_order` | See below. |

**`merge_order` is the single most consequential field you fill in.** It is
REQUIRED the moment this Task's MRs span more than one repo: the Repository CR
names, first-merged first. **There is no default.** Get it wrong and a downstream
repo ships against an API that has not merged yet. With exactly one repo you may
omit it - there is one order and nothing to get wrong. Omit it on a multi-repo
change and you get a 400; omit a repo that has an owned open MR and you get a 400
naming it.

**Full scope or decline. There is no partial MR.** If part of the agreed scope
cannot be delivered (a hard blocker, a dependency that does not exist, work
genuinely outside this Task), that is `action="declined"` (section 6), not an MR
you already know is incomplete.

---

## 6. Terminal escape hatches

A silent finish is **never allowed**. A Task that receives no outcome does not
quietly stop: it ages out at `stageReason=no-outcome`, the pod is deleted, and
the work is lost. Every implement run ends with `submit_outcome`.

There are exactly two actions.

### 6a. action="declined"

```
submit_outcome(action="declined", decline_reason="<what you investigated, why no change should be made>")
```

Use when, after investigation, **no code change should be made**: the change is
the wrong direction, harmful, genuinely out of platform scope, or blocked by a
hard external dependency the platform cannot provide. Also use it when the fix
**already exists** - another Task shipped it, or it landed in a prior MR - naming
the commit or MR that already delivers it. There is no separate already-done
tool; a decline with an honest reason IS that report.

`decline_reason` is required and must be non-empty. The Task parks at
`implement-declined`.

**`decline_reason` MUST NOT cite insufficient context, ambiguous scope, or "need
more information".** By construction (section 0) you already have everything a
human maintainer has: every owned Issue, every comment thread, every MR's state,
and every prior note. If a specific technical unknown remains, dispatch an
`architect` subagent to resolve it, or make the best defensible engineering call
and record the assumption in your outcome `body`. A "this is ambiguous" decline
is a protocol violation.

### Decision table

| Situation | Correct call |
|---|---|
| FULL agreed scope implemented and pushed | `mr_write(open)` per repo, then `submit_outcome(action="submitted", ...)` |
| Scope cannot be delivered (blocked, wrong approach, harmful, out of scope) | `submit_outcome(action="declined", decline_reason=...)` |
| The fix already exists in the repo or on the default branch | `submit_outcome(action="declined", decline_reason="already delivered in <sha/MR>")` |
| Neither (a silent finish, or an MR with acknowledged remaining scope) | **FORBIDDEN** - the Task ages out at `no-outcome` and the work is lost |

---

## 7. Running out of turns, or being stopped

Your pod has a TTL and a turn budget. Before you stop for ANY reason - your
outcome is submitted, your budget is spent, or the operator hands you a turn
saying your pod is being stopped - write:

```
task_note(kind="handoff", body="<state / done / next / blocked>")
```

See `handoff` for what a good one contains. Notes ARE the continuation state:
there is no shared filesystem between pods, no chat, and no conversation to
resume. If you write nothing, the operator synthesises a note from your last
message and the repos you pushed - it knows what you DID and nothing about what
you MEANT to do next.

---

## 8. Platform problems

If you are blocked by a platform or tooling failure (an MCP server error, missing
credentials, a tatara tool returning an unexpected error):

```
report_internal_issue(...)
```

This is the **only** correct channel. Do not open a tracker issue, do not post a
normal output, and do not treat a blocked tool as a reason to decline. Report it
and stop.
