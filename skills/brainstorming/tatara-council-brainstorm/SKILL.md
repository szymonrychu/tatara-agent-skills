---
name: tatara-council-brainstorm
description: "TASK harness for the brainstorm task kind: an architect-council session under the lens the operator selected for this cycle, grounding one high-leverage finding in real code and emitting a single submit_outcome (propose or skip). Invoke FIRST on every brainstorm turn; it owns the whole turn end to end."
profiles: ["brainstorm"]
---

# tatara council brainstorm

The disciplined shell for a brainstorm turn. It works one architectural lens per
cycle so successive runs examine the platform from different angles, forces
evidence before conclusion, and emits a single grounded outcome via
`submit_outcome`. All I/O is via the `tatara` MCP tools; you never
use git or gh.

## The lens

**The OPERATOR selects the lens and renders it into your assignment.** Read it
there. There is no rotation register to read and no register to advance - the
harness-state tools are gone, and the operator owns the rotation.

The lenses in the rotation: failure-modes, fitness-functions, coupling,
simplification, operability, product-growth, tech-radar.

## Procedure (execute the numbered phases in order)

1. **Pre-flight context assembly (HARD GATE).** For every enrolled repo cloned
   under `/workspace/<owner>/<repo>` (`repo_list` names them), read its on-disk
   `ROADMAP.md`, `MEMORY.md`, and `CLAUDE.md`. Then `memory_query` (mode global)
   for "tatara platform goal" and "open roadmap themes". Write a short summary of
   the platform goal plus the open themes to your scratchpad before continuing.
2. **Early-exit dedup scan (do this cheaply, FIRST action-gate).** Read the open
   issues and MRs with `scm_read(kind="issues"|"mr", repo=..., state="open")`,
   the `<task_index>` in your bundle, and `task_list`. If nothing clears the bar
   for a genuinely novel, high-leverage proposal through this cycle's lens, call
   `submit_outcome(action="skip", reason=...)` - naming the lens and why nothing
   qualified - and STOP. Silence over noise.
3. **Lens-specific evidence gathering.** When the lens needs evidence from more
   than one repo (failure-modes, coupling and tech-radar routinely do; the others
   may), dispatch one `explorer` subagent per implicated repo (via the `Agent`
   tool, `model: haiku`, `effort: low`) to gather that repo's slice of the
   evidence, launched in a single message so they run concurrently. This is what
   keeps your own surface context under the ~50% budget where reasoning quality
   degrades - synthesize the subagents' compact reports yourself rather than
   reading every repo's code inline. Prescribed tool calls per lens:
   - failure-modes: `code_graph(op="bridges")` + `code_graph(op="important")`,
     then read the actual failure-path source.
   - fitness-functions: read the CI config on disk and run the real lint/test,
     cite numeric output.
   - coupling: `code_context(rel="cross_repo")` + `code_graph(op="communities")`,
     report a concrete hop count.
   - simplification: `code_graph(op="stats")` + `code_graph(op="important")` plus
     a TODO/dead-code scan.
   - operability: inspect `/metrics`, tracing, and the on-disk runbooks.
   - product-growth: gap-analysis of the unbuilt roadmap (beyond current scope).
   - tech-radar: Hold-list dependencies and hard-rule gaps.

   If the lens you were given genuinely yields nothing but another does, you MAY
   override - but log the override and the reason explicitly in your outcome.
4. **Options-with-tradeoffs scratchpad (HARD GATE).** Before any terminal action,
   write: a problem statement grounded in a concrete `file:line`; a decomposition
   into sub-problems; for EACH sub-problem 2-3 options with a one-line tradeoff
   and your recommended pick; a pre-mortem naming at least 2 concrete failure
   mechanisms. No terminal action without this artifact.
5. **ADR-vs-scoped-issue decision, and repo scope (written).** Decide whether the
   finding warrants a structural ADR (architectural, cross-cutting) or a single
   scoped issue, AND list every repo the finding touches. Write both as one-line
   answers.
6. **Terminal action (you own it).** Exactly one `submit_outcome`.

   Emit `submit_outcome(action="skip", reason=...)` when nothing clears the bar,
   or when the finding duplicates an open issue or an in-flight Task (name the
   duplicate in the reason - you have no `issue_write` and cannot comment on it).

   Otherwise emit ONE call carrying every issue you want opened:

       submit_outcome(action="propose",
                      proposals=[{repo, title, body, kind}, ...])   # 1..5

   **Each proposal becomes its own issue and its own clarify Task.** There is no
   umbrella Task, no `systemicId`, and no linked-issue group: a finding that
   touches three repos is three entries, and the clarify conversation on each is
   where its scope is settled. The array is capped at 5.

   Every proposal body MUST:
   - Ground itself per `tatara-code-quality-proposal` (concrete `file:line`
     evidence).
   - Split the problem into at least 2 concrete approaches, each with a one-line
     tradeoff, ONE explicitly flagged "Recommended" - never a single-decision
     "approve or comment" framing.
   - Carry the ADR sketch in the body when phase 5 said structural.
   - Name the sibling proposals in this same call when the finding spans repos,
     so the humans reading three new issues can see they are one design.

   You never implement, push, or open an MR. Those tools are not in your profile.
7. **Handoff note (last).** `task_note(kind="handoff", body=...)` before you
   stop - see `handoff`. On a `skip` this is what tells the NEXT brainstorm cycle
   what you already surveyed and ruled out.

## Anti-patterns

- Taking any action before the phase-1 context summary.
- Looking for a lens register to read or advance. The operator owns the lens.
- A generic assertion with no `file:line` / SHA / graph finding behind it.
- Calling `submit_outcome(action="propose")` before the phase-4 scratchpad exists.
- More than one `submit_outcome` per turn, or none at all (a Task with no outcome
  ages out at `no-outcome` and the work is lost).
- Trying to comment on an existing issue instead of skipping. brainstorm has no
  `issue_write`.
