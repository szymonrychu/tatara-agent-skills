---
name: tatara-mcp-platform
description: >
  The six always-on baseline MCP tools (task_get, task_context, task_note,
  project_get, repo_list, report_internal_issue) present in every agent
  profile regardless of task kind, plus task_list where your profile allows
  it. Use report_internal_issue immediately whenever a tool call fails
  systematically, a directive contradicts itself, or the workspace, memory,
  or graph state is inconsistent; use task_get, task_context, project_get,
  and repo_list to orient before any planning or investigation work; use
  task_note to hand context to the pod that picks up after you.
profiles: ["*"]
---

# tatara-mcp-platform

Six tools are in the `alwaysOn` set in `tatara-cli/internal/mcp/profiles.go`.
They are unioned into the allowed set of every profile at server startup and
cannot be gated out by any `TATARA_TOOL_PROFILE` value, including unknown or
empty ones. If you can call any MCP tool at all, you can call these six. A
seventh, `task_list`, is documented here too because it lives in the same
tool group, but it is gated to the `brainstorm`, `incident`, and `refine`
profiles only - see the table below.

## Tool index

| Tool | Profiles | What it does |
|---|---|---|
| `task_get` | all | Your Task: stage, agent kind, notes, issue and MR refs, stats. |
| `task_context` | all | Re-render your context bundle. `notes=all` rehydrates notes that were elided from it. `index=true` gives the project-wide Task index. |
| `task_note` | all | Append a note to your Task. **This is the platform's only agent-to-agent channel.** |
| `project_get` | all | The Project: agent model, turn budgets, the pod TTL. |
| `repo_list` | all | The Repository CRs in this project. `repo` in every other tool is one of THESE names, never an owner/repo slug. |
| `report_internal_issue` | all | Report a PLATFORM defect (a tool that errors, a contradiction in your directives, a broken workspace). Not a code bug - that is an issue. |
| `task_list` | brainstorm, incident, refine | The Task index. Broad-context kinds only. |

`project_get`, `repo_list`, and `task_get` fall back to `TATARA_PROJECT` /
`TATARA_TASK` environment variables when the matching arg is omitted.
Omit them; the operator injects the correct values into every agent pod.

`report_internal_issue` is a pure-local handler (no HTTP round-trip). It
runs in the `tatara mcp` process, emits a structured `slog.Error` or
`slog.Warn` line, and increments the `tatara_mcp_internal_issue_total{category,
severity}` Prometheus counter. It does NOT open a GitHub issue.

### `task_note` is your only voice to the next pod

There is no chat service. There is no handoff store. There is no shared
filesystem between pods. `Task.status.notes` is it, and it arrives in the next
pod's context bundle automatically - it does not have to fetch it.

- `kind=note` - an observation worth carrying forward.
- `kind=plan` - what you intend to do, written BEFORE you do it.
- `kind=handoff` - what the NEXT pod needs. Write one before you stop. Always.

There is no `agent` parameter. The operator stamps the writer from your Task's
agent kind, and it refuses the write outright rather than defaulting it. You
cannot write a note that the next pod will read as operator-authored, and that
is deliberate: a note's `source` attribute is what tells the next agent whether
it is reading trusted platform output or untrusted agent text.

Notes are capped at 50 in the CR. Past that the OLDEST spills out to memory -
your write NEVER fails for lack of room. If the `<notes>` element in your bundle
carries `elided="N"`, the full history is one call away:
`task_context(notes=all)`.

---

## Procedure 1: Orient at task start

Run this sequence before any planning, investigation, or brainstorm work.

```
1. task_get()
   -> Read spec.kind, spec.repo, status.stage, status.notes, status.issueRef,
      status.mrRefs. This is your task brief. Do not proceed without reading it.

2. project_get()
   -> Read spec.scm, spec.model, spec.turnTimeoutSeconds, spec.podTTL.
      Tells you the SCM host (GitHub/GitLab), agent model, and turn/pod budgets.

3. repo_list()
   -> Returns all enrolled Repository CRs. Each has spec.scm.owner + spec.scm.repo
      (the slug) and spec.scm.branch (default branch).
      Use this to build the complete list of repos in scope before touching code.
```

