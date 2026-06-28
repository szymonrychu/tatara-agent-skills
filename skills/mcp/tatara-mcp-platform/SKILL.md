---
name: tatara-mcp-platform
description: >
  The four always-on baseline MCP tools (report_internal_issue, project_get,
  repo_list, task_get) present in every agent profile regardless of task kind.
  Use report_internal_issue immediately whenever a tool call fails
  systematically, a directive contradicts itself, or the workspace, memory, or
  graph state is inconsistent; use project_get, repo_list, and task_get to
  orient before any planning or investigation work.
profiles: ["*"]
---

# tatara-mcp-platform

These four tools are in the `alwaysOn` set in `tatara-cli/internal/mcp/profiles.go`.
They are unioned into the allowed set of every profile at server startup and
cannot be gated out by any `TATARA_TOOL_PROFILE` value, including unknown or
empty ones. If you can call any MCP tool at all, you can call these four.

## Tool index

| Tool | Args (required*) | Env fallback | Purpose |
|------|-----------------|--------------|---------|
| `report_internal_issue` | `category`* `description`* `severity` `offending_tool` `resource_id` | - | Signal a platform health problem; emits structured log + metric |
| `project_get` | `project` | `TATARA_PROJECT` | Fetch the full Project CR for the current project |
| `repo_list` | `project` | `TATARA_PROJECT` | List all Repository CRs enrolled in the project |
| `task_get` | `task` | `TATARA_TASK` | Fetch the current Task CR |

`project_get`, `repo_list`, and `task_get` fall back to `TATARA_PROJECT` /
`TATARA_TASK` environment variables when the matching arg is omitted.
Omit them; the operator injects the correct values into every agent pod.

`report_internal_issue` is a pure-local handler (no HTTP round-trip). It
runs in the `tatara mcp` process, emits a structured `slog.Error` or
`slog.Warn` line, and increments the `tatara_mcp_internal_issue_total{category,
severity}` Prometheus counter. It does NOT open a GitHub issue.

---

## Procedure 1: Orient at task start

Run this sequence before any planning, investigation, or brainstorm work.

```
1. task_get()
   -> Read spec.kind, spec.repo, spec.payload, status.phase, status.workItems.
      This is your task brief. Do not proceed without reading it.

2. project_get()
   -> Read spec.scm, spec.maxOpenProposals, status.workItems (project-level ledger).
      Tells you the SCM host (GitHub/GitLab), proposal cap, and in-flight work.

3. repo_list()
   -> Returns all enrolled Repository CRs. Each has spec.scm.owner + spec.scm.repo
      (the slug) and spec.scm.branch (default branch).
      Use this to build the complete list of repos in scope before touching code.
```

All three calls omit the `task`/`project` arg. The operator pod sets
`TATARA_TASK` and `TATARA_PROJECT` at launch; the CLI resolves them
from the environment.

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

A tool call to `query` returns HTTP 502 three times in a row:

```
report_internal_issue(
  category       = "tool_error",
  severity       = "error",
  description    = "tatara-memory query endpoint returned 502 on three consecutive calls with mode=hybrid. Memory retrieval is unavailable.",
  offending_tool = "query",
  resource_id    = "szymonrychu/tatara-cli"
)
```

After calling `report_internal_issue`, do NOT keep retrying blindly.
Either adapt (use an alternative tool or approach) or call
`decline_implementation` / `skip_research` with the reason.

---

## Procedure 3: Refresh task or project state mid-task

Call `task_get()` again whenever you suspect the Task's status has changed
(e.g., after a long code generation pass, before calling a terminal tool like
`change_summary` or `decline_implementation`).

```
task_get()  -> check status.phase, status.workItems for any operator updates
```

Call `project_get()` again if you need to recheck the proposal cap before
calling `propose_issue` multiple times.

---

## Anti-patterns

- Do NOT omit `task_get` at task start. The task brief (spec.payload, spec.kind,
  spec.repo) is the authoritative source of your assignment; do not infer it
  from memory or context alone.
- Do NOT call `report_internal_issue` for transient failures (a single timeout,
  a single 429). Report only when the failure is systematic or blocks the task.
- Do NOT rely on `report_internal_issue` to create a GitHub issue or notify a
  human in real time. It is a telemetry signal only (log + metric).
- Do NOT construct the `project` or `task` arg from memory or guesses. Omit
  them; the env fallback is authoritative.
- Do NOT treat an auth error (401/403) as a transient retry candidate. Report
  it as category=`auth` and stop; retrying with bad credentials floods the log.
