# Eval scaffolding for reference skills

Reference skills (those that ADVISE rather than drive) carry an additional quality gate: they must not activate during open ideation when no hard rail has been tripped. This directory holds the fixture prompts used to verify that gate.

## Why this gate exists

A reference skill loaded into every brainstorm or investigation turn will be read alongside the agent's own reasoning. If its content is a rule tree or ideation script, it suppresses creative latitude even when no constraint applies. The should-not-fire-during-open-ideation gate catches this regression.

## Directory structure

```
docs/eval/
  brainstorm-guardrails/
    should-trigger/       # prompts where the guardrails should be consulted
    should-not-trigger/   # prompts where the guardrails should stay silent
  triage-judgment/
    should-trigger/       # prompts where the rubric should be applied
    should-not-trigger/   # prompts where the rubric should stay silent
```

Each fixture file is a plain-text prompt (`.txt`) or a JSON object (`.json`) with `prompt` and optionally `expected_behavior` fields.

## The A/B gate procedure

This procedure is a manual review process. Automated execution (live A/B runs) is out of scope for Phase 1.

### Gate definition

A reference skill PASSES the gate if:
1. When given a should-trigger prompt, the agent consults the skill and applies its rubric before deciding.
2. When given a should-not-trigger prompt (open ideation, no hard rail tripped), the agent does NOT let the skill constrain or script its reasoning.

### How to run the gate (manual)

1. For each `should-not-trigger/` fixture:
   a. Run a brainstorm or investigation turn with the fixture as the opening prompt.
   b. Observe whether the reference skill content appears to constrain the agent's ideation.
   c. FAIL if the agent applies the rubric or anti-patterns list to a case not described by the skill.

2. For each `should-trigger/` fixture:
   a. Run a turn with the fixture as the opening prompt.
   b. Observe whether the agent correctly consults the rubric and applies the correct rail.
   c. FAIL if the agent ignores the skill when a hard constraint was clearly tripped.

### Writing good fixtures

**should-trigger prompts** should describe a situation where a hard invariant from the skill is relevant: a tatara-authored issue with no human comment (triage-judgment), or a brainstorm turn where the proposal count is at cap (brainstorm-guardrails).

**should-not-trigger prompts** should describe genuine open ideation: a brainstorm turn exploring a new improvement area with no constraints tripped, or a triage turn where the issue is clearly human-authored and the intent is clear. The agent should reason freely without the skill prescribing a path.

### Regression tracking

When a regression is found (a should-not-trigger prompt causes the skill to suppress ideation), fix the skill content first, then add or update the fixture that caught it. The fixture file name should describe the regression: `no-constraint-tripped-open-ideation.txt`.