All three calls omit the `task`/`project` arg. The operator pod sets
`TATARA_TASK` and `TATARA_PROJECT` at launch; the CLI resolves them
from the environment.

If your bundle's `<notes>` element carries `elided="N"`, call
`task_context(notes=all)` before you plan - a prior pod's `kind=handoff` note
may be sitting past the elision cutoff.

If your profile carries `task_list` (`brainstorm`, `incident`, `refine`), use
`task_context(index=true)` or `task_list()` to see what else is in flight in
this project before proposing or folding work that overlaps it.

---

## Procedure 2: Report a platform health problem

Call `report_internal_issue` immediately when you detect a systematic
platform problem. Do not swallow errors silently. Do not retry endlessly
before reporting.

```
report_internal_issue(
  category    = "<see decision table below>",
  description = "<what happened, what you tried, what state you observed>",
  severity    = "error",          # or "warn" for degraded-but-not-blocked
  offending_tool = "<tool name>", # if a specific MCP tool caused this
  resource_id    = "<task/repo/entity id>"  # if a specific resource is implicated
)
```

### Category decision table

| Situation | category |
|-----------|----------|
| An MCP tool call returned an unexpected error (not a transient network blip) | `tool_error` |
| A skill, directive, or operator prompt contradicts itself or another rule | `directive_contradiction` |
| The workspace (git repo, file system, build tool) is in a broken state you cannot recover | `workspace_broken` |
| The memory graph returns stale, contradictory, or missing data that blocks your work | `memory_inconsistent` |
| The code graph (`code_*` tools) returns stale, contradictory, or structurally broken data | `graph_inconsistent` |
| An MCP call fails with 401/403, a token is missing, or OIDC identity is wrong | `auth` |
| None of the above | `other` |

### Severity

Use `error` (the default) when the problem blocks task completion.
Use `warn` when the problem is notable but you can proceed.
`severity` defaults to `error` if omitted.

### Worked example

A tool call to `memory_query` returns HTTP 502 three times in a row:

```
report_internal_issue(
  category       = "tool_error",
  severity       = "error",
  description    = "tatara-memory query endpoint returned 502 on three consecutive calls with mode=hybrid. Memory retrieval is unavailable.",
  offending_tool = "memory_query",
  resource_id    = "szymonrychu/tatara-cli"
)
```

After calling `report_internal_issue`, do NOT keep retrying blindly.
Either adapt (use an alternative tool or approach), or write a
`task_note(kind=handoff)` and call `submit_outcome` with the shape your
profile owns (see `tatara-mcp-outcome`) - most profiles have a decline or
skip path for exactly this situation.

---

## Procedure 3: Refresh task or project state mid-task

Call `task_get()` again whenever you suspect the Task's status has changed
(e.g., after a long code generation pass, before calling `submit_outcome`).

```
task_get()  -> check status.stage, status.notes for any operator updates
```

Call `task_context()` again if a note you wrote earlier this turn should now
be visible in your own bundle, or if you need the freshest render before your
final `task_note(kind=handoff)`.

Call `project_get()` again if you need to recheck the proposal cap
(`spec.maxOpenProposals`) before including more than one proposal in a
`submit_outcome(action="propose", ...)` call.

---

## Anti-patterns

- Do NOT omit `task_get` at task start. The task brief (`spec.kind`, `spec.repo`)
  is the authoritative source of your assignment; do not infer it
  from memory or context alone.
- Do NOT call `report_internal_issue` for transient failures (a single timeout,
  a single 429). Report only when the failure is systematic or blocks the task.
- Do NOT rely on `report_internal_issue` to create a GitHub issue or notify a
  human in real time. It is a telemetry signal only (log + metric).
- Do NOT construct the `project` or `task` arg from memory or guesses. Omit
  them; the env fallback is authoritative.
- Do NOT treat an auth error (401/403) as a transient retry candidate. Report
  it as category=`auth` and stop; retrying with bad credentials floods the log.
- Do NOT stop a turn without a `task_note(kind=handoff)`. There is no other
  mechanism that carries context to the next pod.
- Do NOT pass an `agent` argument to `task_note`. There is none; the operator
  stamps the writer.
