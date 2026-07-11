---
name: tatara-mcp-code-graph
description: >
  Drive the 19 code_* code-graph MCP tools (groupCodeGraph) to orient in an
  unfamiliar codebase, trace call chains, map dependencies, find coupling
  hotspots, and explain cross-repo symbol links. Use whenever you need to
  understand code structure before reading files, trace a bug across call
  boundaries, assess impact of a change, or locate tightly-coupled subsystems.
  Available in every agent profile.
profiles: ["brainstorm", "implement", "incident", "review", "clarify"]
---

# tatara-mcp-code-graph

All 19 tools in `groupCodeGraph` are available in every agent profile. They
hit the tatara-memory backend (Target=TargetMemory) at `/code/...` and
`/code-graph/...` routes. Tool names are exact; use them verbatim.

The `repo` argument is always a slug like `szymonrychu/tatara-cli`. Every
tool requires it; it scopes results to one repository's code graph.

## Tool index

| Tool | Args (required*) | Purpose |
|------|-----------------|---------|
| `code_search` | `repo`* `q` `type` `limit` | Keyword search over entities (name + description) |
| `code_entity` | `repo`* `id`* | Single entity + its immediate edges |
| `code_neighbors` | `repo`* `id`* `relation`* `direction` `depth` `min_confidence` `tier` | Traverse one relation type from an entity |
| `code_callers` | `repo`* `id`* `depth` `min_confidence` `tier` | Who calls this function/method (reverse calls) |
| `code_callees` | `repo`* `id`* `depth` `min_confidence` `tier` | What this function/method calls (forward calls) |
| `code_dependents` | `repo`* `id`* `depth` `min_confidence` `tier` | What depends on this entity (reverse imports/references) |
| `code_dependencies` | `repo`* `id`* `depth` `min_confidence` `tier` | What this entity depends on (forward imports/references) |
| `code_file_imports` | `repo`* `path`* | Imports out of a file's package |
| `code_resource_graph` | `repo`* `id`* `depth` | Terraform/Helm dependency subgraph for a resource |
| `code_cross_repo` | `repo`* `id`* | Cross-repo symbol links: who consumes/provides what this entity provides/requires |
| `code_path` | `repo`* `from`* `to`* `relations` `max_depth` | Shortest path between two entities |
| `code_important` | `repo`* `limit` `by` | Most important entities ranked by degree or betweenness |
| `code_stats` | `repo`* | Entity/edge counts, types, tiers, isolated entities, import cycles |
| `code_ambiguous_edges` | `repo`* `limit` | Edges with low confidence or AMBIGUOUS tier (ascending by score) |
| `code_explain` | `id`* `repo`* | Full context: detail, in/out neighbors with file locations |
| `code_related` | `id`* `repo`* `relations` `min_confidence` | Semantic neighbors over conceptual/rationale/similarity edges |
| `code_hyperedges` | `repo`* `entity` `id` | N-ary hyperedges (group relations); supply `id` for one, omit for list |
| `code_communities` | `repo`* `community` | Detected communities (label, size, cohesion); supply `community` int for members |
| `code_bridges` | `repo`* `limit` | High-betweenness bridge entities connecting multiple communities |

## Orientation: first move in an unfamiliar repo

Run both before reading any files. These establish the map.

```
1. code_stats(repo="szymonrychu/<repo>")
   -> Read: total entity count, entity type breakdown (function, file, type, etc.),
      edge count, isolated entities, import cycles.
   -> If import_cycles is non-empty, note them; they indicate design debt.

2. code_important(repo="szymonrychu/<repo>", limit=20, by="degree")
   -> Returns the 20 most-connected entities by in+out edge count.
   -> Skim names: these are the load-bearing symbols. Start here when asked
      "where is the core logic?".

3. code_important(repo="szymonrychu/<repo>", limit=10, by="betweenness")
   -> Entities on the most shortest paths - architectural bottlenecks.
   -> Different from degree: a low-degree bridge can still have high betweenness.
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

2. code_entity(repo="szymonrychu/<repo>", id="<entity_id>")
   -> Returns the full entity: fields, description, and ALL immediate edges
      (in and out). Edge list shows relation types.
   -> Use the edge list to decide what to traverse next.

3. code_explain(repo="szymonrychu/<repo>", id="<entity_id>")
   -> Richer than code_entity: includes narrative detail, in-neighbor list
      with file locations, out-neighbor list with file locations.
   -> Use this when you need to understand WHY an entity exists and HOW it
      connects to the rest of the graph, not just WHAT it is.
```

