---
name: tatara-evidence-and-citation
description: "REFERENCE - evidence and citation conventions for tatara agents: query the memory/code graph before reading raw files, cite file:line for every code-level claim, and never assert a codebase fact without a tool result proving it. Read in any research, triage, brainstorm, incident, or implement turn before making assertions about the platform."
---

# tatara evidence and citation

This is a REFERENCE skill. It defines the evidence standard and citation conventions that apply across every tatara agent kind. It ADVISES; it does not drive. The research procedure for a specific turn lives in the task skill for that kind (e.g. `tatara-deep-research`, `tatara-research-followup`, `tatara-health-check`).

## What the platform expects

Every injected turn-0 prompt that requires codebase investigation anchors its output requirement in evidence:

- `brainstormGoalProject` (`internal/controller/projectscan.go`): proposals must include "the concrete defect with file:line evidence from the code graph."
- `healthCheckGoalProject` (`internal/controller/projectscan.go`): proposals require "the concrete defect with file:line evidence, the proposed fix."
- `lifecycleTriageText` (`internal/controller/turnloop.go`): triage agents must "Use tatara MCP tools (memory, code search, docs) to understand the codebase" before deciding.
- `incident.GoalProject` (`internal/incident/goal.go`): the issue body MUST contain "the queries/tools you ran and their results."

The operator profile system (`internal/mcp/profiles.go`) makes all 13 memory tools (`groupMemory`) and all 19 code-graph tools (`groupCodeGraph`) available in every named profile. They are never gated away.

## The tool ladder

Use the cheapest tool that can answer the question. Ascend only when a lower rung is insufficient.

**Rung 1 - memory semantic search (cheapest, widest):**
- `query(mode, text, top_k)` - retrieve memory chunks matching the query. Mode options: `local` (entity-focused), `global` (community-focused), `hybrid` (both), `naive` (direct chunk retrieval). Start here for any conceptual or cross-repo question.
- `describe(mode, text, top_k)` - same as query but returns a generative answer plus source paths. Use when you need a synthesized answer, not just chunks.
- `search_entities(q)` / `get_entity(id)` - direct entity lookup in the knowledge graph.

**Rung 2 - code graph traversal (precise, structural):**
- `code_search(repo, q, type, limit)` - find entities by name/description within a repo. Required arg: `repo` (slug e.g. `szymonrychu/tatara-cli`).
- `code_entity(repo, id)` - single entity plus its immediate edges. Use to confirm a candidate exists and see its direct connections.
- `code_explain(id, repo)` - full context: detail, in/out neighbors with file locations. This is the primary tool for building a `file:line` citation.
- `code_neighbors(repo, id, relation, direction, depth, min_confidence, tier)` - graph traversal from a known entity. Optional depth and confidence filters.
- `code_callers(repo, id, depth)` / `code_callees(repo, id, depth)` - call-graph traversal (reverse / forward).
- `code_dependents(repo, id, depth)` / `code_dependencies(repo, id, depth)` - import/reference traversal (reverse / forward).
- `code_cross_repo(repo, id)` - cross-repo symbol links: who consumes what the entity provides, who provides what it requires.
- `code_path(repo, from, to, relations, max_depth)` - shortest path between two entities.
- `code_related(id, repo, relations, min_confidence)` - semantic edges (conceptually_related_to, semantically_similar_to, rationale_for, shares_data_with, cites).

**Rung 3 - graph analytics (orientation, not citation):**
- `code_important(repo, limit, by)` - highest-degree or highest-betweenness entities. Use to orient in an unfamiliar repo; not a citation source on its own.
- `code_stats(repo)` - entity/edge counts, types, tiers, isolated entities, import cycles. Use for structural orientation.
- `code_communities(repo, community)` - detected communities. Use to identify module boundaries.
- `code_bridges(repo, limit)` - high-betweenness entities bridging communities. Use to find integration points.
- `code_ambiguous_edges(repo, limit)` - low-confidence or AMBIGUOUS-tier edges. Use to flag uncertain relationships.
- `code_hyperedges(repo, entity, id)` - n-ary group relations. Use when a relationship involves more than two entities.
- `code_file_imports(repo, path)` - imports out of a file's package.
- `code_resource_graph(repo, id, depth)` - Terraform/Helm dependency subgraph for infrastructure resources.

