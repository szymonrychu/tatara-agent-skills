---
name: tatara-research-followup
description: Use when continuing an existing discovery/research issue conversation on a clarify turn. Read the issue thread and task context, research the gaps with the tatara-memory graph and on-disk code, post substantive design comments with issue_write, refine the proposal into a concrete design, and push toward human approval - never self-approving. Idle quietly when there is nothing new to add.
profiles: ["clarify"]
---

# tatara research follow-up

Keep a discovery-phase issue conversation alive and move it toward an
approvable design. All input and output go through the `tatara` MCP
server. You never use git or gh.

## Hard constraints

- NEVER self-approve. Approval is a maintainer's comment on the issue. YOU judge
  whether that comment gives the go-ahead - there is no wordlist - and your
  `submit_outcome(decision="implement")` only REPORTS your reading of it, with
  the comment CITED in `approval_citations` (`{id, quote}`; see
  `tatara-mcp-outcome`). The operator then re-reads that exact comment and
  verifies WHO wrote it, that it is the most recent maintainer comment, and that
  your quote really occurs in it. So end this turn with
  `submit_outcome(decision="discuss", reason=...)` unless a maintainer has
  actually posted something you can honestly read, and quote, as approval.
- Silence over noise - HARD RULE. When no human has replied since the
  last bot message, post NOTHING and submit `decision="discuss"`
  immediately (a silent hold). Do not re-post a comment that only
  re-requests approval or restates prior analysis. The operator enforces the same
  invariant structurally: bot events are never enqueued, so your own comment can
  never wake your own Task.
- One focused turn. Communication only via `tatara` MCP tools.

The `tatara` tools auto-scope to your current task and project from the pod
environment. Do NOT try to pass an environment variable as an argument
(you cannot expand it) - just omit the `task`/`project` args and the tool
fills them in. `repo_list` gives you the Repository CR names the `code_*` and
`scm_read` tools want as `repo=`.

## Workflow

Create a TodoWrite item per numbered step.

1. **Load context.** Your bundle already contains every Issue this Task owns -
   title, body, and the full comment thread - plus every prior note. Read it.
   Extract: open questions, maintainer asks, unresolved design decisions, and
   whether a human has engaged. If the `<notes>` element reports a nonzero
   `elided` count, pull the rest with `task_context(notes="all")`.

2. **Research the gaps.** Use the memory tools (`memory_query`,
   `memory_describe`) and the code-graph tools (`code_search`, `code_explain`,
   `code_context(rel="related"|"cross_repo"|"callers"|...)`, passing
   `repo=<Repository CR name>`) plus the on-disk code to answer the specific
   questions raised and to deepen any thin part of the proposal. Use the graph for
   cross-repo facts. If those tools return `MEMORY_DEGRADED`, research from the
   on-disk repos instead, report it ONCE, and say in your comment which
   cross-repo facts you could not confirm - do not stall the turn (see
   `tatara-mcp-memory`).

3. **Respond in-thread** with `issue_write(action="comment", repo=..., number=...,
   body=...)`. Post focused comments, not one wall of text:
   - Answer each maintainer question with evidence (`file:line`, graph findings).
   - Refine the proposal into a concrete design: architecture, components, data
     flow, error handling, testing, plus an implementation outline.
   - Surface the remaining decisions for the maintainer.

   `issue_write(action="comment")` is a DEFERRED write: the call persists the
   intent and a reconciler posts it. You get nothing back to read, and
   `scm_read(kind="comments")` will not show it back to you this turn. Do not
   look for it.

4. **Drive to approval.** When the design is converged AND a human has engaged,
   post a short summary of the agreed design and ask a maintainer to reply
   saying whether to go ahead. Ask in plain language: there is no wordlist and no
   required form of words, so do NOT instruct the thread to write a magic phrase
   or to put it on a line of its own. A later clarify turn reads whatever they
   write and judges it. Do not approve it yourself; you cannot.

   If this Task owns SEVERAL Issues, every live one needs its own approval
   comment. Say so, and name the `<repo>#<number>` that is still missing one.

5. **Idle discipline.** Has a human posted since the last bot comment? If NO -
   go straight to step 6 without calling `issue_write`. The silence-over-noise
   hard rule applies here.

6. **Close the turn.** `submit_outcome(decision="discuss", reason=...)` holds the
   Task at `awaiting-human`; the next human comment un-parks it and a fresh
   clarify pod picks it up. Use `decision="close"` ONLY if the idea is clearly
   dead AND a human concurred in the thread. Use `decision="implement"` only when
   every live Issue carries a maintainer comment you read as a go-ahead - say WHO
   and WHY in your `reason`, and carry one `approval_citations` entry per issue,
   its `id` copied from that comment's `external_id` attribute in your bundle and
   its `quote` a verbatim substring of its body.

   You MUST submit an outcome. A turn that ends without one ages the Task out at
   `stageReason=no-outcome` and the work is lost. Write a
   `task_note(kind="handoff", body=...)` first (see `handoff`) - the design state
   you carry is otherwise gone when your pod stops.

## Anti-patterns

- Reporting `decision="implement"` with no cited maintainer comment, or with a
  quote you paraphrased instead of copied.
- Telling the thread that a go-ahead must use particular words, or be posted on a
  line of its own. Neither is true.
- Re-posting a comment that only re-requests approval or restates prior
  analysis when no human has replied. This is a HARD violation of the
  silence-over-noise rule.
- Posting one giant comment instead of focused, answerable ones.
- Commenting with no new research when the thread is waiting on the human.
- Looking for a label to apply, or a status to set. `issue_write` has neither
  parameter, on purpose.
- Making code changes or opening MRs in this turn.
