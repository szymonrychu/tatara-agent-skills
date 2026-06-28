#!/usr/bin/env python3
"""Validate per-kind skill profile routing.

Mirrors the wrapper's install logic (a skill installs for profile P when its
`profiles:` list contains P or "*", and absent/empty is treated as "*"). This
guard locks each gated profile to its exact set of explicitly-tagged skills so
an accidental over-tag (or a dropped tag) fails CI.

The refine groomer is deliberately minimal: it must receive ONLY the dup/keep
judgment rubric and the SCM close/edit-issue surface, never the dev/PR/research
skills. Locking the refine set here is the load-bearing guard for that intent.
"""

import sys
import pathlib

import yaml

# Profile -> exact set of skill names that must EXPLICITLY tag the profile
# (wildcard "*" skills are excluded; they install everywhere by definition).
EXPECTED_PROFILE_SKILLS = {
    "refine": {"tatara-triage-judgment", "tatara-mcp-scm-lifecycle"},
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
