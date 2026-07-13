---
name: tatara-mcp-code-graph
description: >
  Drive the 4 code_* code-graph MCP tools (groupCodeGraph) to orient in an
  unfamiliar codebase, trace call chains, map dependencies, find coupling
  hotspots, and explain cross-repo symbol links. Use whenever you need to
  understand code structure before reading files, trace a bug across call
  boundaries, assess impact of a change, or locate tightly-coupled subsystems.
  Available in every agent profile except refine.
profiles: ["brainstorm", "implement", "incident", "review", "clarify", "documentation"]
---

# tatara-mcp-code-graph

All 4 tools in `groupCodeGraph` hit the tatara-memory backend
(Target=TargetMemory) at `/code/...` and `/code-graph/...` routes. Tool names
are exact; use them verbatim. `code_graph` is not available in the `clarify`
profile (D.6); the other three are.

The `repo` argument is always a slug like `szymonrychu/tatara-cli`. Every
tool requires it; it scopes results to one repository's code graph.

## Tool index

| Tool | Args (required*) | Purpose |
|------|-----------------|---------|
| `code_search` | `repo`* `q`* `type` `limit` | Keyword search over entities (name + description). **Entry point.** Everything else takes an `id` you got from here. |
| `code_context` | `repo`* `rel`* `id` `depth` `relation` `direction` `limit` | One entity's neighbourhood. `rel` selects the view: `entity`, `neighbors`, `callers`, `callees`, `dependents`, `dependencies`, `file_imports`, `related`, `cross_repo`. `depth` defaults to 1, max 4. |
| `code_graph` | `repo`* `op`* `from` `to` `community` `id` `limit` | Whole-graph analysis. `op` selects the view: `path`, `important`, `stats`, `ambiguous`, `communities`, `hyperedges`, `bridges`, `resource_graph`. |
| `code_explain` | `repo`* `id`* | Full context: detail, in/out neighbors with file locations. |

### `code_context` rel values

