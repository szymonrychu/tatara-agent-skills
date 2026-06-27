---
name: your-skill-name
description: "One sentence: what this skill does AND when the agent should use it. This is the trigger text the agent reads to decide whether to invoke the skill. Be specific about activation conditions."
# Optional frontmatter fields:
# isolated: true     # run in a forked subagent context (for task-type skills with side effects)
# fork: true         # fork a new conversation before executing
---

<!--
BEFORE WRITING: choose a content type.

TASK content (prescriptive, step-by-step, drives execution):
- Use for rote, repeatable work with a known correct procedure.
- Examples: MCP tool discipline, writeback steps, implement workflow, review checklist, deploy procedure.
- Format: numbered steps, checklists, mandatory callouts.

REFERENCE content (heuristics + rails, runs inline alongside the agent's own reasoning):
- Use when the skill should ADVISE, not drive. The agent applies judgment; this sets the guardrails.
- Examples: brainstorm guardrails, triage judgment rubric, incident hypothesis heuristics.
- Format: rubrics, anti-patterns, "what belongs here vs there" sections.
- CRITICAL: do NOT write a rule tree or ideation script for reference skills. That destroys the creative space they are meant to protect.

Delete this comment block before committing.
-->

# Skill Title

Brief one-paragraph context: what problem this skill solves and where it fits in the platform lifecycle.

## [For TASK skills] Procedure

Steps the agent must follow in order.

1. Step one
2. Step two
3. ...

## [For REFERENCE skills] Judgment rubric

Heuristics, conditions, and anti-patterns. NOT a step-by-step script.

### When to apply X

...

### Anti-patterns

- Do not ...
- Do not ...
