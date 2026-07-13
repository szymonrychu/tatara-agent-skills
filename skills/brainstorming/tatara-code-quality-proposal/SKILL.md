---
name: tatara-code-quality-proposal
description: "How a brainstorm turn grounds a code-quality / simplification / robustness proposal in the real source - read the shallow clones on disk and the code-graph MCP tools, then propose via submit_outcome. Read before proposing code-quality work."
profiles: ["brainstorm"]
---

# tatara code-quality proposal

REFERENCE skill. brainstorm is a project-scoped, read-only proposer. It never
pushes and never implements; it emits proposals through `submit_outcome` and the
operator turns each one into an issue and a clarify Task. This skill is how you
ground a code-quality proposal in real code rather than guessing.

## Read the real code (two signals, use both)

1. Shallow clones on disk. Every enrolled repo is cloned read-only (depth 1) into
   `workspace/<owner>/<repo>`; `repo_list` names them. Read the actual source,
   configs, and tests for deep, file-level detail.
2. Code-graph MCP tools (`tatara-mcp-code-graph`). Four tools index every enrolled
   repo in tatara-memory:
   - `code_search(repo, q)` - find entities by name or text.
   - `code_context(repo, rel=..., id=...)` - `related`, `cross_repo`, `callers`,
     `callees`, `dependents`, `dependencies`, `neighbors`, `file_imports`,
     `entity`.
   - `code_graph(repo, op=...)` - `important` (load-bearing entities),
     `communities` (subsystem clusters), `bridges` (coupling seams), `stats`,
     `path`, `hyperedges`, `ambiguous`, `resource_graph`.
   - `code_explain(repo, id)` - what a symbol link means.

   Use them for the whole-project map: hotspots, cross-repo duplication,
   over-abstracted or brittle areas.

Prefer graph queries first (cheap), then open the on-disk files the graph points
at (expensive) to confirm before proposing.

## What to propose

Simplification (remove premature abstraction, dead code, redundant layers),
robustness (missing error wrapping, unhandled failure modes, absent
metrics/logs for things that count or fail), and quality (test gaps on real
logic, KISS violations). Ground every claim in a concrete file or symbol you
actually read. No speculative "you might also want" features.

## How to propose

- Everything goes in ONE `submit_outcome` call:

      submit_outcome(action="propose",
                     proposals=[{repo, title, body, kind}, ...])   # 1..5

  One entry per issue you want opened. Each becomes its own issue and its own
  clarify Task - there is no umbrella and no `systemicId`. A cross-repo cleanup
  is N entries, and the clarify conversation on each settles its scope. See
  `tatara-brainstorm-guardrails` for the rails and `tatara-mcp-outcome` for the
  exact shape.
- If nothing clears the bar this cycle, call
  `submit_outcome(action="skip", reason=...)` and stop. Silence over noise.
- Duplicate of an existing open issue: do not propose it. Name the duplicate in
  your `skip` reason. You have no `issue_write`, so you cannot comment on it
  either.
- Never implement, never push, never open an MR. Proposals only - and the tools
  to do otherwise are not in your profile.
- No attribution or session links in any proposal body.