| `rel` | Old tool | Extra args |
|-------|----------|------------|
| `entity` | `code_entity` | - |
| `neighbors` | `code_neighbors` | `relation`, `direction` (`out`\|`in`) |
| `callers` | `code_callers` | `depth` |
| `callees` | `code_callees` | `depth` |
| `dependents` | `code_dependents` | `depth` |
| `dependencies` | `code_dependencies` | `depth` |
| `file_imports` | `code_file_imports` | `id` (the file entity's id, from `code_search`) |
| `related` | `code_related` | - |
| `cross_repo` | `code_cross_repo` | - |

### `code_graph` op values

| `op` | Old tool | Extra args |
|------|----------|------------|
| `path` | `code_path` | `from`*, `to`* |
| `important` | `code_important` | `limit` |
| `stats` | `code_stats` | - |
| `ambiguous` | `code_ambiguous_edges` | `limit` |
| `communities` | `code_communities` | `community` (int, omit for the full list) |
| `hyperedges` | `code_hyperedges` | `id` (one hyperedge, omit for the full list) |
| `bridges` | `code_bridges` | `limit` |
| `resource_graph` | `code_resource_graph` | `id`* |

## Orientation: first move in an unfamiliar repo

Run both before reading any files. These establish the map.

```
1. code_graph(repo="szymonrychu/<repo>", op="stats")
   -> Read: total entity count, entity type breakdown (function, file, type, etc.),
      edge count, isolated entities, import cycles.
   -> If import_cycles is non-empty, note them; they indicate design debt.

2. code_graph(repo="szymonrychu/<repo>", op="important", limit=20)
   -> Returns the top 20 most important entities in the graph.
   -> Skim names: these are the load-bearing symbols. Start here when asked
      "where is the core logic?".
```

Skip orientation if you already have a specific entry point (a symbol name or
file path). Go straight to Workflow 1 or 2.

## Workflow 1: Locate an entity and understand it

Use when you have a name, partial name, or concept to look up.

```
1. code_search(repo="szymonrychu/<repo>", q="<name or keyword>", type="<type>")
   -> Returns matching entity stubs. Scan names and descriptions.
   -> `type` is optional but narrows results when you know the kind
      (e.g. "function", "type", "file", "resource").

2. code_context(repo="szymonrychu/<repo>", rel="entity", id="<entity_id>")
   -> Returns the full entity: fields, description, and ALL immediate edges
      (in and out). Edge list shows relation types.
   -> Use the edge list to decide what to traverse next.

3. code_explain(repo="szymonrychu/<repo>", id="<entity_id>")
   -> Richer than code_context(rel="entity"): includes narrative detail,
      in-neighbor list with file locations, out-neighbor list with file
      locations.
   -> Use this when you need to understand WHY an entity exists and HOW it
      connects to the rest of the graph, not just WHAT it is.
```

`code_context(rel="entity")` is fast; use it for structural questions.
`code_explain` is richer; use it when the entity is the focus of the task
(the function you are about to change, the type at the center of a bug).

## Workflow 2: Trace a call chain

Use when you need to understand who calls a function, what it calls, or the
full call path between two points.

```
# Forward (what this function calls):
code_context(repo="szymonrychu/<repo>", rel="callees", id="<function_id>", depth=3)
-> Returns the tree of functions/methods this entity calls, up to depth 3.
   Increase depth if the chain is deep; start at 2-3 to avoid noise.

# Reverse (who calls this function):
code_context(repo="szymonrychu/<repo>", rel="callers", id="<function_id>", depth=2)
-> Returns all callers up to depth 2. Useful for impact analysis before
   changing a function's signature or behavior.

# Shortest path between two known entities:
code_graph(
  repo="szymonrychu/<repo>",
  op="path",
  from="<entity_a_id>",
  to="<entity_b_id>"
)
-> Returns the shortest connection path through any relation type.
   If no path is found, check code_context(rel="cross_repo") in case the
   entities connect through another repo.
```

Decision: use `code_context(rel="callers"|"callees")` for unbounded fan-out;
use `code_graph(op="path")` when you have a specific source and target and
want the shortest connection.

## Workflow 3: Map dependencies

Use when assessing the impact of a change, or understanding what a component
imports from and what imports it.

```
# What does this entity import/depend on?
code_context(repo="szymonrychu/<repo>", rel="dependencies", id="<entity_id>", depth=2)
-> Forward imports and depends_on edges. Shows what this entity needs.

# What depends on this entity?
code_context(repo="szymonrychu/<repo>", rel="dependents", id="<entity_id>", depth=2)
-> Reverse imports. Shows blast radius: everything that will be affected
   by a change to this entity.

# What does a file's package import?
code_context(repo="szymonrychu/<repo>", rel="file_imports", id="<file_entity_id>")
-> All imports out of that file's package. Get the file entity's id from
   code_search first. Use for a broad package-level dependency picture when
   you don't have a specific entity to start from.

# Infrastructure resources (Terraform / Helm):
code_graph(repo="szymonrychu/<repo>", op="resource_graph", id="<resource_id>")
-> Dependency subgraph for that resource. Use for infra repos.
```

## Workflow 4: Find coupling hotspots and community structure

Use when a brainstorm or health-check task asks "where is the system tightly
coupled?" or "what are the major subsystems?".

```
1. code_graph(repo="szymonrychu/<repo>", op="communities")
   -> Returns community list: id (int), label, size, cohesion score.
   -> Sort by cohesion desc: highest cohesion = tightest internal coupling.
   -> A community with many members and low cohesion = poorly bounded module.

2. code_graph(repo="szymonrychu/<repo>", op="communities", community=<int>)
   -> Returns the member entities of that community.
   -> Use to name and describe the subsystem.

3. code_graph(repo="szymonrychu/<repo>", op="bridges", limit=10)
   -> Returns the top bridge entities by betweenness (entities on many
      shortest paths between communities).
   -> These are high-risk change targets and architectural seams.
      A bridge entity with low test coverage = a liability.
```

Interpret cohesion: there is no universal threshold, but relative comparison
within the same repo is meaningful. Flag communities with cohesion noticeably
below the median.

## Workflow 5: Traverse a specific relation type

Use when you know the edge type (calls, imports, depends_on, etc.) and want
to walk it directionally.

```
code_context(
  repo="szymonrychu/<repo>",
  rel="neighbors",
  id="<entity_id>",
  relation="<relation_type>",  # e.g. "calls", "imports", "depends_on"
  direction="out",             # "out" = follow the edge forward; "in" = reverse
  depth=2
)
-> Returns entities reachable from id along that relation, to depth.
```

Common relation types (use exact names from edge list in
`code_context(rel="entity")` output): `calls`, `imports`, `depends_on`,
`implements`, `references`, `conceptually_related_to`,
`semantically_similar_to`.

## Workflow 6: Cross-repo symbol links

Use when an entity in one repo consumes or provides something from another.

```
code_context(repo="szymonrychu/<repo>", rel="cross_repo", id="<entity_id>")
-> Returns two lists:
     consumers: other-repo entities that import/use what this entity provides
     providers: other-repo entities that this entity imports/uses
-> Use to understand API surface area and multi-repo coupling before refactoring.
```

If a `code_graph(op="path")` search finds no path within one repo, check
`rel="cross_repo"` first before concluding two entities are unrelated.

## Workflow 7: Semantic and conceptual neighbors

Use when you need to find things that are conceptually related (not
structurally connected by calls or imports).

```
code_context(
  repo="szymonrychu/<repo>",
  rel="related",
  id="<entity_id>"
)
-> Returns entities linked by semantic edges (conceptually_related_to,
   semantically_similar_to, rationale_for, and similar relation types).

code_graph(repo="szymonrychu/<repo>", op="hyperedges", id="<hyperedge_id>")
-> Fetches one specific hyperedge and its members. Omit id for the full list.
```

Semantic edges are lower-confidence by nature; there is no confidence filter
on the tool, so weigh a `related` result accordingly rather than trusting it
at the same strength as a structural (`callers`/`callees`/`dependencies`) edge.

## Workflow 8: Graph quality check

Use when you suspect the code graph is stale, poorly ingested, or has
systematic ingestion errors.

```
1. code_graph(repo="szymonrychu/<repo>", op="stats")
   -> Check import_cycles and isolated entity count.
   -> Many isolated entities = ingestion gaps or missing edge extraction.

2. code_graph(repo="szymonrychu/<repo>", op="ambiguous", limit=20)
   -> Returns edges with AMBIGUOUS tier or low confidence, ascending by score.
   -> These are the weakest inferences in the graph. If most of the graph's
      edges appear here, the graph should be re-ingested.
```

## Decision table: which tool for which question

| Question | Tool |
|----------|------|
| "Where is the core logic?" | `code_graph(op="important")` |
| "What are the major subsystems?" | `code_graph(op="communities")` |
| "What is entity X?" | `code_context(rel="entity")` or `code_explain` |
| "Find something named X" | `code_search(q="X")` |
| "What does X call?" | `code_context(rel="callees")` |
| "Who calls X?" | `code_context(rel="callers")` |
| "What does X import?" | `code_context(rel="dependencies")` or `code_context(rel="file_imports")` |
| "What will break if I change X?" | `code_context(rel="dependents")` |
| "How does A connect to B?" | `code_graph(op="path")` |
| "What are the coupling hotspots?" | `code_graph(op="bridges")` + `code_graph(op="communities")` |
| "Does X affect other repos?" | `code_context(rel="cross_repo")` |
| "What is X conceptually related to?" | `code_context(rel="related")` |
| "Is the graph healthy?" | `code_graph(op="stats")` + `code_graph(op="ambiguous")` |
| "Terraform dependency of resource X?" | `code_graph(op="resource_graph")` |

## Worked example: tracing a bug in tatara-cli

Task: "Understand how the MCP server decides which tools to expose."

```
1. code_graph(repo="szymonrychu/tatara-cli", op="stats")
   -> Get lay of the land. Note entity count and types.

2. code_search(repo="szymonrychu/tatara-cli", q="resolveProfile", type="function")
   -> Find the resolveProfile function entity. Note its id.

3. code_explain(repo="szymonrychu/tatara-cli", id="resolveProfile")
   -> Read: what resolveProfile does, its callers, what it calls.

4. code_context(repo="szymonrychu/tatara-cli", rel="callers", id="resolveProfile", depth=2)
   -> See what drives it: the MCP server registration path.

5. code_context(repo="szymonrychu/tatara-cli", rel="callees", id="resolveProfile", depth=2)
   -> See what it calls: profile lookup, allow-map construction.

6. code_graph(
     repo="szymonrychu/tatara-cli",
     op="path",
     from="<server_start_entity>",
     to="resolveProfile"
   )
   -> Confirms the call path from startup to profile resolution.
```

At this point you have a complete structural picture without reading any files.
Open files only for the specific functions you need to read or change.

## Anti-patterns

- Do NOT start with `code_context(rel="entity")` when you do not know the
  exact entity id. Use `code_search` first to find the id.
- Do NOT call `code_context(rel="callees", depth=10)` on a central entity.
  Start at 2-3; deep traversal on high-degree nodes produces enormous noisy
  results.
- Do NOT skip orientation (`code_graph(op="stats")` + `code_graph(op="important")`)
  before exploring. Without it you have no map and will wander.
- Do NOT assume `code_graph(op="path")` finds the only path. It returns the
  SHORTEST path along any relation. There may be other paths; check
  `code_context(rel="neighbors")` if you need completeness.
- Do NOT use `code_context(rel="related")` as a substitute for
  `code_context(rel="callers"|"callees")`. Semantic edges are inferred, not
  structural. Use structural tools for call tracing; use `rel="related"` for
  conceptual exploration only.
- Do NOT infer coupling from community membership alone. A large community
  with low cohesion may be a catch-all grouping, not a real tight cluster.
  Confirm with `code_graph(op="bridges")` and `code_context(rel="neighbors")`.
