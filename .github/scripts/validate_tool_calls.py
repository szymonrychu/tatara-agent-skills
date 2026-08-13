#!/usr/bin/env python3
"""Validate that skill-documented MCP tool calls match tatara-cli's canonical
tool surface (tool names, and action/kind/decision/verdict enum literals).

This closes the skill-vs-tool-surface drift hole: validate_skills.py checks
frontmatter, the forge-CLI ban, and one hand-crafted merge-instruction regex,
but nothing previously checked that a documented call like
`submit_outcome(decision="implement")` or `mr_write(action="open")` matches
the real schema tatara-cli serves (internal/mcp/outcome.go,
internal/mcp/tools_scm.go). A skill naming a renamed/removed tool or a stale
enum value reads fine to a human reviewer and fails only at agent runtime -
see tatara-agent-skills#28 and the tatara-operator incident-refire-dedupe
precedent it cites.

Source of truth: tatara-cli publishes a JSON tool-manifest (tool names + top-
level enum fields) as a release artifact via `tatara tool-manifest`
(internal/mcp/manifest.go). This script fetches the version pinned in
.github/tool-manifest-version ("latest" or a specific vX.Y.Z tag).

Scope (B1): only literal `tool_name(field="value")` tokens are checked - an
unrecognized tool name, or a field=value literal not in that tool's enum, is
an error. Bare signatures (`code_search(repo, q, type, limit)`) and elided
prose (`body=...`) have no `="literal"` shape and are silently skipped - this
is deliberately narrow to avoid the false-positive storm a full JSON-schema
conformance check would cause on illustrative examples.

An unrecognized tool name is ALSO an error (tatara-agent-skills#46) - that is
the one case this script exists to catch: a tool renamed or removed in
tatara-cli. It is scoped to calls written as markdown code (a fenced ``` ```
block, a 4-space indented code block, or an inline `backtick` span), because
every genuine documented call in the corpus is written that way already
(verified against all 45 skills/**/SKILL.md + template + .claude/agents
files: 315/315 `tool_name(field="value")`-shaped matches live in one of those
three forms, zero in bare prose). A name typed in ordinary prose - not code -
stays unchecked, so this cannot drown the build in false positives on
`run(...)`/`get(...)`-shaped English.

A manifest fetch failure (network, 404, no release published yet) FAILS THE
RUN (tatara-agent-skills#46). It used to be a soft warning so a CDN blip
wouldn't block unrelated skill PRs (pre-mortem #3) - but that made the
manifest-fetch step a silent no-op skip of the entire check, which is worse
than an occasional false-alarm-red build: a fetch that never succeeds looks
identical, in CI, to a repo with zero drift.
"""

import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

MANIFEST_REPO = "szymonrychu/tatara-cli"
MANIFEST_ASSET = "tool-manifest.json"
VERSION_PIN_FILE = ".github/tool-manifest-version"
FETCH_TIMEOUT = 10

# tool_name(field="value"["|"value2"...]) - captures the tool, the field, and
# the whole pipe-separated literal-value list. Requires at least one `="..."`
# token, so bare signatures and `body=...` prose never match.
CALL_RE = re.compile(
    r'\b([a-z][a-z_]*)\(\s*(?:[a-zA-Z_]+\s*=\s*"[^"]*"\s*,\s*)*'
    r'([a-zA-Z_]+)\s*=\s*("(?:[^"]*)"(?:\s*\|\s*"(?:[^"]*)")*)'
)
VALUE_RE = re.compile(r'"([^"]*)"')

# Mirrors validate_skills.py's own heuristic: a line like `Do NOT attempt
# mr_write(action="approve"|"request_changes"|"merge")` names values that do
# NOT exist, on purpose, as part of the prohibition itself. Any negation word
# earlier on the same line suppresses enum errors for that line.
NEGATION_RE = re.compile(
    r"\b(?:never|not|no|don't|cannot|can't|without|do not)\b", re.IGNORECASE
)

# A fenced code block: a line starting with ``` up to the next such line.
FENCE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)

# An inline code span: a backtick up to the next backtick. Real spans in this
# corpus occasionally wrap across a soft line break inside a single bullet
# (e.g. `` `task_note(kind="handoff", body="...\n     ...")` ``), so this is
# intentionally DOTALL rather than anchored to one line.
BACKTICK_RE = re.compile(r"`[^`]*?`", re.DOTALL)


