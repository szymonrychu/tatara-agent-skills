#!/usr/bin/env python3
"""Validate all SKILL.md files have required YAML frontmatter (name + description),
never invoke a forge CLI, and never instruct an agent to approve or merge."""

import sys
import pathlib
import re

REQUIRED_FIELDS = {"name", "description"}
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# A COMMAND INVOCATION, not the substring. A naive `gh `/`glab ` grep matches
# "enough ", "through " (tatara-pipeline-waiting), and - fatally - the five
# "You never use git or gh directly" lines that ARE the ban (contract L.4,
# L.10; skills/brainstorming/tatara-deep-architectural-research,
# tatara-council-brainstorm, tatara-deep-research,
# skills/investigation/tatara-research-followup,
# skills/clarify/tatara-clarify-conversation). A checker that flags the
# prohibition as a violation is a checker nobody keeps.
FORGE_CLI = re.compile(
    r"\bg(?:h|lab)\s+(?:pr|run|api|issue|repo|mr|ci|auth|release|workflow|"
    r"browse|search|codespace|gist)\b"
)

# An agent pod has no forge token and no merge action (contract C.2.13, C.9).
# A skill that tells it to merge or approve is teaching it to hallucinate a
# tool call - mr_write has no merge/approve/request_changes action at all -
# or, if it reaches for raw curl with GIT_TOKEN, to bypass the platform's
# only merge gate.
#
# Two shapes are flagged:
#   1. a forge-CLI merge invocation (gh pr merge / glab mr merge)
#   2. a positive mr_write(action="merge"|"approve"|"request_changes") call,
#      EXCLUDING a pipe-enumerated list of forbidden actions (the negative
#      lookahead) - `mr_write(action="approve"|"request_changes"|"merge")`
#      appearing after "Do NOT attempt" is the ban, not a violation of it.
#   3. imperative prose: "merge/approve the/your/this PR/MR/pull request"
#
# This repo is full of LEGITIMATE uses of "merge": `git merge`, "merge
# conflict", `mergeOrder`, `mergeCursor`, "the operator merges", "you never
# merge". None of shapes 1-3 match those. Shape 3 alone would still false-
# positive on "you never merge the MR yourself" (negation precedes the
# match), so any match is additionally dropped if a negation word appears
# earlier on the same line - this is a line-level heuristic, not a full
# parse, and is intentionally narrow rather than clever.
MERGE_INSTRUCTION = re.compile(
    r"g(?:h|lab)\s+(?:pr|mr)\s+merge"
    r"|mr_write\s*\(\s*action\s*=\s*[\"']?(?:merge|approve|request_changes)(?!\s*[\"']?\s*\|)"
    r"|\b(?:merge|approve)\s+(?:the|your|this)\s+(?:PR|MR|pull request|merge request)\b",
    re.IGNORECASE,
)

NEGATION_RE = re.compile(
    r"\b(?:never|not|no|don't|cannot|can't|without)\b", re.IGNORECASE
)


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


def validate_forge_cli(path: pathlib.Path) -> list[str]:
    """Return a list of error strings for forge CLI invocations, empty if none."""
    errors = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FORGE_CLI.search(line):
            errors.append(
                f"{path}:{n}: forge CLI invocation - agent pods have no forge "
                f"token and gh/glab are banned in-cluster (contract L.10): {line.strip()}"
            )
    return errors


def validate_no_merge_instruction(path: pathlib.Path) -> list[str]:
    """Return a list of error strings for merge/approve instructions, empty if none."""
    errors = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = MERGE_INSTRUCTION.search(line)
        if match and not NEGATION_RE.search(line[: match.start()]):
            errors.append(
                f"{path}:{n}: instructs an agent to approve or merge - merge is "
                f"operator-only and the operator posts every review (contract C.5, "
                f"C.9): {line.strip()}"
            )
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
    forge_cli_errors = 0
    merge_errors = 0
    for path in skill_files:
        errors.extend(validate_yaml_frontmatter(path))
        fc = validate_forge_cli(path)
        mi = validate_no_merge_instruction(path)
        forge_cli_errors += len(fc)
        merge_errors += len(mi)
        errors.extend(fc)
        errors.extend(mi)

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
            f"and {len(agent_files)} agent files "
            f"({forge_cli_errors} forge-CLI, {merge_errors} merge-instruction)"
        )
        return 1

    print(
        f"OK: {len(skill_files)} SKILL.md and {len(agent_files)} agent files "
        f"validated (0 forge-CLI, 0 merge-instruction violations)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
