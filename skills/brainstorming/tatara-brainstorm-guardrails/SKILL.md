---
name: tatara-brainstorm-guardrails
description: "Hard rails and judgment heuristics for tatara brainstorm turns - read before submit_outcome to ensure the proposals are valid, grounded, and non-duplicate."
profiles: ["brainstorm"]
---

# tatara brainstorm guardrails

REFERENCE skill. Defines the invariants, terminal-action rules, and quality
heuristics for every brainstorm turn. Does not drive research - that is
`tatara-deep-research` and `tatara-deep-architectural-research`. Advises inline
alongside the agent's own reasoning; never a script.

## What you have

Your bundle carries your Task, the compact project-wide index of prior
brainstorms (`<task_index>`), and your assignment - including the architectural
LENS the operator selected for this cycle. Pull any indexed Task's full bundle on
demand with `task_context(task=<name>)`.

Your tool surface (per `tatara-mcp-platform`, `tatara-mcp-scm`,
`tatara-mcp-code-graph`, `tatara-mcp-memory`, `tatara-mcp-outcome`):

- always-on: `task_get`, `task_context`, `task_note`, `project_get`, `repo_list`,
  `report_internal_issue`
- `task_list`
- `scm_read` - read the forge (issues, MRs, comments, commits, CI)
- all four code-graph tools, `memory_query` / `memory_describe` /
  `memory_write` / `memory_entity`
- `submit_outcome`

**You have NO `issue_write` and NO `mr_write`.** You cannot comment on an issue,
you cannot open an MR, and you cannot label anything. Everything you want to
exist in the forge, you propose through `submit_outcome`, and the OPERATOR
creates it.

## Hard rails (non-negotiable)

### 1. Dedup before the expensive fan-out - REQUIRED FIRST STEP

Before dispatching per-repo subagents:

1. Read the open issues and MRs: `scm_read(kind="issues", repo=..., state="open")`
   and `scm_read(kind="mr", repo=..., state="open")` across the repos in scope
   (`repo_list`). Any idea that duplicates or is merely a sub-aspect of one of
   these must NOT be proposed.
2. Read the `<task_index>` in your bundle, and `task_list`, for work already
   queued or in flight on the same domain. If it is there, treat it as covered.

Both checks are cheap. Do them before the expensive fan-out, not after.

### 2. XOR terminal action

A brainstorm turn ends with exactly ONE `submit_outcome`, in one of two shapes:

| Action | When |
|---|---|
| `submit_outcome(action="skip", reason=...)` | No genuinely novel candidate clears the bar this cycle |
| `submit_outcome(action="propose", proposals=[{repo, title, body, kind}, ...])` | One or more genuinely novel opportunities - between 1 and 5 proposals, one entry per issue you want opened |

No combinations. No silent exits. **A turn that ends without an outcome does not
quietly stop:** the Task ages out at `stageReason=no-outcome`, the pod is
deleted, and the work is lost.

There is no third "comment on the existing issue instead" action any more. You
have no `issue_write`. If your candidate is only an extension of an open issue,
that is a `skip` naming the issue - not a proposal, and not a comment.

### 3. Novelty bar

A proposal must be:

- **Not already tracked**: no open forge issue and no in-flight Task covering the
  same problem (checked in rail 1).
- **Grounded**: supported by `file:line` evidence from the code graph and the code
  you actually read, not general intuition.
- **Actionable**: scoped so a maintainer can approve it, or redirect it with a
  comment, without further back-and-forth. Not "improve X generally."
- **Platform-compatible**: consistent with the platform rules (KISS,
  cluster-agnostic charts, no tech debt, newest stable Go, JSON slog, `/metrics`).
  An incompatible proposal is rejected downstream.

### 4. What a proposal becomes

Each entry in `proposals[]` becomes its OWN issue and its OWN clarify Task. There
is no umbrella, no `systemicId`, and no linked-issue group: a cross-repo finding
is N proposals, and the clarify conversation on each is where scope gets settled.
The array is capped at 5 by the schema.

`kind` is `bug` or `improvement`.

### 5. No silent finish

