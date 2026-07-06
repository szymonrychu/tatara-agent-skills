---
name: tatara-council-brainstorm
description: "TASK harness for the brainstorm task kind: a rotating seven-lens architect-council session that grounds one high-leverage proposal in real code and delegates the terminal action to tatara-deep-research (scoped) or tatara-deep-architectural-research (structural). Invoke FIRST on every brainstorm turn; do not call the deep-research skills directly."
profiles: ["brainstorm"]
---

# tatara council brainstorm

The disciplined shell for a brainstorm turn. It imposes a rotating architectural lens so successive
runs examine the platform from different angles, forces evidence before conclusion, and delegates
the actual proposal to the deep-research sub-skills. All I/O is via the `tatara` MCP tools; you never
use git or gh. Run at maximum effort.

## Lens rotation order

failure-modes, fitness-functions, coupling, simplification, operability, product-growth, tech-radar.

## Procedure (execute the numbered phases in order)

1. **Lens rotation read (state-assembly, HARD GATE).** Call `harness_state_get(key="LENS_CYCLE")`.
   The value is the last lens used (or empty on first run / a stale register). Select the NEXT lens
   after it in the rotation order above; on empty/unrecognized value, default to `failure-modes`.
   Record the chosen lens and the `version` token you read - you will CAS it back in phase 8. Do NOT
   proceed to any action before this read succeeds.
2. **Pre-flight context assembly (HARD GATE).** For every enrolled repo cloned under
   `/workspace/<owner>/<repo>`, read its on-disk `ROADMAP.md`, `MEMORY.md`, and `CLAUDE.md`. Then
   `query` (mode global) the memory graph for "tatara platform goal" and "open roadmap themes".
   Write a short summary of the platform goal + open themes to your scratchpad before continuing.
3. **Early-exit dedup scan (do this cheaply, FIRST action-gate).** Review the injected
   ISSUES / OPEN MRs / MAIN HEALTH state and `task_list`. If nothing clears the bar for a genuinely
   novel, high-leverage proposal through your chosen lens this cycle, call `skip_research(reason)`
   (naming the lens and why nothing qualified), advance the register (phase 8), and STOP. Silence
   over noise.
4. **Lens-specific evidence gathering** (prescribed tool calls for the chosen lens):
   - failure-modes: `code_bridges` + `code_important`, then read the actual failure-path source.
   - fitness-functions: read CI config on disk and run the real lint/test, cite numeric output.
   - coupling: `code_cross_repo` + `code_communities`, report a concrete hop count.
   - simplification: `code_stats` + `code_important` + a TODO/dead-code scan.
   - operability: inspect `/metrics`, tracing, and on-disk runbooks.
   - product-growth: gap-analysis of the unbuilt roadmap (beyond current scope).
   - tech-radar: Hold-list dependencies + hard-rule gaps.
   If the current lens genuinely yields nothing but another does, you MAY override - but log the
   override and the reason explicitly.
5. **Options-with-tradeoffs scratchpad (HARD GATE).** Before any terminal action, write: a problem
   statement grounded in a concrete `file:line`; a decomposition into sub-problems; for EACH
   sub-problem 2-3 options with a one-line tradeoff and your recommended pick; a pre-mortem naming
   >=2 concrete failure mechanisms. No terminal action without this artifact.
6. **ADR-vs-scoped-issue decision (written).** Decide whether the finding warrants a structural ADR
   (architectural, cross-cutting) or a single scoped issue. Write the one-line answer.
7. **Terminal action via a delegated sub-skill.** Invoke `tatara-deep-research` for a scoped
   proposal, or `tatara-deep-architectural-research` for a structural one. Do NOT open the issue
   yourself and do NOT call the deep-research skills' terminal tools directly outside them - the
   sub-skill owns the single `propose_issue` / `comment_on_issue` action and the
   `<!-- tatara-authored -->` discovery contract.
8. **Register update (HARD GATE, last).** Call
   `harness_state_cas(key="LENS_CYCLE", value="<lens used>", version="<version from phase 1>")`.
   On a 409 conflict another turn advanced the register concurrently - re-read with
   `harness_state_get` and CAS again with the fresh version. This is best-effort bookkeeping: never
   fail the whole turn on it, but always attempt it so the rotation advances.

## Anti-patterns

- Taking any action before the phase-1 register read and the phase-2 context summary.
- A generic assertion with no `file:line` / SHA / graph finding behind it.
- Calling `tatara-deep-research` or `propose_issue` before the phase-5 scratchpad exists.
- More than one terminal action (one proposal / one comment / one skip) per turn.
- Silently skipping the register update, which strands the rotation on one lens forever.
