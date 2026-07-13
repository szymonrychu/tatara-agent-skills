---
name: tatara-deep-architectural-research
description: Use on an architectural-research turn to discover ONE high-leverage structural improvement for the tatara platform. Walks SCOPE -> MAP INWARD -> (Phase-1 stubbed) SURVEY -> ASSESS FIT -> NOVELTY -> SYNTHESIZE ADR -> PROPOSE; Phase-1 external field survey deferred (memory graph + on-disk only); the terminal no-yield action is submit_outcome(action=skip); never self-implemented.
profiles: ["brainstorm"]
---

# tatara deep architectural research

Discover ONE high-leverage structural improvement per run, produce an
ADR/RFC artifact, then report it through `submit_outcome(action="propose")` - or
`submit_outcome(action="skip")` when nothing novel or shippable emerges. All input
and output go through the
`tatara` MCP server. You never use git or gh directly; you never open an
issue yourself - the OPERATOR opens it from your accepted proposal, under the
bot identity.

## Hard constraints

- ONE outcome per run: `submit_outcome(action="propose", proposals=[...])` (novel,
  shippable) or `submit_outcome(action="skip", reason=...)` (honest no-yield). No
  partial outputs, no implementation requests. **A run that submits no outcome
  ages out at `no-outcome` and the work is lost.**
- Discovery-only. You have no `issue_write`, no `mr_write`, no label and no merge.
  Approval happens later, on the clarify Task the operator mints from your
  proposal, when a maintainer posts a whole-line approval phrase and the operator
  verifies it. Nothing you write advances that gate; never imply in a proposal
  body that it does.
- Respect every platform hard rule (read the on-disk `CLAUDE.md`): KISS, no
  tech debt, charts cluster-agnostic, conventional commits, newest stable Go,
  JSON slog + INFO business logging + /metrics.
- Communication only via `tatara` MCP tools.
- Use the ADR template and Technology Radar convention in
  [`adr-template.md`](adr-template.md) for the SYNTHESIZE artifact.

## Orchestration (context-boundary subagent dispatch)

This is a deep, cross-repo architectural research turn. Sustain multi-step
reasoning yourself for MAP INWARD / ASSESS FIT / SYNTHESIZE; keep your own
context lean by fanning per-repo legwork out to subagents.

- **Decompose** the cross-repo survey into one independent unit of work per
  repository in the Project (repos under `/workspace/*/` plus the
  cross-repo graph view).
- **Dispatch one `explorer` subagent per repo** (via the `Agent` tool,
  `model: haiku`, `effort: low`) to gather that repo's state: MEMORY themes,
  fragile/load-bearing code via the code-graph tools, open issues and MRs,
  recurring debt. Launch them in a single message so they run concurrently;
  do not serialize what can fan out. Each reports back compact evidence, not
  full-file dumps - this is what keeps your own context under the ~50%
  budget.
- **Synthesize** the subagent reports yourself into the single
  highest-leverage SYSTEMIC opportunity - a pattern spanning 2 or more repos, a
  platform-wide gap, or recurring debt - in preference to a one-repo tweak.
- A genuinely systemic improvement is several entries in ONE `proposals[]` array
  (capped at 5), one per affected repo. Each becomes its own issue and its own
  clarify Task; there is no umbrella and no `systemicId`. Name the siblings in
  each body so the humans can see the three new issues are one design.

The `tatara` tools auto-scope to your current task and project from the pod
environment. Do NOT try to pass an environment variable as an argument
(you cannot expand it) - omit the `task`/`project` args and the tool fills
them in. `repo_list` gives you the Repository CR names the `code_*` and
`scm_read` tools want as `repo=`.

## Workflow

Create a TodoWrite item per numbered step.

