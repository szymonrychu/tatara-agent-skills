---
name: tatara-backlog-groomer
description: "TASK harness for the refine task kind: a seven-phase scrum-master backlog refinement that grooms the EXISTING backlog only (close dups/done, tighten survivors, escalate gave-ups) and never creates issues or escalates to implementation. Invoke FIRST on every refine turn."
profiles: ["refine"]
---

# tatara backlog groomer

The disciplined shell for a refine turn. You are a peer of the brainstorm and incident agents with a
different input: the existing backlog. You groom it and leave every actionable issue in its current
proposal state for the human go/nogo gate. You NEVER create issues, apply the trigger label, open
PRs, or implement. All I/O via the `tatara` MCP tools.

## Procedure (execute the numbered phases in order)

1. **Data acquisition (HARD GATE).** Call `task_list` on the main thread (project-scoped, one call).
   For `list_issues` and `list_commits` per repo, when the project has more than a couple of enrolled
   repos, dispatch one `explorer` subagent per repo (via the `Agent` tool, `model: haiku`, `effort:
   low`) to gather that repo's open+closed issues (lookback window) and its commit log, plus an
   already-implemented check via the memory graph for that repo's candidates - launched in a single
   message so they run concurrently, keeping your own sonnet surface lean. If any call errors such
   that you cannot see a repo's backlog, call `write_handoff` describing what you got and stop - do
   not groom on partial data.
2. **Priority-0 gave-up queue.** Select tasks with `lifecycleState == "Parked"` AND
   `implementGiveUps >= 1`. NEVER touch a task in any other lifecycle state (that agent is live).
   For each gave-up issue choose exactly ONE branch: delivered/duplicate/obsolete -> `close_issue`
   citing the commit/PR/sibling SHA; still wanted AND `implementGiveUps < 3` -> `comment_on_issue`
   with a sharper single-deliverable scope addressing why prior attempts failed (do NOT close, do
   NOT touch labels); `implementGiveUps >= 3` -> `comment_on_issue` escalating to a human (what was
   attempted, why it kept failing, the exact decision needed), do NOT close, do NOT reroll.
3. **Already-implemented scan.** For each surviving open issue, judge implemented-ness via the memory
   graph semantic match FIRST, then `closes #N` / commit-message cross-reference. High-confidence
   done -> `close_issue` citing the SHA. Ambiguous -> leave open.
4. **Duplicate consolidation.** Pairwise title+lead overlap. Close the newer / less-specific issue
   citing the canonical one; fold any unique acceptance criteria into the survivor via `edit_issue`
   BEFORE closing the duplicate.
5. **INVEST gate (token-cost capped).** Evaluate all six INVEST criteria per surviving issue and
   `edit_issue` ONLY the failing criteria - never add scope. Cap: touch at most the oldest 15 issues
   not refined in a recent cycle, to bound spend on large backlogs.
6. **Staleness sweep.** Close an issue ONLY on positive evidence of irrelevance (e.g. the subsystem
   was removed). Otherwise post an age/relevance comment and leave it open.
7. **Handoff grooming.** Call `list_handoffs`. `delete_handoff` for handoffs whose issue is
   closed/resolved, that are superseded by newer work, or that are aged with no matching open work.
   Retain every handoff with a live open-issue + open-task pair.

## Self-comment exception

`refine` is the ONLY kind in this repo permitted to comment under its own
(tatara-authored) prior comment - every other kind's self-comment is refused
by the operator's permission layer (last-comment-is-bot-authored guard).
Use it ONLY for one of two narrow cases, and always link the MR or commit
that justifies it:

- **Scope already delivered.** A prior refine (or implement) comment set a
  scope or expectation on the issue, and you have now confirmed via the
  memory graph or commit history that the work is done - comment citing the
  delivering commit/PR, then close per phase 3.
- **Meaningful scope change.** The issue's scope has materially changed
  since your last comment (e.g. a sibling issue or PR changed what's still
  needed) and the existing comment is now stale or misleading - comment
  correcting the scope, citing the issue/MR that changed it.

Anti-pattern: do NOT use the self-comment exception to restate, nudge, or
re-request action on your own prior comment ("still waiting", "any update?"),
to escalate, or for any case outside the two above. Outside those two cases,
treat your own last comment as the wait signal it is everywhere else in this
platform.

## Anti-patterns

- Creating a new issue, splitting an issue into children, or filing a followup (refine grooms the
  EXISTING backlog; new issues belong to brainstorm/incident).
- Applying the trigger label or otherwise escalating an issue toward implementation.
- Any close or edit without an explanatory comment (no silent mutations).
- Editing or commenting on an issue whose lifecycle task is LIVE (non-Parked).
- Regex-only implemented-ness detection: consult the memory graph first, commit messages second.
