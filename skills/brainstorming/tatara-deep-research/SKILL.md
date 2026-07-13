---
name: tatara-deep-research
description: "Use on a brainstorm turn to research ONE high-leverage improvement for the tatara platform. Researches deeply across the whole platform using the tatara-memory knowledge/code graph plus the on-disk repos, scores leverage, dedups against open issues and in-flight Tasks, then takes exactly one action: submit_outcome(action=propose) with 1..5 grounded proposals when something is genuinely novel, or submit_outcome(action=skip) when nothing clears the bar. Never self-implemented."
profiles: ["brainstorm"]
---

# tatara deep research

Discover ONE high-leverage improvement per run, then take exactly one
action: `submit_outcome(action="propose")` (novel, shippable) or
`submit_outcome(action="skip")` (honest no-yield). All input and output go through
the `tatara` MCP server. You never use git or gh; you never open or comment
on an issue yourself - the OPERATOR opens an issue from each accepted proposal,
under the bot identity, and mints a clarify Task for it.

## Hard constraints

- ONE outcome per run. **A run that submits no outcome does not quietly end:** the
  Task ages out at `stageReason=no-outcome`, the pod is deleted, and the work is
  lost. If nothing is genuinely novel, that is `submit_outcome(action="skip",
  reason=...)` - an honest no-yield, not silence.
- **You have no `issue_write` and no `mr_write`.** There is no "comment on the
  existing issue instead" path any more. An idea that only extends an open issue
  is a `skip` that names that issue, not a proposal and not a comment.
- Stay in discovery. Do NOT request implementation. Approval happens later, on the
  clarify Task the operator mints from your proposal, when a maintainer posts a
  comment that CONSISTS OF one of the project's approval phrases and the operator
  verifies both the identity and the wording. Nothing you write advances that
  gate; never imply in a proposal body that it does.
- Every proposal must respect the platform's hard rules (read the on-disk
  `CLAUDE.md`), or the loop that later implements it will reject it. KISS; no
  tech debt; charts cluster-agnostic; conventional commits; newest stable Go;
  JSON slog + INFO business logging + /metrics.
- Communication only via `tatara` MCP tools.

## Orchestration (context-boundary subagent dispatch)

This is a deep, cross-repo research turn. Sustain multi-step reasoning
yourself for the synthesis step; keep your own context lean by fanning the
per-repo LEGWORK out to subagents rather than reading every repo inline.

- **Decompose** the cross-repo survey into one independent unit of work per
  repository in the Project (the repos under `/workspace/*/` plus the
  cross-repo graph view).