`code_entity` is fast; use it for structural questions. `code_explain` is
richer; use it when the entity is the focus of the task (the function you are
about to change, the type at the center of a bug).

## Workflow 2: Trace a call chain

Use when you need to understand who calls a function, what it calls, or the
full call path between two points.

```
# Forward (what this function calls):
code_callees(repo="szymonrychu/<repo>", id="<function_id>", depth=3)
-> Returns the tree of functions/methods this entity calls, up to depth 3.
   Increase depth if the chain is deep; start at 2-3 to avoid noise.

# Reverse (who calls this function):
code_callers(repo="szymonrychu/<repo>", id="<function_id>", depth=2)
-> Returns all callers up to depth 2. Useful for impact analysis before
   changing a function's signature or behavior.

# Shortest path between two known entities:
code_path(
  repo="szymonrychu/<repo>",
  from="<entity_a_id>",
  to="<entity_b_id>",
  max_depth=6
)
-> Returns the shortest connection path through any relation type.
   Set relations="calls,imports" to restrict to specific edge types.
   If no path exists within max_depth, try increasing it or check
   code_cross_repo if entities may connect through another repo.
```

Decision: use `code_callers`/`code_callees` for unbounded fan-out; use
`code_path` when you have a specific source and target and want the shortest
connection.

## Workflow 3: Map dependencies

Use when assessing the impact of a change, or understanding what a component
imports from and what imports it.

```
# What does this entity import/depend on?
code_dependencies(repo="szymonrychu/<repo>", id="<entity_id>", depth=2)
-> Forward imports and depends_on edges. Shows what this entity needs.

# What depends on this entity?
code_dependents(repo="szymonrychu/<repo>", id="<entity_id>", depth=2)
-> Reverse imports. Shows blast radius: everything that will be affected
   by a change to this entity.

# What does a file's package import?
code_file_imports(repo="szymonrychu/<repo>", path="internal/mcp/tools.go")
-> All imports out of that file's package. Use for a broad package-level
   dependency picture when you don't have a specific entity to start from.

# Infrastructure resources (Terraform / Helm):
code_resource_graph(repo="szymonrychu/<repo>", id="<resource_id>", depth=3)
-> Dependency subgraph for that resource. Use for infra repos.
```

## Workflow 4: Find coupling hotspots and community structure

Use when a brainstorm or health-check task asks "where is the system tightly
coupled?" or "what are the major subsystems?".

```
1. code_communities(repo="szymonrychu/<repo>")
   -> Returns community list: id (int), label, size, cohesion score.
   -> Sort by cohesion desc: highest cohesion = tightest internal coupling.
   -> A community with many members and low cohesion = poorly bounded module.

2. code_communities(repo="szymonrychu/<repo>", community=<int>)
   -> Returns the member entities of that community.
   -> Use to name and describe the subsystem.

3. code_bridges(repo="szymonrychu/<repo>", limit=10)
   -> Returns the top bridge entities by betweenness (entities on many
      shortest paths between communities).
   -> These are high-risk change targets and architectural seams.
      A bridge entity with low test coverage = a liability.

4. code_important(repo="szymonrychu/<repo>", limit=15, by="betweenness")
   -> Cross-checks bridges from the analytics store. Both list entities
      that mediate coupling; bridges uses community membership context,
      important-by-betweenness uses raw path centrality.
```

Interpret cohesion: there is no universal threshold, but relative comparison
within the same repo is meaningful. Flag communities with cohesion noticeably
below the median.

## Workflow 5: Traverse a specific relation type

Use when you know the edge type (calls, imports, depends_on, etc.) and want
to walk it directionally.

```
code_neighbors(
  repo="szymonrychu/<repo>",
  id="<entity_id>",
  relation="<relation_type>",  # e.g. "calls", "imports", "depends_on"
  direction="out",             # "out" = follow the edge forward; "in" = reverse
  depth=2,
  min_confidence=0.7           # omit to include all; set to filter low-confidence
)
-> Returns entities reachable from id along that relation, to depth.
```

Common relation types (use exact names from edge list in code_entity output):
`calls`, `imports`, `depends_on`, `implements`, `references`,
`conceptually_related_to`, `semantically_similar_to`.

## Workflow 6: Cross-repo symbol links

Use when an entity in one repo consumes or provides something from another.

```
code_cross_repo(repo="szymonrychu/<repo>", id="<entity_id>")
-> Returns two lists:
     consumers: other-repo entities that import/use what this entity provides
     providers: other-repo entities that this entity imports/uses
-> Use to understand API surface area and multi-repo coupling before refactoring.
```

