---
name: tatara-research-followup
description: Use when continuing an existing discovery/research issue conversation on an implement turn, before or during the approval gate. Read the issue thread and task context, research the gaps with the tatara-memory graph and on-disk code, post substantive design comments with issue_write, refine the proposal into a concrete design, and push toward human approval - never self-approving. Idle quietly when there is nothing new to add.
profiles: ["implement"]
---

# tatara research follow-up

Keep a discovery-phase issue conversation alive and move it toward an
approvable design. All input and output go through the `tatara` MCP
server. You never use git or gh.

## Hard constraints

- NEVER self-approve. Approval is a maintainer's comment on the issue. YOU judge
  whether that comment gives the go-ahead - there is no wordlist - and your
  `submit_outcome(action="approved")` only REPORTS your reading of it, with
  the comment CITED in `approval_citations` (`{id, quote}`, alongside
  `approving_maintainer` and `plan_note_id`; see `tatara-mcp-outcome` and
  `tatara-implement-gate`). The operator then re-reads that exact comment and
  verifies WHO wrote it and that your quote really occurs in it - it does NOT
  check that you cited the newest comment, so judging the later maintainer
  comments is your job, not its: a withdrawal ("actually hold off") kills the
  approval and means `discuss`, while a benign follow-up ("thanks - ping me when
  the PR is up") leaves it standing and you should still cite it. So end this
  turn with `submit_outcome(action="discuss", reason=...)`
  unless a maintainer has actually posted something you can honestly read, and
  quote, as approval, and nothing later in the thread takes it back. Reporting an
  approval you cannot cite does not buy you a head start either: until the gate
  returns `granted:true`, `mr_write(action="open")` is refused, so there is
  nothing for the code to land in.
- Silence over noise - HARD RULE. When no human has replied since the
  last bot message, post NOTHING and submit `action="discuss"`
  immediately (a silent hold). Do not re-post a comment that only
  re-requests approval or restates prior analysis. The operator enforces the same
  invariant structurally: bot events are never enqueued, so your own comment can
  never wake your own Task. **This rule matters MORE now that your pod stays
  alive across turns, not less: an agent that is woken for every event and posts
  on every wake is exactly how a thread becomes a forty-comment loop nobody
  reads.**
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
   or to put it on a line of its own. A later turn - yours, on the same live pod -
   reads whatever they write and judges it. Do not approve it yourself; you
   cannot.

   If this Task owns SEVERAL Issues, every live one a human has engaged with
   needs its own approval comment. Say so, and name the `<repo>#<number>` that is
   still missing one.

5. **Idle discipline.** Has a human posted since the last bot comment? If NO -
   go straight to step 6 without calling `issue_write`. The silence-over-noise
   hard rule applies here.

6. **Close the turn.** `submit_outcome(action="discuss", reason=...)` holds the
   conversation open; the next human comment reaches you as a new turn, on the
   same pod, with your notes intact. Use `action="rejected"` ONLY if the idea is
   clearly dead AND a human concurred in the thread. Use `action="approved"` only
   when every live Issue a human has commented on carries a maintainer comment
   you read as a go-ahead, with nothing later in the thread withdrawing it - say
   WHO and WHY in your `reason`, set `approving_maintainer` to that comment's
   author and `plan_note_id` to the id of the `task_note(kind="plan")` they
   approved, and carry one `approval_citations` entry per such issue (a live
   issue no human ever commented on needs none, and holding the Task for one you
   must not invent stalls it forever), its `id` copied from that comment's
   `external_id` attribute in your bundle and its `quote` a verbatim substring of
   its body. Read what comes back: `granted:false` is a normal answer, not an
   error - post its `reason` in the thread and keep talking.

   You MUST submit an outcome. A turn that ends without one ages the Task out at
   `no-outcome` and the work is lost. Write a
   `task_note(kind="handoff", body=...)` first (see `handoff`) - the design state
   you carry is otherwise gone when your pod stops, and a warm pod is not a
   guaranteed one.

## Anti-patterns

- Reporting `action="approved"` with no cited maintainer comment, or with a
  quote you paraphrased instead of copied.
- Telling the thread that a go-ahead must use particular words, or be posted on a
  line of its own. Neither is true.
- Re-posting a comment that only re-requests approval or restates prior
  analysis when no human has replied. This is a HARD violation of the
  silence-over-noise rule, and a live pod woken repeatedly is the shape that
  makes it easy.
- Posting one giant comment instead of focused, answerable ones.
- Commenting with no new research when the thread is waiting on the human.
- Looking for a label to apply, or a status to set. `issue_write` has neither
  parameter, on purpose.
- Making code changes or opening MRs before the gate returned `granted: true`.
  This skill covers the research and conversation half of an implement turn;
  `tatara-implement-workflow` covers what happens after the gate opens.
