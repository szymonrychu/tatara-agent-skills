#!/usr/bin/env python3
"""Validate per-kind skill profile routing.

Mirrors the wrapper's install logic (a skill installs for profile P when its
`profiles:` list contains P or "*", and absent/empty is treated as "*"). This
guard locks EVERY gated profile (all seven: brainstorm, incident, implement,
review, refine, documentation, upgrade) to its exact set of explicitly-tagged
skills, so an accidental over-tag or a dropped tag fails CI.
`["*"]` skills are excluded from every set by definition (see the wildcard
note below) - they are not a gap in this guard, they install everywhere and
need no per-profile lock.

Each locked set protects a specific profile's tool-surface boundary
(contract D.6):

- `brainstorm`: the five brainstorming/research skills plus the code-graph
  and SCM reference skills. Must never pick up issue_write/mr_write-heavy
  skills - brainstorm files issues through submit_outcome, not issue_write.
- `incident`: the two incident skills plus code-graph, SCM, and pipeline-
  waiting references. Must never pick up brainstorm-proposal or refine
  skills.
- `implement`: the merged implement kind - it conducts the issue conversation,
  runs the approval gate, and writes the code. It gets the three implement
  skills, the gate skill, the triage-judgment rubric and the research-followup
  discipline the deleted clarify profile used to own, plus code-graph, SCM and
  pipeline-waiting references. Must never pick up `task_list`-broad-context
  skills (D.6: implement has no `task_list`).
- `review`: the review-checklist and mcp-review skills plus code-graph, SCM,
  and pipeline-waiting references. `mr_write` here is comment/reply-only
  (never approve/merge) - see `validate_no_merge_instruction` in
  `validate_skills.py` for the skill-body-level enforcement of that.
- `refine`: deliberately minimal. It must receive ONLY the dup/keep judgment
  rubric, the backlog-groomer skill, and the SCM reference (whose
  `mr_write` for refine is comment-only) - never the dev/PR/research skills
  and never `code_*` (D.6: code tools are denied to refine, a backlog
  groomer reads issues, not code).
- `documentation`: the documentation-workflow skill plus code-graph and SCM
  references. Must never pick up incident/brainstorm-only skills.
  Since 2026-08-17 it also carries `tatara-writing-voice`, the register and
  banned-list contract Phase 2 applies. `brainstorm` and `review` carry it
  too: brainstorm drafts issue prose, review enforces the register and the
  humor gate that Vale structurally cannot check.
- `upgrade`: the upgrade-workflow skill plus code-graph, SCM and pipeline-
  waiting references, and the implement conflict-resolution skill (see the
  comment on its entry below). Like implement it opens MRs, so it must never
  pick up `task_list`-broad-context skills (D.6: unit dedup goes through the
  always-on `task_context(index=true)`), and like documentation it has no
  approval gate, so it must never pick up the gate or triage-judgment skills.
"""

import sys
import pathlib

import yaml

# Profile -> exact set of skill names that must EXPLICITLY tag the profile
# (wildcard "*" skills are excluded; they install everywhere by definition,
# and the dict-builder below skips every `p == "*"` entry - a `["*"]` skill,
# e.g. `handoff` or `tatara-mcp-outcome`, can NEVER populate any set here).
EXPECTED_PROFILE_SKILLS = {
    "brainstorm": {
        "tatara-brainstorm-guardrails",
        "tatara-code-quality-proposal",
        "tatara-council-brainstorm",
        "tatara-deep-architectural-research",
        "tatara-deep-research",
        "tatara-mcp-code-graph",
        "tatara-mcp-scm",
        "tatara-writing-voice",
    },
    "incident": {
        "tatara-incident-investigation",
        "tatara-incident-sre",
        "tatara-mcp-code-graph",
        "tatara-mcp-scm",
        "tatara-pipeline-waiting",
    },
    # "clarify" is DELETED: the kind was folded into implement (#521).
    "implement": {
        "tatara-implement-conflict-resolution",
        "tatara-implement-gate",
        "tatara-implement-takeover",
        "tatara-implement-workflow",
        "tatara-mcp-code-graph",
        "tatara-mcp-scm",
        "tatara-pipeline-waiting",
        "tatara-research-followup",
        "tatara-triage-judgment",
    },
    "review": {
        "tatara-mcp-code-graph",
        "tatara-mcp-review",
        "tatara-mcp-scm",
        "tatara-pipeline-waiting",
        "tatara-review-checklist",
        "tatara-review-takeover",
        "tatara-writing-voice",
    },
    "refine": {
        "tatara-triage-judgment",
        "tatara-mcp-scm",
        "tatara-backlog-groomer",
    },
    "documentation": {
        "tatara-documentation-workflow",
        "tatara-mcp-code-graph",
        "tatara-mcp-scm",
        "tatara-writing-voice",
    },
    # The 7th profile (2026-08-13). tatara-implement-conflict-resolution is here
    # because AgentKindFor(under-implementation, upgrade) routes the post-
    # request_changes re-entry back to the UPGRADE agent, not to implement: an
    # upgrade agent meets exactly the same unmergeable-MR situation and needs the
    # same never-rebase discipline.
    "upgrade": {
        "tatara-implement-conflict-resolution",
        "tatara-mcp-code-graph",
        "tatara-mcp-scm",
        "tatara-pipeline-waiting",
        "tatara-upgrade-workflow",
    },
}


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    return yaml.safe_load(block) or {}


def main() -> int:
    root = pathlib.Path(__file__).parent.parent.parent
    skill_files = sorted(root.glob("skills/**/SKILL.md"))
    if not skill_files:
        print("ERROR: no SKILL.md files found", file=sys.stderr)
        return 1

    # Build profile -> set of skills that explicitly (non-wildcard) tag it.
    explicit: dict[str, set[str]] = {}
    for path in skill_files:
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        name = fm.get("name")
        profiles = fm.get("profiles")
        if not isinstance(profiles, list):
            continue
        for p in profiles:
            if p == "*":
                continue
            explicit.setdefault(p, set()).add(name)

    errors = []
    for profile, expected in EXPECTED_PROFILE_SKILLS.items():
        actual = explicit.get(profile, set())
        if actual != expected:
            missing = expected - actual
            extra = actual - expected
            errors.append(
                f"profile '{profile}': expected {sorted(expected)} got {sorted(actual)}"
                + (f"; missing {sorted(missing)}" if missing else "")
                + (f"; unexpected {sorted(extra)}" if extra else "")
            )

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"OK: profile routing validated for {sorted(EXPECTED_PROFILE_SKILLS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