1. **SCOPE** - pick ONE pain-point from your assignment, MEMORY, ROADMAP, or
   a failing fitness function. State it as a problem, not a solution (e.g.
   "direct github SDK imports in operator core block adding GitLab support"
   not "add GitLab"). Read the Project's repos via `ls /workspace/*/`, then
   read each repo's `MEMORY.md`, `ROADMAP.md`, and `CLAUDE.md`. Use
   `memory_query` (mode global or hybrid) for "tatara platform goal" and
   "open roadmap themes" to situate the problem in context.

2. **MAP INWARD** - establish what tatara does today and where the
   coupling/debt lives. Use the code-graph tools: `code_graph(op="stats")`,
   `code_graph(op="important")` (high-PageRank load-bearing entities),
   `code_graph(op="communities")` (subsystem clusters),
   `code_graph(op="bridges")` (coupling/risk seams), and
   `code_context(rel="cross_repo")` (cross-repo edges). The pod has the repos on
   disk, but cross-repo UNDERSTANDING comes from the graph. Then read the actual
   on-disk code for the strongest candidate area to confirm what the graph
   suggested. Dispatch one parallel subagent per repo for concurrent coverage.

3. **SURVEY THE FIELD** - **STUBBED for Phase 1.** External web/academic
   research is not yet wired (Phase 2). For now, survey only the memory
   graph and on-disk repos for prior art and comparable patterns already
   inside tatara. Record "field survey: external sources not yet available"
   as an explicit open question to carry into the ADR. Do not attempt
   WebSearch or WebFetch. In Phase 2 this step will activate outbound search
   (arXiv, OpenAlex, web) to find existing systems and papers that address
   this class of problem.

4. **ASSESS FIT** - score candidates against tatara's hard constraints:
   frozen model, headless, GitOps-only, KISS, no tech debt. Reject anything
   needing weight updates or live self-patch. Produce 2-3 surviving options
   with explicit tradeoffs. Prefer strangler-fig approaches (behavior-
   preserving, reversible, incrementally shippable) over big-bang rewrites.

5. **NOVELTY + LEARN** - OMNI-style gate. Is this genuinely novel vs past
   proposals (`task_list`, the `<task_index>` in your bundle, and
   `scm_read(kind="issues", repo=..., state="open")`)? And is it shippable now given the
   repo state? If neither - call `submit_outcome(action="skip", reason=...)` and
   stop. A near-duplicate, or a proposal blocked by an unmet prerequisite, does
   not advance the platform.

6. **SYNTHESIZE** - produce an ADR artifact following the template in
   [`adr-template.md`](adr-template.md): problem statement, evidence
   (`file:line` references + graph findings from steps 1-2), 2-3 options with
   on-disk citations (Phase-1) and a recommended option, a strangler-fig
   migration sketch, and the fitness function (CI check) that would gate the
   decision over time. Open questions are explicitly ALLOWED here - including
   the carried "field survey: external sources not yet available" follow-up
   from step 3. This is the ADR/RFC artifact that outlives the turn.

7. **PROPOSE** - file the ADR-backed proposal:

       submit_outcome(action="propose",
                      proposals=[{repo, title, body, kind}, ...])   # 1..5

   Include the full ADR text in the body. `kind` is `improvement` for structural
   work, `bug` only for a real defect. Write a `task_note(kind="handoff")` with
   what you surveyed and ruled out - the next cycle reads it - and stop.

## Anti-patterns

- Submitting more than one outcome, or none at all.
- Requesting implementation of your own proposal, or implying a proposal body
  can approve itself.
- Looking for a label or a status to set. `issue_write` is not in your profile,
  and it has no `labels` and no `status` parameter anywhere on the platform.
- Proposing a vague "improve X" issue with no `file:line` evidence.
- Attempting WebSearch/WebFetch in Phase 1 (egress is not yet wired).
- Proposing memory ranking work before the eval-harness gate exists.
- Reading only the on-disk repo and ignoring the cross-repo graph.
- Producing an issue body that lists open questions (they go in the ADR
  artifact; the issue body has one well-researched decision for approval).
