---
name: tatara-implement-workflow
description: "Prescriptive implement-phase procedure for tatara agents: subtask decomposition, per-turn commit discipline, change_summary format, and mandatory terminal escapes (decline_implementation / already_done / submit_handover). Use at the start of every Implement-phase task."
---

# Tatara Implement Workflow

TASK content. Follow these steps in order. Do not skip or reorder.

---

## 0. Understand your context

At turn 0 you receive:

- `task` ID (also in env `TATARA_TASK`) and `project` ID (env `TATARA_PROJECT`). Pass these to every MCP tool call.
- The issue goal (`Spec.Goal`).
- The task branch (e.g. `tatara/task-<name>`). All your pushes target this branch. The branch is created from the default branch automatically. **Never commit or push to the default branch directly.**
- Workspace root: `/workspace/<owner>/<repo>` (a two-level namespace from the repo slug, e.g. `/workspace/szymonrychu/tatara-cli`). Every repo in scope is cloned here under its own `owner/repo` subdirectory. Changes you commit and push to the task branch are restored on the next run; uncommitted edits are discarded.
- Optionally: a `## Re-entry context` block (from a previous partial run), or a `## Resume from handover` block (when you were handed over from a prior agent that hit the context limit). Read these before doing anything else.

---

## 1. Decide: direct implementation vs subtask decomposition

**Criterion:** If the objective fits comfortably in one turn (single focused change, no multi-step sequencing needed), implement it directly now. Otherwise decompose.

**Decompose** by creating ordered subtasks:

```
subtask_create(task="<TATARA_TASK>", title="<step title>", detail="<what to do>", order=1)
subtask_create(task="<TATARA_TASK>", title="<step title>", detail="<what to do>", order=2)
...
```

Required args: `title`. Optional: `detail` (recommended - give enough context for execution), `order` (integer, lower runs first).

List subtasks at the start of each subsequent turn to find the next pending one:

```
subtask_list(task="<TATARA_TASK>")
```

Mark each subtask done when complete:

```
subtask_update(subtask="<subtask-id>", phase="Completed", result="<brief result>")
```

Work through subtasks in order across turns. Each turn ends with a git push; the branch is restored on the next turn.

---

## 2. Multi-repo work

If the prompt includes `**This issue spans repos: ...**`, each listed repo has a clone at `/workspace/<owner>/<repo>`. Edit and push every repo you change. Each repo with a committed change gets its own PR. If a listed repo genuinely needs no change, state that explicitly in your result summary.

---

## 3. Systemic group leadership

If the prompt includes `**You lead systemic improvement group ...**`, you are the lead agent for a group of related issues in this repo. Resolve all listed sibling issues in one combined PR and close them from the PR body using `Closes #N` for each sibling. Do not open separate PRs per sibling.

For cross-repo siblings listed under "Related work in OTHER repos": those are handled by separate agents. Do not edit those repos here.

---

## 4. Commit discipline

- Commit and push to the task branch at the end of each turn (the harness does this automatically via a post-turn hook, but make sure your changes are staged).
- Commits must not go to the default branch. The task branch was created for you.
- Each repo with a change gets its own push and its own PR.

---

## 5. Call change_summary before finishing (happy path)

When implementation is complete and you are about to end your final turn with a PR ready, call `change_summary`. This populates the MR title and body used by the operator.

```
change_summary(
  task="<TATARA_TASK>",
  pr_title="<concise imperative title>",        # required - becomes the MR title
  pr_body="<markdown body>",                     # required - becomes the MR description
  delivered_scope="<what was implemented>",      # required - appended as ## Delivered block
  remaining_scope="<what was not done>",         # optional - surfaces follow-up work
  most_problematic="<gotchas / dead-ends>"       # optional - recorded in MR body and docs
)
```

**Field guidance:**

| Field | What to write |
|---|---|
| `pr_title` | Short imperative: `fix: <thing>`, `feat: <thing>`. No trailing period. |
| `pr_body` | Motivation + approach. Enough for a reviewer to understand without reading code. |
| `delivered_scope` | Bullet list of concrete changes made (files, behaviors, tool names). |
| `remaining_scope` | Anything explicitly out of scope for this PR, or follow-up issues worth tracking. Leave blank if nothing. |
| `most_problematic` | The single biggest gotcha or surprise (dead-end explored, tricky integration point, non-obvious constraint). Leave blank if nothing notable. |

---

## 6. Terminal escape hatches

A silent finish (no PR, no tool call) is **never allowed**. Every implement run must end with one of: a pushed branch that opens a PR (happy path), `decline_implementation`, or `already_done`.

### 6a. decline_implementation - explicit refusal

Use when, after investigation, you determine **no code change should be made**: the issue is out of scope, the approach is wrong, the work is blocked by an external dependency, or implementing it would be harmful.

```
decline_implementation(
  task="<TATARA_TASK>",
  reason="<what you investigated, why the change should not be made>"
)
```

`reason` is required and must be non-empty. It is posted as a comment on the issue and the task is parked.

Do **not** use this when the fix already exists - use `already_done` instead.

### 6b. already_done - fix already present

Use when, after reading the issue and the repository, you confirm the requested change already exists (e.g. another task committed it on the shared branch, or it was shipped in a prior PR).

```
already_done(
  task="<TATARA_TASK>",
  reason="<where the fix already lives: commit, branch, or PR reference>"
)
```

`reason` is required and must be non-empty. Posted as a comment; task is parked. This is not a refusal.

### Decision table

| Situation | Correct call |
|---|---|
| Implemented, branch pushed | `change_summary(...)` then finish turn |
| Should not be implemented (wrong/out-of-scope/harmful) | `decline_implementation(reason=...)` |
| Fix already exists in the repo/branch | `already_done(reason=...)` |
| None of the above (silent finish) | **FORBIDDEN** - will trigger a re-prompt |

---

## 7. Context-limit handover

If you are approaching your context limit mid-implementation (many turns in, large codebase), call `submit_handover` before ending the turn. The operator will start a fresh agent with your handover as the `## Resume from handover` block.

```
submit_handover(
  task="<TATARA_TASK>",
  handover="<full context: what was done, what branch state looks like, what remains, where to pick up>"
)
```

`handover` is required. Write it so a new agent with no prior conversation history can continue without re-investigation. Include: which subtasks are done/pending, which files were edited, what the outstanding issue is, and the next concrete step.

---

## 8. Platform problems

If you are blocked by a platform or tooling failure (MCP server error, missing credentials, a tatara tool returning an unexpected error):

```
report_internal_issue(task="<TATARA_TASK>", ...)
```

This is the **only** correct channel. Do not open a tracker issue, do not post a normal output, do not treat a blocked tool as a reason to call `decline_implementation`. Report it and stop.