def _code_mask(text: str) -> bytearray:
    """Mark every character position that is markdown CODE - a fenced ```
    block, an inline `backtick` span, or a 4-space indented code block - as
    1, everything else (plain prose) as 0.

    This is the tightening that makes an unknown tool name safe to hard-fail
    on (tatara-agent-skills#46): every genuine documented call in the real
    44-file corpus is written as one of these three forms, and ordinary
    prose - the false-positive risk the original `continue` was guarding
    against - is none of them.
    """
    mask = bytearray(len(text))

    for m in FENCE_RE.finditer(text):
        for i in range(*m.span()):
            mask[i] = 1

    for m in BACKTICK_RE.finditer(text):
        if mask[m.start()]:
            continue  # a stray backtick inside an already-fenced block
        for i in range(*m.span()):
            mask[i] = 1

    pos = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\n")
        stripped = content.lstrip(" ")
        indent = len(content) - len(stripped)
        if stripped and indent >= 4 and not mask[pos]:
            for i in range(pos, pos + len(content)):
                mask[i] = 1
        pos += len(line)

    return mask


def fetch_manifest() -> dict | None:
    root = pathlib.Path(__file__).parent.parent.parent
    version = (root / VERSION_PIN_FILE).read_text(encoding="utf-8").strip()
    tag_path = "latest/download" if version in ("", "latest") else f"download/{version}"
    url = f"https://github.com/{MANIFEST_REPO}/releases/{tag_path}/{MANIFEST_ASSET}"
    try:
        with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
    ) as exc:
        print(
            f"ERROR: could not fetch tool manifest from {url}: {exc}\n"
            "ERROR: failing closed (tatara-agent-skills#46) - a manifest that "
            "cannot be fetched must fail the run, not silently skip validation",
            file=sys.stderr,
        )
        return None
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: tool manifest at {url} is not valid JSON: {exc}", file=sys.stderr
        )
        return None


def build_index(manifest: dict) -> dict:
    """tool name -> {field name -> set(allowed values)}."""
    index = {}
    for entry in manifest.get("tools", []):
        index[entry["name"]] = {
            field: set(values) for field, values in entry.get("enums", {}).items()
        }
    return index


def validate_file(path: pathlib.Path, index: dict) -> list[str]:
    errors = []
    text = path.read_text(encoding="utf-8")
    mask = _code_mask(text)
    lines = text.splitlines()

    # byte offset each line starts at, for turning a full-text match position
    # back into a 1-based line number.
    line_starts = [0]
    for line in text.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))

    for match in CALL_RE.finditer(text):
        tool, field, value_list = match.group(1), match.group(2), match.group(3)

        if not mask[match.start()]:
            continue  # bare prose, not a documented call - not every parenthesized word is a tool call

        n = _line_number(line_starts, match.start())
        line = lines[n - 1]

        if tool not in index:
            errors.append(
                f'{path}:{n}: {tool}(...) - "{tool}" is not a known tool in the '
                f"tool manifest (renamed, removed, or never existed): {line.strip()}"
            )
            continue
        fields = index[tool]
        if field not in fields:
            continue  # not every documented field is enum-constrained; only check ones the manifest tracks
        if NEGATION_RE.search(line[: match.start() - line_starts[n - 1]]):
            continue
        allowed = fields[field]
        for value in VALUE_RE.findall(value_list):
            if value not in allowed:
                errors.append(
                    f'{path}:{n}: {tool}({field}="{value}") - "{value}" is not a valid '
                    f"{field} for {tool} (allowed: {', '.join(sorted(allowed))}): {line.strip()}"
                )
    return errors


def _line_number(line_starts: list[int], offset: int) -> int:
    """1-based line number containing byte offset `offset`, given the
    cumulative per-line start offsets `line_starts` (line_starts[0] == 0)."""
    lo, hi = 0, len(line_starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def main() -> int:
    root = pathlib.Path(__file__).parent.parent.parent
    manifest = fetch_manifest()
    if manifest is None:
        print(
            "ERROR: tool-call validation failed closed - no manifest to validate "
            "against (tatara-agent-skills#46)",
            file=sys.stderr,
        )
        return 1

    index = build_index(manifest)
    if not index:
        print(
            "WARNING: fetched tool manifest has no tools; skipping validation",
            file=sys.stderr,
        )
        return 0

    doc_files = sorted(root.glob("skills/**/**/SKILL.md"))
    doc_files += sorted(root.glob("template/SKILL.md"))
    doc_files += sorted(root.glob(".claude/agents/*.md"))

    errors = []
    for path in doc_files:
        errors.extend(validate_file(path, index))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"\n{len(errors)} tool-call drift error(s) found in {len(doc_files)} files"
        )
        return 1

    print(
        f"OK: {len(doc_files)} files validated against tool manifest ({len(index)} tools known)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
