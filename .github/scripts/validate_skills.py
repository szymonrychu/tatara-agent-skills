#!/usr/bin/env python3
"""Validate all SKILL.md files have required YAML frontmatter (name + description)."""

import sys
import pathlib
import re

REQUIRED_FIELDS = {"name", "description"}
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """Extract key: value pairs from YAML frontmatter. Handles simple scalar values only."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    block = match.group(1)
    result = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            result[key] = value
    return result


def validate_yaml_frontmatter(path: pathlib.Path) -> list[str]:
    """Return a list of error strings for this SKILL.md, empty if valid."""
    errors = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        errors.append(f"{path}: missing YAML frontmatter (file must start with ---)")
        return errors
    fields = parse_frontmatter(text)
    for field in REQUIRED_FIELDS:
        if field not in fields:
            errors.append(f"{path}: frontmatter missing required field '{field}'")
        elif not fields[field]:
            errors.append(f"{path}: frontmatter field '{field}' is empty")
    return errors


AGENT_REQUIRED_FIELDS = {"name", "description", "model"}


def validate_agent_frontmatter(path: pathlib.Path) -> list[str]:
    """Return a list of error strings for this agent .md file, empty if valid."""
    errors = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        errors.append(f"{path}: missing YAML frontmatter (file must start with ---)")
        return errors
    fields = parse_frontmatter(text)
    for field in AGENT_REQUIRED_FIELDS:
        if field not in fields:
            errors.append(f"{path}: frontmatter missing required field '{field}'")
        elif not fields[field]:
            errors.append(f"{path}: frontmatter field '{field}' is empty")
    return errors


def main() -> int:
    root = pathlib.Path(__file__).parent.parent.parent
    skill_files = sorted(root.glob("skills/**/**/SKILL.md"))
    # also check template
    skill_files += sorted(root.glob("template/SKILL.md"))

    if not skill_files:
        print("ERROR: no SKILL.md files found", file=sys.stderr)
        return 1

    errors = []
    for path in skill_files:
        errors.extend(validate_yaml_frontmatter(path))

    agent_files = sorted(root.glob(".claude/agents/*.md"))
    if not agent_files:
        print("ERROR: no .claude/agents/*.md files found", file=sys.stderr)
        return 1
    for path in agent_files:
        errors.extend(validate_agent_frontmatter(path))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"\n{len(errors)} error(s) found in {len(skill_files)} SKILL.md "
            f"and {len(agent_files)} agent files"
        )
        return 1

    print(
        f"OK: {len(skill_files)} SKILL.md and {len(agent_files)} agent files validated"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
