---
name: tatara-brainstorm-guardrails
description: "Hard rails and judgment heuristics for tatara brainstorm turns - read before any propose_issue, comment_on_issue, or skip_research call to ensure output is valid and non-duplicate."
profiles: ["brainstorm"]
---

# tatara brainstorm guardrails

REFERENCE skill. Defines the invariants, terminal-action rules, and quality heuristics for every brainstorm turn. Does not drive research - that is `tatara-deep-research` and `tatara-deep-architectural-research`. Advises inline alongside the agent's own reasoning; never a script.

## What the operator injects

`brainstormGoalProject` (projectscan.go) supplies:
- The list of target repository slugs.
- A live ISSUES / OPEN MRs / MAIN HEALTH context block (built from SCM ListOpenIssues + ListOpenPRs across all repos).
- An instruction to invoke `tatara-deep-research` (or `tatara-deep-architectural-research` for net-new architecture).
- An early-exit path: scan the ISSUES block cheaply before running the expensive per-repo fan-out.

The brainstorm MCP profile exposes: `task_list`, `propose_issue`, `comment_on_issue`, `skip_research`, all memory tools, all code-graph tools, all chat tools, and the alwaysOn set (`report_internal_issue`, `project_get`, `repo_list`, `task_get`).

## Hard rails (non-negotiable)

### 1. Dedup before the expensive fan-out - REQUIRED FIRST STEP

Before dispatching per-repo subagents:

1. Scan the injected ISSUES / OPEN MRs / MAIN HEALTH block. This contains the live open SCM proposals. Any idea that duplicates or is merely a sub-aspect of an entry here must NOT be proposed - call `skip_research(reason)` naming the duplicate (e.g. "Duplicate of szymonrychu/tatara-operator#N").
2. Call `task_list` (no args needed; defaults to `TATARA_PROJECT` env). This lists the operator Task ledger - inflight and recent tasks. Check whether work on the same domain is already queued or in-flight. If it is, treat as covered.

Both checks are cheap. Do them before the expensive fan-out, not after.

### 2. XOR terminal action

A brainstorm turn ends with exactly ONE of:

| Action | When |
|---|---|
| `skip_research(reason)` | No genuinely novel candidate clears the bar this cycle |
| `propose_issue(repo, title, body, kind, systemicId)` | Genuinely novel opportunity - one call per affected repo (even a one-repo finding), all sharing one `systemicId` you generate, bounded to at most 6 |
| `comment_on_issue(repo, number, body)` | Candidate extends an existing open issue - contributes concrete new design content |

No combinations. No silent exits. A turn that ends without one of these three is a protocol violation the operator will re-enqueue or wedge.

### 3. Novelty bar

`propose_issue` requires the idea to be:
- **Not already tracked**: no open SCM issue and no inflight Task covering the same problem (checked in step 1 above).
- **Grounded**: supported by file:line evidence from the code graph, not general intuition.
- **Actionable**: scoped so the maintainer can approve or redirect in one comment. Not "improve X generally."
- **Platform-compatible**: consistent with all platform rules (KISS, cluster-agnostic charts, no tech-debt, newest stable Go, JSON slog, /metrics endpoint, conventional commits). An incompatible proposal will be rejected at the implement gate.

If the candidate clears the bar but only as an extension of an existing issue, use `comment_on_issue` (not `propose_issue`).

### 4. Systemic cap

Every brainstorm proposal - whether it touches one repo or spans several - is framed as one project
Task's linked-issue set. Emit one `propose_issue` per affected repository, all sharing the same
`systemicId` string you generate (maximum 6). A one-repo finding still gets exactly one issue under
its own `systemicId`. This counts as ONE proposal against `maxOpenProposals`, not N.

### 5. No silent finish

`skip_research` must carry a concrete `reason`: what you surveyed and why nothing clears the bar (backlog at cap, all candidates duplicate open issues, no evidence of a high-leverage gap). A blank or one-word reason is not acceptable. A turn that ends without any terminal action is treated as a violation.

