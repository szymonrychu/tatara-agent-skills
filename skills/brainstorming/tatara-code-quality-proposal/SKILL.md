---
name: tatara-code-quality-proposal
description: "How a brainstorm turn grounds a code-quality / simplification / robustness proposal in the real source - read the shallow clones on disk and the code-graph MCP tools, then propose via propose_issue. Read before proposing code-quality work."
profiles: ["brainstorm"]
---

# tatara code-quality proposal

REFERENCE skill. brainstorm is a project-scoped, read-only proposer. It never
pushes and never implements; it emits `propose_issue` proposals under the
`maxOpenProposals` cap. This skill is how you ground a code-quality proposal in
real code rather than guessing.

## Read the real code (two signals, use both)

1. Shallow clones on disk. Every enrolled repo listed in `TATARA_REPOS` is
   cloned read-only (depth 1) into `workspace/<owner>/<repo>`. Read the actual
   source, configs, and tests for deep, file-level detail.
2. Code-graph MCP tools. `code_search`, `code_explain`, `code_related`,
   `code_important`, `code_cross_repo`, `code_bridges`, `code_communities` index
   every enrolled repo in tatara-memory. Use them for the whole-project map:
   find hotspots, cross-repo duplication, over-abstracted or brittle areas.

Prefer graph queries first (cheap), then open the on-disk files the graph points
at (expensive) to confirm before proposing.

## What to propose

Simplification (remove premature abstraction, dead code, redundant layers),
robustness (missing error wrapping, unhandled failure modes, absent
metrics/logs for things that count/fail), and quality (test gaps on real logic,
KISS violations). Ground every claim in a concrete file/symbol you actually
read. No speculative "you might also want" features.

## How to propose

- One `propose_issue` per affected repo under a shared `systemicId` (bounded
  to 6) - true even for a one-repo improvement; see
  `tatara-brainstorm-guardrails` for the umbrella-Task framing.
- Respect `maxOpenProposals`: if nothing clears the bar this cycle, call
  `skip_research(reason)` and stop. Silence over noise.
- Duplicate of an existing open issue: do not propose; note the duplicate.
- Every `propose_issue` body MUST embed the `<!-- tatara-authored -->` marker
  (per tatara-brainstorm-guardrails). The operator holds the proposal in the
  brainstorming state until a maintainer (per `MaintainerLogins`, bots
  excluded) applies the `tatara-approved` label directly on the issue - a
  comment does not advance it; omitting the marker bypasses this gate.
- Never implement, never push, never open a PR. Proposals only.
- No attribution or session links in any proposal body or comment.