**Rung 4 - raw file read (most expensive, use as fallback):**
Raw file reads (Read tool, Bash cat, etc.) are appropriate when the code graph lacks coverage for a specific location (new files not yet ingested, generated code, inline values) or when the graph result must be verified against the literal source. Raw reads without a prior graph query are inefficient and produce unchecked citations.

## Citation format

A claim is cited when a reader can verify it without re-running the investigation. Citation precision matches claim precision:

- **Code entity claim**: `<entity-name> (<file>:<line>)`. Example: `BuildPod (internal/agent/pod.go:201)`. Source: `code_explain` result which includes file locations.
- **Code relationship claim**: name both endpoints and the relation. Example: "`brainstormGoalProject` calls `appendGuidance` via a direct call edge." Source: `code_callers` or `code_callees`.
- **Memory / conceptual claim**: name the query and mode used, quote the key phrase from the result. Example: `query(hybrid, "incident goal evidence requirements") -> "the body MUST contain: the alert summary, the queries/tools you ran"`.
- **Grafana / observability claim**: include the query string, datasource, and result. Example: `query_prometheus("sum(rate(...))")` returned 0.03 req/s at T.
- **Cross-repo claim**: run `code_cross_repo(repo, id)` before asserting that entity X in repo A is consumed by repo B.

When a line number is unavailable (the graph returned a file path only), note that and cite file path. Do not omit the file entirely.

## Hard rails

These apply to every agent kind in every profile. Violating them produces unverifiable output that the operator and maintainer cannot act on.

**Claim without proof is not a claim.** If you cannot point to a tool result (memory chunk, graph node, file:line, Grafana query output), do not assert the fact. Use "I could not confirm" or run the tool first.

**Graph before raw read.** Before opening a raw file to answer a question about code structure, run `code_search` or `code_entity` for the entity, then `code_explain` for detail. Raw read is a verification step, not the entry point.

**Include tool results in issue bodies.** For `propose_issue` and `comment` output, paste the relevant graph result excerpt or query output. Saying "I checked the code graph" without quoting the result is not evidence.

**`report_internal_issue` for tool failures; do not mask them.** If a graph tool returns an error or empty result that you did not expect, call `report_internal_issue(category="tool_error", description="...", offending_tool="...")` and note the gap explicitly in your output. Do not silently proceed as if the tool succeeded.

## Judgment calls (left to the agent)

The following are open; the agent applies its own judgment:

- Which `query` mode (local / global / hybrid / naive) fits the question. Hybrid is a reasonable default for cross-cutting conceptual questions; local for entity-focused; global for community-level patterns.
- How deep to traverse (the `depth` parameter on `code_neighbors`, `code_callers`, `code_callees`). Depth 1 is usually enough to establish a direct relationship; go deeper only when the question is about transitive impact.
- Whether `describe` or `query` is the right memory tool. `describe` synthesizes; `query` returns raw chunks. Prefer `query` when you need to quote the source verbatim; prefer `describe` when you need a structured answer you will paraphrase.
- How many entities to surface via `code_important`. More is not always better; the top 10 by degree is usually sufficient for orientation.
- When a graph gap justifies a raw read vs when it is acceptable to note "coverage unavailable." New or generated files not yet ingested into the graph are common; note the gap and read the file.

## Anti-patterns

- Asserting "this function does X" with no `code_explain` or `code_entity` result to support it.
- Citing a file name without a line number when `code_explain` returned line locations.
- Running raw file reads on every relevant file before trying `code_search` or `code_entity`.
- Writing "I confirmed in the codebase that..." without quoting the tool output.
- Claiming a cross-repo dependency without running `code_cross_repo`.
- Submitting a `propose_issue` body that says "file:line evidence: TBD" or omits evidence entirely.
- Treating `code_important` results alone as evidence of a bug or problem. High betweenness/degree means the entity is structurally central; it does not imply defect.
- Inferring code structure from memory chunks alone when code-graph tools are available and the entity has been ingested.

## What belongs here vs in the task skill

This skill defines the evidence standard (what constitutes a valid citation, when to use each tool family, what the hard rails are). The task skill for each agent kind defines the workflow (how many steps, what to output, when to call which MCP outcome tool). Read both; this skill's conventions apply whenever you make a factual assertion inside that workflow.