### 6. Discovery only, never self-implement

Do not open PRs, request CI triggers, or set approval labels. Every `propose_issue` body must embed the literal marker `<!-- tatara-authored -->` - the operator holds it in brainstorming state until a human approves. Implementation is gated on human sign-off; the brainstorm turn only discovers and proposes.

### 7. Per-cycle concurrency and cap (enforced externally)

The operator blocks a new brainstorm task when one is already in-flight (`brainstormInFlightProject`) and skips the cycle when `maxOpenProposals` is reached (default: 10; project-configured via `spec.activities.brainstorm.maxOpenProposals`). If this turn was triggered, the operator already cleared both gates - do not re-check or apply a lower cap.

## What is explicitly left open

These are judgment calls. This skill does not prescribe them:

- **Pain-point selection**: which category of problem is most worth surfacing this cycle (performance, reliability, DX, security, architecture). Your call.
- **Leverage scoring**: how to weigh impact vs effort vs reversibility vs novelty. Your call.
- **Option generation**: what concrete implementation options exist for each sub-problem. Your call.
- **Systemic vs local judgment**: whether a pattern is systemic enough to warrant a multi-repo `systemicId` group or is better scoped to one repo. Your call - the rail is only the 6-issue ceiling once you decide systemic.
- **Research depth**: how much graph traversal and subagent fan-out is warranted before concluding there is nothing to propose. The early-exit check is required; the depth of the full survey is not prescribed.
- **ADR vs issue**: whether a net-new architectural opportunity is better expressed as a long-lived ADR/RFC artifact (via `tatara-deep-architectural-research`) or as a scoped improvement issue. Your call.

The creative-space requirement is structural: the rails above are narrow by design so the agent retains full judgment on what is interesting, important, and worth proposing.

## Output quality heuristics

**Good `propose_issue` body:**
- One-paragraph problem statement with file:line evidence.
- Decomposition into constituent sub-problems / decision points.
- >=2 concrete approaches, each with a one-line tradeoff, and ONE explicitly flagged "Recommended".
- Maintainer decision framed as picking an approach (or redirecting) - NOT a list of open questions.
- Ends with `<!-- tatara-authored -->`.

**Good `comment_on_issue` body:**
Adds concrete design content not yet in the issue: new evidence, a concrete option, a tradeoff analysis. An empty or one-line vague comment is worse than `skip_research`.

**Good `skip_research` reason:**
Names the specific barrier with enough detail that a human reviewing the outcome understands why the cycle yielded nothing (e.g. "Surveyed tatara-operator and tatara-cli graph; all three candidate gaps duplicate open issues #N, #M, and #P. No novel high-leverage opportunity found this cycle.").

## Anti-patterns

- Running the expensive per-repo fan-out before the cheap early-exit dedup check.
- Opening a `propose_issue` that duplicates or merely restates an existing open SCM issue or inflight Task.
- Proposing vague "improve X" issues with no grounded file:line evidence.
- Using `comment_on_issue` with a one-line body that adds no concrete design content.
- Emitting more than one `propose_issue` in a turn without a `systemicId` grouping.
- Emitting more than 6 `propose_issue` calls even with a shared `systemicId`.
- Ending the turn without calling any of the three terminal actions.
- Requesting implementation, setting trigger/approval labels, or opening PRs from a brainstorm turn.
- Proposing work that violates any platform rule (non-cluster-agnostic charts, hand-rolled tech-debt, etc.).
- Reporting a platform tooling failure (MCP error, 401, missing access) as a tracker issue - use `report_internal_issue` for that exclusively.

## Relationship to other skills

| Skill | Role |
|---|---|
| `tatara-deep-research` | The workflow: orient, map, score, dedup, compose, file. Drives the turn. |
| `tatara-deep-architectural-research` | Variant for net-new architecture; produces long-lived ADR/RFC. |
| `tatara-brainstorm-guardrails` (this) | The rails: valid output shape, invariants, quality bar. Advises. |