`skip` must carry a concrete `reason`: what you surveyed and why nothing clears
the bar (all candidates duplicate open issues; no evidence of a high-leverage
gap; the backlog already covers the lens you were given). A blank or one-word
reason is not acceptable.

### 6. Discovery only, never self-implement

You do not open MRs, request CI, approve anything, or label anything. The tools
do not exist in your profile. **Approval is a maintainer's comment on the issue,
matching the project's `approvalPhrases` as a whole line, verified by the
operator** - and it happens on the clarify Task the operator mints from your
proposal, long after your pod is gone. Nothing you write in a proposal body
advances that gate; do not pretend otherwise in the prose.

### 7. Concurrency and cap (enforced externally)

The operator gates how many Tasks a project may have open (`maxOpenTasks`) and
how many agents may run at once (`maxConcurrentAgents`). If your turn was
triggered, the operator already cleared those gates - do not re-check them or
apply a lower cap of your own.

## What is explicitly left open

These are judgment calls. This skill does not prescribe them:

- **Pain-point selection**: which category of problem is most worth surfacing
  through this cycle's lens (performance, reliability, DX, security,
  architecture). Your call.
- **Leverage scoring**: how to weigh impact vs effort vs reversibility vs
  novelty. Your call.
- **Option generation**: what concrete implementation options exist for each
  sub-problem. Your call.
- **One proposal or several**: whether a pattern is systemic enough to warrant
  several proposals across repos or is better scoped to one. Your call - the rail
  is only the 5-entry ceiling.
- **Research depth**: how much graph traversal and subagent fan-out is warranted
  before concluding there is nothing to propose. The early-exit check is
  required; the depth of the full survey is not prescribed.
- **ADR vs issue**: whether a net-new architectural opportunity is better
  expressed as a long-lived ADR/RFC artifact (via
  `tatara-deep-architectural-research`) or as a scoped improvement issue. Your
  call.

The creative-space requirement is structural: the rails above are narrow by
design so the agent retains full judgment on what is interesting, important, and
worth proposing.

## Output quality heuristics

**Good proposal body:**
- One-paragraph problem statement with `file:line` evidence.
- Decomposition into constituent sub-problems / decision points.
- At least 2 concrete approaches, each with a one-line tradeoff, and ONE
  explicitly flagged "Recommended".
- The maintainer's decision framed as picking an approach (or redirecting) - NOT
  a list of open questions.

**Good `skip` reason:**
Names the specific barrier with enough detail that a human reading the outcome
understands why the cycle yielded nothing. For example: "Surveyed tatara-operator
and tatara-cli through the coupling lens; all three candidate gaps duplicate open
issues tatara-operator#N, #M and tatara-cli#P. No novel high-leverage opportunity
this cycle."

## Anti-patterns

- Running the expensive per-repo fan-out before the cheap early-exit dedup check.
- Proposing something that duplicates or merely restates an open forge issue or
  an in-flight Task.
- Proposing vague "improve X" issues with no grounded `file:line` evidence.
- Emitting more than 5 proposals, or more than one `submit_outcome`.
- Ending the turn without calling `submit_outcome`.
- Trying to comment on an issue, open an MR, or label anything. You have none of
  those tools.
- Proposing work that violates a platform rule (non-cluster-agnostic charts,
  hand-rolled tech debt).
- Reporting a platform tooling failure (an MCP error, a 401, missing access) as a
  proposal - use `report_internal_issue` for that, exclusively.
- Stopping without a `task_note(kind="handoff")`. See `handoff`.

## Relationship to other skills

| Skill | Role |
|---|---|
| `tatara-council-brainstorm` | The harness: lens, evidence gates, scratchpad, terminal action. Owns the turn. |
| `tatara-deep-research` | The workflow: orient, map, score, dedup, compose, file. |
| `tatara-deep-architectural-research` | Variant for net-new architecture; produces a long-lived ADR/RFC. |
| `tatara-brainstorm-guardrails` (this) | The rails: valid output shape, invariants, quality bar. Advises. |
| `tatara-mcp-outcome` | The exact `submit_outcome` shapes. |
