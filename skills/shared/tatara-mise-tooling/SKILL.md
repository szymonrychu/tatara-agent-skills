---
name: tatara-mise-tooling
description: >
  Use when you need a CLI tool, language runtime, or formatter/linter that is
  not already on PATH to do your job (analysis, build, test, implementation).
  mise is preinstalled in every agent pod; this skill covers installing tools on
  demand, persisting them to a repo, recording tooling gaps for the implementer,
  and reporting mise/egress failures.
profiles: ["*"]
---

# tatara-mise-tooling

## Environment facts

- mise is preinstalled and on PATH for the agent user (uid 10001). The `mise` binary, its shims dir, and `~/.local/bin` are all on PATH. Bash tool calls receive `mise activate` via BASH_ENV.
- mise is configured with `auto_install`, `not_found_auto_install`, and `experimental` enabled. `/workspace` is in `trusted_config_paths`, so every `.mise.toml` under `/workspace` is already trusted. You do NOT need `mise trust`.
- At pod boot the wrapper runs `mise install` in each cloned repo. Every repo's pinned tools (its `.mise.toml`) are present on session start without any action from you.

## Getting a tool not yet on PATH

**Step 1:** Try invoking the tool directly. `not_found_auto_install` will fetch it automatically if mise recognizes the command name.

**Step 2:** If auto-install does not trigger, install explicitly:

```
mise use -g <tool>@<version>
```

This installs globally for this session and puts the tool on PATH immediately. Egress to tool registries (port 443) is allowed.

## PERSISTENCE rule

| Situation | Action |
|---|---|
| Tool is for your own one-off analysis | `mise use -g` only - no file change needed |
| Tool is required to build, test, or lint the repo | Add it to that repo's root `.mise.toml` as part of your change - implementation agents only |

**MUST NOT** add a tool to `.mise.toml` unless it is genuinely required to build, test, or lint the repo. Analysis-only tools stay session-scoped.

## TOOLING-GAP rule (brainstorm / refine / incident agents)

If you installed a tool via `mise use -g` that is NOT already in the target repo's `.mise.toml`, and the work you are proposing will need that tool, fold a `## Tooling` section into the proposed issue body. List each tool: name, version, and one line explaining why. Do NOT file a separate issue for the tool. The implementation agent reading that issue will add it to `.mise.toml`.

## FAILURE rule

If mise itself fails, a tool download is blocked (egress or registry unreachable), or the toolchain is broken in a way you cannot work around:

1. Call the `report_internal_issue` MCP tool with category `workspace_broken` and severity `error`.
2. Do NOT silently give up and proceed with incomplete tooling.
3. Do NOT open a tracker issue for the platform failure.

`report_internal_issue` emits a structured error log picked up by an alert, routing the problem to an incident agent that can resolve the platform-level failure.