If a `code_path` search finds no path within one repo, check cross_repo links
first before concluding two entities are unrelated.

## Workflow 7: Semantic and conceptual neighbors

Use when you need to find things that are conceptually related (not
structurally connected by calls or imports).

```
code_related(
  repo="szymonrychu/<repo>",
  id="<entity_id>",
  relations="conceptually_related_to,rationale_for",
  min_confidence=0.6
)
-> Returns entities linked by semantic edges.

code_hyperedges(repo="szymonrychu/<repo>", entity="<entity_id>")
-> Lists n-ary group relations involving this entity (e.g. a design pattern
   grouping three entities).

code_hyperedges(repo="szymonrychu/<repo>", id="<hyperedge_id>")
-> Fetches one specific hyperedge and its members.
```

Semantic edges are lower-confidence by nature. Set `min_confidence` to 0.5-0.7
for exploratory work; raise to 0.8+ when you need only strong signals.

## Workflow 8: Graph quality check

Use when you suspect the code graph is stale, poorly ingested, or has
systematic ingestion errors.

```
1. code_stats(repo="szymonrychu/<repo>")
   -> Check import_cycles and isolated entity count.
   -> Many isolated entities = ingestion gaps or missing edge extraction.

2. code_ambiguous_edges(repo="szymonrychu/<repo>", limit=20)
   -> Returns edges with AMBIGUOUS tier or low confidence, ascending by score.
   -> These are the weakest inferences in the graph. If most of the graph's
      edges appear here, the graph should be re-ingested.
```

## Decision table: which tool for which question

| Question | Tool |
|----------|------|
| "Where is the core logic?" | `code_important(by="degree")` |
| "What are the major subsystems?" | `code_communities` |
| "What is entity X?" | `code_entity` or `code_explain` |
| "Find something named X" | `code_search(q="X")` |
| "What does X call?" | `code_callees` |
| "Who calls X?" | `code_callers` |
| "What does X import?" | `code_dependencies` or `code_file_imports` |
| "What will break if I change X?" | `code_dependents` |
| "How does A connect to B?" | `code_path` |
| "What are the coupling hotspots?" | `code_bridges` + `code_communities` |
| "Does X affect other repos?" | `code_cross_repo` |
| "What is X conceptually related to?" | `code_related` |
| "Is the graph healthy?" | `code_stats` + `code_ambiguous_edges` |
| "Terraform dependency of resource X?" | `code_resource_graph` |

## Worked example: tracing a bug in tatara-cli

Task: "Understand how the MCP server decides which tools to expose."

```
1. code_stats(repo="szymonrychu/tatara-cli")
   -> Get lay of the land. Note entity count and types.

2. code_search(repo="szymonrychu/tatara-cli", q="resolveProfile", type="function")
   -> Find the resolveProfile function entity. Note its id.

3. code_explain(repo="szymonrychu/tatara-cli", id="resolveProfile")
   -> Read: what resolveProfile does, its callers, what it calls.

4. code_callers(repo="szymonrychu/tatara-cli", id="resolveProfile", depth=2)
   -> See what drives it: the MCP server registration path.

5. code_callees(repo="szymonrychu/tatara-cli", id="resolveProfile", depth=2)
   -> See what it calls: profile lookup, allow-map construction.

6. code_path(
     repo="szymonrychu/tatara-cli",
     from="<server_start_entity>",
     to="resolveProfile",
     max_depth=5
   )
   -> Confirms the call path from startup to profile resolution.
```

At this point you have a complete structural picture without reading any files.
Open files only for the specific functions you need to read or change.

## Anti-patterns

- Do NOT start with `code_entity` when you do not know the exact entity id.
  Use `code_search` first to find the id.
- Do NOT call `code_callees` with `depth=10` on a central entity. Start at 2-3;
  deep traversal on high-degree nodes produces enormous noisy results.
- Do NOT skip orientation (`code_stats` + `code_important`) before exploring.
  Without it you have no map and will wander.
- Do NOT assume `code_path` finds the only path. It returns the SHORTEST path
  along any relation. There may be other paths; check `code_neighbors` if you
  need completeness.
- Do NOT use `code_related` as a substitute for `code_callers`/`code_callees`.
  Semantic edges are inferred, not structural. Use structural tools for call
  tracing; use `code_related` for conceptual exploration only.
- Do NOT infer coupling from community membership alone. A large community
  with low cohesion may be a catch-all grouping, not a real tight cluster.
  Confirm with `code_bridges` and `code_neighbors`.
