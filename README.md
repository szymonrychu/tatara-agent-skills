# tatara-agent-skills

Single source of truth for tatara platform agent skills. This repo replaces the baked skills that previously shipped inside the `tatara-claude-code-wrapper` image.

## What this repo is

A Claude Code plugin/marketplace bundle. When installed, it surfaces a library of skills to any Claude session working on the tatara platform. Tatara agents (running inside the autonomous loop) load skills from this repo. Human developers working in tatara repos also benefit from the shared process skills.

## How skills are consumed by tatara agents

The operator (`tatara-operator`) creates agent pods via `internal/agent/pod.go`. Each pod runs the `tatara-claude-code-wrapper` image, which bootstraps a Claude session with this plugin installed. The plugin surfaces the skills directory; the operator injects a turn-0 prompt that names which skill to invoke (e.g. `Invoke the tatara-deep-research skill...`). The agent reads the SKILL.md, decides whether to execute it as a task or use it as inline reference, and proceeds.

Per-kind tool profiles are gated by `TATARA_TOOL_PROFILE` (set in `pod.go`). The profile determines which MCP tools are available. Skills must respect the tool surface for their target kind; referencing a tool not in the profile for that kind will produce a runtime error.

### Per-kind skill routing: `profiles:`

Each SKILL.md declares a `profiles:` list in its frontmatter. The wrapper reads `TATARA_SKILL_PROFILE` (set by the operator per task kind, mirrors `TATARA_TOOL_PROFILE`) and installs only skills whose `profiles:` list contains the active profile or `"*"`.

Profile names, matching `skillProfileForKind`:

| Task kind | Profile |
|---|---|
| implement | `implement` |
| review | `review` |
| triageIssue | `triage` |
| brainstorm | `brainstorm` |
| issueLifecycle | `lifecycle` |
| incident | `incident` |
| selfImprove | `selfImprove` |
| refine | `refine` |
| healthCheck / unknown | (empty - fail-open, install all) |

`profiles: ["*"]` installs in every profile. Absent or empty `profiles:` is treated as `["*"]`. If `TATARA_SKILL_PROFILE` is empty the wrapper fails open and installs all skills. A non-empty but unknown profile is NOT fail-open: it matches only the `["*"]` (wildcard) skills, so an unrecognized profile name installs the wildcards alone. Clone failure also fails open with a WARN metric.

## Directory layout

```
.claude-plugin/
  marketplace.json    # marketplace manifest
  plugin.json         # plugin manifest (name, version, author)
skills/
  shared/             # superpowers-derived process skills, always relevant
  brainstorming/      # tatara brainstorm/healthCheck kind skills + guardrails
  investigation/      # tatara triage + health investigation skills + judgment
  review/             # code review discipline skills
  implement/          # implementation workflow skills
  mcp/                # MCP tool discipline and writeback skills
  operations/         # deploy and ops skills
template/             # starter skill (copy this to begin a new skill)
docs/
  eval/               # eval scaffolding for reference skills (A/B gate fixtures)
.github/
  workflows/
    lint.yml          # SKILL.md frontmatter + JSON manifest validation
  scripts/
    validate_skills.py
```

## Skill inventory

### skills/shared/ (superpowers-derived, 15 skills)

| Skill | Type |
|---|---|
| brainstorming | task |
| writing-plans | task |
| test-driven-development | task |
| systematic-debugging | task |
| requesting-code-review | task |
| receiving-code-review | task |
| subagent-driven-development | task |
| using-git-worktrees | task |
| finishing-a-development-branch | task |
| verification-before-completion | task |
| writing-skills | reference |
| using-superpowers | reference |
| dispatching-parallel-agents | task |
| executing-plans | task |
| handoff | task |

### skills/brainstorming/ (tatara brainstorm kind, 3 skills)

| Skill | Type |
|---|---|
| tatara-deep-research | task |
| tatara-deep-architectural-research | task |
| tatara-brainstorm-guardrails | reference |

### skills/investigation/ (tatara triage + health, 3 skills)

| Skill | Type |
|---|---|
| tatara-research-followup | task |
| tatara-health-check | task |
| tatara-triage-judgment | reference |

### skills/operations/ (deploy + ops, 2 skills)

| Skill | Type |
|---|---|
| tatara-deploy-harness | task |
| tatara-pipeline-waiting | task |

## Task vs Reference content types

See `CONTENT-TYPES.md` for the full explanation and decision guide. The short version:

- **Task**: prescriptive step-by-step procedure for rote work. Drives execution.
- **Reference**: heuristics + rails that run inline alongside the agent's own reasoning. Advises, does not drive. Never a rule tree or ideation script.

Choosing correctly is the heart of this design. Reference skills exist to preserve creative space; over-standardizing brainstorming or investigation with a task script defeats the purpose.

## Contributing a new skill

1. Copy `template/SKILL.md` to `skills/<category>/<skill-name>/SKILL.md`.
2. Choose task vs reference content type (see `CONTENT-TYPES.md`).
3. Write the frontmatter: `name` (matches directory name), a strong `description` that states what AND when, and a `profiles:` list from the table above (`["*"]` for shared skills).
4. Ground every claim in real platform code: tool names from `tatara-cli/internal/mcp/profiles.go`, prompts from `tatara-operator/internal/controller/`, kind-to-profile mapping from `pod.go`.
5. Run `pre-commit run --all-files` (or `python3 .github/scripts/validate_skills.py`) to validate.
6. For reference skills: add should-trigger and should-not-trigger fixtures to `docs/eval/<skill-name>/`.
7. Open a PR; CI runs the lint gate automatically.

## Eval gate (reference skills only)

Reference skills (those that should advise without firing during open ideation) require an A/B eval fixture under `docs/eval/`. See `docs/eval/README.md` for the procedure. The gate is a should-not-fire-during-open-ideation check: the skill must not activate when an agent is mid-brainstorm and no hard rail has been tripped.