- **Dispatch one `explorer` subagent per repo** (via the `Agent` tool, `model:
  haiku`, `effort: low` - explorer's baked defaults) to gather that repo's
  state: roadmap themes, fragile/load-bearing code via the code-graph
  tools, open issues and MRs, recurring debt. Launch them in a single message so
  they run concurrently; do not serialize what can fan out. Each explorer
  reports back a compact summary (`file:line` evidence, not full-file dumps) -
  this is what keeps your own surface context under the ~50% budget where
  reasoning degrades.
- **Synthesize** the subagent reports yourself into the single highest-leverage
  opportunity - prefer a pattern spanning 2 or more repos, a platform-wide gap, or
  recurring debt over a one-repo tweak, but a well-evidenced one-repo finding
  is a valid outcome too.
- A systemic improvement is several entries in ONE `proposals[]` array (capped at
  5), one per affected repo. Each entry becomes its OWN issue and its OWN clarify
  Task - there is no umbrella and no `systemicId`. Name the siblings in each body
  so the humans reading three new issues can see they are one design.

The `tatara` tools auto-scope to your current task and project from the pod
environment. Do NOT try to pass an environment variable as an argument
(you cannot expand it) - just omit the `task`/`project` args and the tool
fills them in. `repo_list` gives you the Repository CR names that the `code_*`
and `scm_read` tools want as `repo=`.

## Workflow

Create a TodoWrite item per numbered step.

1. **Orient on goals.** The Project's repos are cloned under
   `/workspace/<owner>/<repo>` (e.g. `/workspace/szymonrychu/tatara-operator`);
   run `ls /workspace/*/` to list them. Read each repo's on-disk `ROADMAP.md`,
   `MEMORY.md`, and `CLAUDE.md` (the platform goal, the repo charter, the hard
   rules). Then use the memory tools for the wider picture: `memory_query` (mode
   global or hybrid) for "tatara platform goal" and "open roadmap themes";
   `memory_describe` for an overview of a target repo.

2. **Map current state.** Use the code-graph tools to find where the
   system is fragile or under-optimized, repo-scoped where useful:
   `code_graph(op="stats")`, `code_graph(op="important")` (high-PageRank entities
   = load-bearing code), `code_graph(op="communities")` (subsystem clustering),
   `code_graph(op="bridges")` (coupling/risk), and
   `code_context(rel="cross_repo")` (cross-repo edges - cross-repo understanding
   MUST come from the graph). Then READ the actual on-disk code for the strongest
   candidate area to confirm what the graph suggested.

3. **Score leverage.** Rank candidate improvements by impact in this
   order: (a) reliability/observability of the LIVE autonomous loop
   (it is dogfooding in production and surfaces real bugs); (b) un-built
   but planned loop features; (c) the SOTA backlog; (d) deploy
   debt. Respect gates: do NOT propose downstream memory ranking/reranker
   work before the memory retrieval-quality eval harness exists. Pick the
   single highest-leverage, well-scoped item.

4. **Dedup - and there is no comment path.** Before acting, call `task_list`,
   read the `<task_index>` in your bundle, and read the open backlog with
   `scm_read(kind="issues", repo=..., state="open")`:
   - **Duplicate** of an already-open issue, or of an in-flight Task -> do NOT
     propose it. Either pick the next-best novel candidate, or
     `submit_outcome(action="skip", reason=...)` naming the duplicate.
   - **Extends / is a sub-aspect of** an existing open issue -> same thing. You
     have no `issue_write`, so you cannot add your design note to that thread.
     Skip, naming the issue and, in one line, the addition you would have made -
     the next cycle's pod reads your `task_note(kind="handoff")` and can carry it.
   - **Genuinely novel and standalone** -> proceed to compose a proposal (step 5).

5. **Compose the proposal(s), each split into 2 or more approaches.** Per entry:
   - `title`: imperative, specific (e.g. "Add per-item ingest timeout to the
     memory ingest worker").
   - `body`: Problem (what hurts, why it matters to the platform/repo goal);
     Evidence (`file:line` references and concrete graph findings from
     steps 1-2); at least 2 concrete approaches, each with a one-line
     tradeoff, with ONE explicitly flagged "Recommended"; Scope boundary
     (what is in and explicitly out, per approach if it differs). Do NOT
     list open questions that invite back-and-forth - the maintainer's job
     is to pick an approach (or redirect), not to answer a design
     questionnaire.
   - `repo`: the Repository CR name from `repo_list`.
   - `kind`: `improvement` or `bug`.

6. **File it.**

       submit_outcome(action="propose",
                      proposals=[{repo, title, body, kind}, ...])   # 1..5

   Then write `task_note(kind="handoff", body=...)` - what you surveyed, what you
   ruled out and why - and stop. The next cycle starts from it.

## Anti-patterns

- Submitting more than one outcome in a run, or none at all.
- Trying to comment on an existing issue. brainstorm has no `issue_write`; the
  right move is a `skip` that names the issue.
- Proposing vague "improve X" issues with no `file:line` evidence.
- Requesting implementation, or claiming a proposal body can approve itself.
- Proposing memory ranking work before the eval-harness gate.
- Reading only the on-disk repo and ignoring the cross-repo graph.
