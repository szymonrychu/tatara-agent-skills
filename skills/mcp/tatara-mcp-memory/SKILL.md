---
name: tatara-mcp-memory
description: >
  Drive the 5 tatara-memory MCP tools (groupMemory) to read, write, and
  traverse the platform knowledge graph. Use whenever you need to recall
  prior decisions, persist findings, inspect entities, or manage edges.
  Available in every agent profile.
profiles: ["*"]
---

# tatara-mcp-memory

All 5 tools in `groupMemory` are available in some form in every agent
profile (`memory_query`/`memory_describe` are always on; the other three are
profile-gated per contract D.6). They hit the tatara-memory backend
(Target=TargetMemory). Tool names are exact; use them verbatim.

`get_memory`, `delete_memory`, `bulk_create_memories` and `get_ingest_job` are
GONE. Point-get and point-delete by an opaque track id had no caller in any
skill, and bulk ingest is the repo-ingester's job, not yours.

## Tool index

| Tool | Args (required*) | Purpose |
|------|-----------------|---------|
| `memory_query` | `mode`* `text`* `top_k` | Ask the knowledge graph a question in natural language. **The main entry point.** Returns matching memory references. |
| `memory_describe` | `mode`* `text`* `top_k` | Ask what the graph KNOWS about something, rather than for an answer. Use it to size a topic before you query it. Returns a generative answer plus source paths. |
| `memory_write` | `text`* `metadata` | Write a memory. Returns `track_id`. |
| `memory_entity` | `op`* (`get`\|`search`\|`patch`) `id` `q` `patch` | One entity in the graph. `op="get"` needs `id`; `op="search"` needs `q`; `op="patch"` needs `id` and `patch`. |
| `memory_edges` | `op`* (`list`\|`create`\|`delete`) `id` `from_entity` `to_entity` `relation` `properties` | Edges between entities. `op="delete"` needs `id`; `op="create"` needs `from_entity`, `to_entity`, `relation`; `op="list"` takes no required args. |

## Query mode decision table

Choose `mode` for `memory_query` and `memory_describe` based on what you need:

| Mode | When to use |
|------|-------------|
| `hybrid` | Default. Combines local and global retrieval. Use first unless you have a reason not to. |
| `local` | You have a specific entity name or narrow concept. Fast. |
| `global` | You need a cross-cutting thematic synthesis (architecture overviews, patterns, trends). |
| `naive` | Verbatim keyword search, no graph traversal. Use only when other modes miss obvious hits. |

`top_k` defaults to a backend constant when omitted; set it explicitly (e.g. `10`) only when you need to limit or expand result count.

## Workflow 1: Recall prior context before acting

Use this before starting any investigation or planning work.

```
1. memory_query(mode="hybrid", text="<topic or decision>")
   -> Returns a list of memory references. Scan the summaries.

2. If you need a synthesized answer rather than raw references:
   memory_describe(mode="hybrid", text="<topic or decision>")
   -> Returns a generative answer plus source paths.
```

Prefer `memory_query` when you want to browse; prefer `memory_describe` when
you want a single coherent answer to a specific question.

## Workflow 2: Find and inspect entities

Use when you know an entity name or keyword (a system, concept, incident, or
decision that the platform has tracked).

```
1. memory_entity(op="search", q="<keyword>")
   -> Returns matching entity stubs with names.

2. memory_entity(op="get", id=<entity_name>)
   -> Returns the entity's fields, description, and attached edges.

3. memory_edges(op="list")
   -> Returns all edges. Filter client-side by from_entity/to_entity
      matching the entity you care about.
```

Do not call `memory_edges(op="list")` to discover entity names; use
`memory_entity(op="search")` first. `memory_edges(op="list")` is for
navigating the graph structure after you know the entities involved.

## Workflow 3: Persist a single finding

Use when you have one discrete piece of information (a decision rationale,
an incident root cause, a design constraint) to record.

```
1. memory_write(
     text="<full text of the finding, in natural language>",
     metadata={
       "source": "<file or url>",
       "kind":   "<decision|incident|constraint|finding>"
     }
   )
   -> Returns {"track_id": "<id>"}.
```

`metadata` values must all be strings. Include `kind` to help future
queries filter by category.

## Workflow 4: Manage edges

Use when you need to add a relationship between two entities that the
automatic ingester did not capture, or remove an incorrect one.

```
# Add:
1. memory_entity(op="search", q="<source concept>")  -> confirm entity name A
2. memory_entity(op="search", q="<target concept>")  -> confirm entity name B
3. memory_edges(
     op="create",
     from_entity="<A>",
     to_entity="<B>",
     relation="<relation_type>",
     properties={"note": "..."}  # optional
   )

# Remove:
1. memory_edges(op="list")  -> find the edge; capture its opaque "id" field exactly
2. memory_edges(op="delete", id=<opaque_id>)
```

Never construct or parse the edge `id` field. It is opaque. Always retrieve
it from `memory_edges(op="list")`.

## Workflow 5: Correct an entity

Use when an entity has a stale field, wrong label, or needs a note added.

```
1. memory_entity(op="search", q="<keyword>")   -> find entity name
2. memory_entity(op="get", id=<name>)          -> inspect current fields
3. memory_entity(
     op="patch",
     id=<name>,
     patch={"description": "...", "tags": ["..."]}
   )
   -> Only the fields in `patch` are updated (PATCH semantics).
```

## Decision: query vs describe vs entity search

```
Goal                                    -> Tool
------------------------------------------------------------
"What do we know about X?"              -> memory_query(mode="hybrid")
"Summarise the decision on X"           -> memory_describe(mode="hybrid")
"Is there an entity called X?"          -> memory_entity(op="search", q="X")
"Get the full record for entity X"      -> memory_entity(op="get", id="X")
"Find anything related to X broadly"    -> memory_describe(mode="global")
```

## Anti-patterns

- Do NOT call `memory_edges(op="list")` to browse entities. Use
  `memory_entity(op="search")`.
- Do NOT construct edge IDs from entity names. Always read from
  `memory_edges(op="list")`.
- Do NOT try to point-get or point-delete a memory by track id. That
  capability is gone; there is no replacement. Recall through
  `memory_query`/`memory_describe` instead.
- Do NOT try to bulk-ingest content through this skill. That is the
  repo-ingester's job, not yours; use `memory_write` for one finding at a
  time.
