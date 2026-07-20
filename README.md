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
| clarify | `clarify` |
| brainstorm | `brainstorm` |
| incident | `incident` |
| refine | `refine` |
| documentation | `documentation` |
| unknown | (empty - fail-open, install all) |

`triageIssue`, `issueLifecycle`, `selfImprove`, and `healthCheck` are retired
kinds; the operator no longer emits them (stored terminal Task CRs of those
kinds may still exist and are read-only history, but no new pod boots with
one of those `TATARA_SKILL_PROFILE` values).

`profiles: ["*"]` installs in every profile. Absent or empty `profiles:` is treated as `["*"]`. If `TATARA_SKILL_PROFILE` is empty the wrapper fails open and installs all skills. A non-empty but unknown profile is NOT fail-open: it matches only the `["*"]` (wildcard) skills, so an unrecognized profile name installs the wildcards alone. Clone failure also fails open with a WARN metric.

## Directory layout

```
.claude-plugin/
  marketplace.json    # marketplace manifest
  plugin.json         # plugin manifest (name, version, author)
.claude/
  agents/             # typed subagent definitions (explorer/tester/builder/architect)
skills/
  shared/             # superpowers-derived process skills, always relevant
  brainstorming/      # tatara brainstorm kind skills + guardrails
  clarify/            # tatara clarify kind conversation harness + judgment
  investigation/      # tatara incident kind SRE workflow + evidence judgment, refine kind backlog groomer, clarify kind research follow-up
  review/             # code review discipline skills
  implement/          # implementation workflow skills
  mcp/                # MCP tool discipline and writeback skills
  operations/         # shared pipeline-waiting mechanic
  documentation/      # scheduled documentation agent skill
template/             # starter skill (copy this to begin a new skill)
docs/
  eval/               # eval scaffolding for reference skills (A/B gate fixtures)
.github/
  workflows/
    lint.yml          # SKILL.md frontmatter + JSON manifest validation
  scripts/
    validate_skills.py
    validate_profiles.py
```

## Typed subagents (`.claude/agents/`)

| Agent | Model | Effort | Role |
|---|---|---|---|
| explorer | haiku | low | read-only code/config location |
| tester | haiku | low | test writing/running for a decided spec |
| builder | sonnet | medium | mechanical 1-3 file edits from a decided spec |
| architect | opus | high | ambiguous scope, competing approaches, cross-file/repo judgment |

`implement`'s rigid skill dispatches through these by task shape. Other
task-harness skills (brainstorm/incident/refine) dispatch `explorer` for
context-boundary (per-repo) fan-out to keep their own Opus/Sonnet surface
context lean.

## Skill inventory

**44 skills** on disk (45 `SKILL.md` files total including `template/SKILL.md`, which is the copy-me starter, has no `profiles:`, and does not count toward the skill inventory). Counted with
`find skills -name SKILL.md | sed 's|skills/\([^/]*\)/.*|\1|' | sort | uniq -c`.

### skills/shared/ (superpowers-derived + tatara-native process skills, 20 skills)

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
| tatara-mise-tooling | task |
| tatara-evidence-and-citation | reference |
| tatara-headless-decisions | task |
| tatara-platform-contract | reference |
| tatara-writeback-discipline | task |

### skills/brainstorming/ (tatara brainstorm kind, 5 skills)

| Skill | Type |
|---|---|
| tatara-council-brainstorm | task |
| tatara-deep-research | task |
| tatara-deep-architectural-research | task |
| tatara-brainstorm-guardrails | reference |
| tatara-code-quality-proposal | reference |

### skills/clarify/ (tatara clarify kind, 2 skills)

| Skill | Type |
|---|---|
| tatara-clarify-conversation | task |
| tatara-triage-judgment | reference |

### skills/investigation/ (tatara incident, refine, and clarify kinds, 4 skills)

| Skill | Type |
|---|---|
| tatara-incident-sre | task |
| tatara-incident-investigation | reference |
| tatara-backlog-groomer | task |
| tatara-research-followup | task |

### skills/implement/ (tatara implement kind, 3 skills)

| Skill | Type |
|---|---|
| tatara-implement-workflow | task |
| tatara-implement-conflict-resolution | task |
| tatara-implement-takeover | reference |

### skills/mcp/ (the tool reference, 6 skills)

| Skill | Type |
|---|---|
| tatara-mcp-platform | reference |
| tatara-mcp-outcome | reference |
| tatara-mcp-scm | reference |
| tatara-mcp-code-graph | reference |
| tatara-mcp-memory | reference |
| tatara-mcp-review | reference |

### skills/review/ (tatara review kind, 2 skills)

| Skill | Type |
|---|---|
| tatara-review-checklist | task |
| tatara-review-takeover | reference |

### skills/operations/ (shared pipeline-waiting mechanic, 1 skill)

| Skill | Type |
|---|---|
| tatara-pipeline-waiting | task |

### skills/documentation/ (scheduled documentation kind, 1 skill)

| Skill | Type |
|---|---|
| tatara-documentation-workflow | task |

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
