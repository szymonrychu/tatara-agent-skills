# Content Types

Every skill in this repo is one of two content types. Choosing correctly is the most important authoring decision.

## TASK content

**Definition:** A prescriptive, step-by-step, actionable procedure. The skill DRIVES execution. The agent follows the steps rather than reasoning freely.

**Use when:**
- The work is rote and repeatable with a single correct procedure.
- Deviation from the procedure produces a wrong or inconsistent result.
- The agent should not need to invent the approach.

**Examples:**
- `tatara-implement-workflow`: fixed sequence of triage, plan, build, test, review, and writeback for an implement turn.
- `tatara-deep-research`: fixed fan-out and synthesis workflow with a required terminal action.
- `writing-plans`: structured decomposition into subtasks with required artifact.
- `test-driven-development`: red-green-refactor cycle with required coverage check.

**Formatting conventions:**
- Numbered steps in execution order.
- Hard gates (MUST / MUST NOT) called out visually (bold, all-caps, or a `<HARD-GATE>` block).
- Checklists for multi-item completion requirements.
- Clear terminal condition: what "done" looks like.

**What NOT to include in task skills:**
- Open-ended "consider whether" language (pick one path and state it).
- Optional steps that the agent must decide on mid-execution (make the choice in the skill).
- Creative latitude sections (belongs in reference content).

## REFERENCE content

**Definition:** Conventions, heuristics, and anti-patterns that run INLINE alongside the agent's own reasoning. The skill ADVISES; the agent retains creative and analytical latitude.

**Use when:**
- The goal is to set guard-rails, not to script the path.
- Over-standardizing the work would produce worse outcomes than letting the agent reason freely within constraints.
- The skill is consumed as background context, not as a procedure to follow.

**Examples:**
- `tatara-brainstorm-guardrails`: what the operator enforces, what valid output looks like, anti-patterns. The actual research strategy is the agent's.
- `tatara-triage-judgment`: decision rubric for classifying an issue on a clarify/refine turn. The
  procedural counterpart is a task skill in the same profile (never a cross-profile reference).
- `writing-skills`: style and communication heuristics, not a writing procedure.
- `using-superpowers`: when to reach for each skill, not how to execute them.

**Formatting conventions:**
- Rubrics: "When X, do Y" decision tables.
- Anti-patterns section: explicit list of common wrong moves.
- "What belongs here vs there" section: clarifies the boundary with the complementary task skill.
- Prose over bullets for explanation sections; bullets for lists of discrete items.

**What NOT to include in reference skills:**
- Step-by-step procedures (those belong in a task skill).
- Rule trees that enumerate every case (the agent handles the long tail; give heuristics for the important cases).
- Ideation scripts or brainstorming frameworks (these destroy the creative space reference content is meant to protect).
- Implementation instructions (reference skills stay at the judgment / advisory level).

## Decision guide

Ask yourself:

1. **Is there one correct procedure?** If yes: task. If the answer depends heavily on context: reference.
2. **Would a deviation from this skill produce a wrong result?** If yes: task (with hard gates). If deviation is sometimes fine: reference.
3. **Does the skill need to preserve creative latitude?** If yes: reference. If the work is rote: task.
4. **Is the skill about WHAT to do or HOW to do it?** What = reference. How (with a specific sequence) = task.

When in doubt, split: write a task skill for the procedure and a reference skill for the judgment
layer. See `tatara-incident-sre` (task) + `tatara-incident-investigation` (reference) as the
canonical example of this split: both carry `profiles: ["incident"]`, so they co-install and are
mandated together on every incident turn.

## Frontmatter `profiles:` field

The `profiles:` list controls which agent kinds receive the skill. The wrapper compares it against `TATARA_SKILL_PROFILE` (set by the operator per task kind) and skips skills that don't match.

Valid profile names: `implement`, `review`, `clarify`, `brainstorm`, `incident`,
`refine`, `documentation`. `triage`, `lifecycle`, and `selfImprove` are
retired - the operator no longer emits those kinds (their agent-facing
front-half work is absorbed into `clarify`/`implement`/`review`; the
lifecycle's CD back-half is an operator-only deploy supervisor with no
agent-facing skills at all). Do not add any of the three retired names to a
`profiles:` list.

`["*"]` (with the asterisk quoted) installs in every profile. Absent or empty field is treated as `["*"]`. When in doubt for a new shared utility skill, use `["*"]`.

Place `profiles:` as the last key in the frontmatter block, after `description:`, before the closing `---`. Example:

```yaml
---
name: my-skill
description: "What this skill does and when to use it."
profiles: ["implement", "review"]
---
```

## Frontmatter `description` field

The `description` is the trigger text. The agent reads it to decide whether to invoke the skill. Write it as:
- One sentence stating what the skill does AND when to use it.
- For task skills: include the activation trigger (e.g. "Use when starting any feature implementation").
- For reference skills: include "REFERENCE" in the description to signal it is advisory, not procedural.

The description is the most-read line in the skill. Spend time on it.
