---
name: tatara-mcp-memory
description: >
  Drive the 13 tatara-memory MCP tools (groupMemory) to read, write, and
  traverse the platform knowledge graph. Use whenever you need to recall
  prior decisions, persist findings, ingest bulk content, inspect entities,
  or manage edges. Available in every agent profile.
profiles: ["*"]
---

# tatara-mcp-memory

All 13 tools in `groupMemory` are available in every agent profile. They
hit the tatara-memory backend (Target=TargetMemory). Tool names are exact;
use them verbatim.

## Tool index

| Tool | Args (required*) | Purpose |
|------|-----------------|---------|
| `query` | `mode`* `text`* `top_k` | Retrieve matching memory references |
| `describe` | `mode`* `text`* `top_k` | Generative answer + source paths |
| `search_entities` | `q` | Find entities by keyword |
| `get_entity` | `id`* | Fetch one entity by name |
| `patch_entity` | `id`* `patch`* | Partial-update an entity |
| `list_edges` | - | Enumerate all knowledge-graph edges |
| `create_edge` | `from_entity`* `to_entity`* `relation`* `properties` | Add an edge |
| `delete_edge` | `id`* | Remove an edge (opaque ID from `list_edges`) |
| `create_memory` | `text`* `metadata` | Insert one memory; returns `track_id` |
| `get_memory` | `id`* | Fetch one memory by `track_id` |
| `delete_memory` | `id`* | Delete one memory by `track_id` |
| `bulk_create_memories` | `items`* `repo` `reconcile_files` | Batch ingest (async); returns job ID |
| `get_ingest_job` | `id`* | Poll a bulk ingest job until done |

## Query mode decision table

Choose `mode` for `query` and `describe` based on what you need:

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
1. query(mode="hybrid", text="<topic or decision>")
   -> Returns a list of memory references. Scan the summaries.

2. If a reference looks relevant, get_memory(id=<track_id>)
   -> Returns the full memory text.

3. If you need a synthesized answer rather than raw references:
   describe(mode="hybrid", text="<topic or decision>")
   -> Returns a generative answer plus source paths.
```

Prefer `query` when you want to browse; prefer `describe` when you want a
single coherent answer to a specific question.

## Workflow 2: Find and inspect entities

Use when you know an entity name or keyword (a system, concept, incident, or
decision that the platform has tracked).

```
1. search_entities(q="<keyword>")
   -> Returns matching entity stubs with names.

2. get_entity(id=<entity_name>)
   -> Returns the entity's fields, description, and attached edges.

3. list_edges()
   -> Returns all edges. Filter client-side by from_entity/to_entity
      matching the entity you care about.
```

Do not call `list_edges` to discover entity names; use `search_entities`
first. `list_edges` is for navigating the graph structure after you know
the entities involved.

## Workflow 3: Persist a single finding

Use when you have one discrete piece of information (a decision rationale,
an incident root cause, a design constraint) to record.

```
1. create_memory(
     text="<full text of the finding, in natural language>",
     metadata={
       "source": "<file or url>",
       "kind":   "<decision|incident|constraint|finding>"
     }
   )
   -> Returns {"track_id": "<id>"}. Record the track_id if you need to
      retrieve or delete this memory later.
```

`metadata` values must all be strings. Include `kind` to help future
queries filter by category.

## Workflow 4: Bulk ingest (async)

Use when you have multiple memories to persist, or when ingesting a full
repository snapshot with reconciliation.

```
1. bulk_create_memories(
     items=[
       {"text": "...", "idempotency_key": "<stable-key>"},
       {"text": "...", "idempotency_key": "<stable-key>"},
       ...
     ],
     repo="szymonrychu/<repo>",   # omit if not repo-scoped
     reconcile_files=true         # omit unless you want stale entries pruned
   )
   -> Returns {"id": "<job_id>"}

2. POLL: get_ingest_job(id=<job_id>)
   -> Check the "status" field:
        "pending"    - not started yet; wait and retry
        "processing" - in progress; wait and retry
        "completed"  - done
        "failed"     - permanent failure; inspect "error" field

   Poll every 2-5 seconds. Stop when status is "completed" or "failed".
```

Supply `idempotency_key` per item (e.g. a stable file path or content hash)
to make retries safe. The server skips duplicate inserts with the same key.

Set `reconcile_files=true` only when you intend this batch to be the
COMPLETE set for the given `repo`; the server removes any indexed file from
that repo not present in this batch.

## Workflow 5: Manage edges

Use when you need to add a relationship between two entities that the
automatic ingester did not capture, or remove an incorrect one.

```
# Add:
1. search_entities(q="<source concept>")  -> confirm entity name A
2. search_entities(q="<target concept>")  -> confirm entity name B
3. create_edge(
     from_entity="<A>",
     to_entity="<B>",
     relation="<relation_type>",
     properties={"note": "..."}  # optional
   )

# Remove:
1. list_edges()  -> find the edge; capture its opaque "id" field exactly
2. delete_edge(id=<opaque_id>)
```

Never construct or parse the edge `id` field. It is opaque. Always retrieve
it from `list_edges`.

## Workflow 6: Correct an entity

Use when an entity has a stale field, wrong label, or needs a note added.

```
1. search_entities(q="<keyword>")     -> find entity name
2. get_entity(id=<name>)              -> inspect current fields
3. patch_entity(
     id=<name>,
     patch={"description": "...", "tags": ["..."]}
   )
   -> Only the fields in `patch` are updated (PATCH semantics).
```

## Decision: query vs describe vs search_entities

```
Goal                                    -> Tool
------------------------------------------------------------
"What do we know about X?"              -> query(mode="hybrid")
"Summarise the decision on X"           -> describe(mode="hybrid")
"Is there an entity called X?"          -> search_entities(q="X")
"Get the full record for entity X"      -> get_entity(id="X")
"Find anything related to X broadly"    -> describe(mode="global")
```

## Anti-patterns

- Do NOT call `list_edges` to browse entities. Use `search_entities`.
- Do NOT construct edge IDs from entity names. Always read from `list_edges`.
- Do NOT use `delete_memory` without first calling `get_memory` to confirm
  you have the right track_id.
- Do NOT skip `get_ingest_job` polling after `bulk_create_memories`. The
  ingest is async; assuming immediate completion causes silent data loss.
- Do NOT omit `idempotency_key` on items you may re-submit; duplicates
  accumulate without it.
- Do NOT set `reconcile_files=true` unless the batch covers ALL files for
  that repo; partial batches with reconcile will delete the missing entries.
