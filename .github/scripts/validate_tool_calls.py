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

A manifest fetch failure (network, 404, no release published yet) is a SOFT
WARNING, not a CI failure, on first rollout (pre-mortem #3): otherwise every
unrelated skill PR blocks the moment the manifest goes briefly missing.
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


def fetch_manifest() -> dict | None:
    root = pathlib.Path(__file__).parent.parent.parent
    version = (root / VERSION_PIN_FILE).read_text(encoding="utf-8").strip()
    tag_path = "latest/download" if version in ("", "latest") else f"download/{version}"
    url = f"https://github.com/{MANIFEST_REPO}/releases/{tag_path}/{MANIFEST_ASSET}"
    try:
        with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        print(
            f"WARNING: could not fetch tool manifest from {url}: {exc}\n"
            "WARNING: skipping tool-call validation for this run (soft warning, "
            "not a CI failure - see tatara-agent-skills#28 pre-mortem #3)",
            file=sys.stderr,
        )
        return None
    except json.JSONDecodeError as exc:
        print(f"WARNING: tool manifest at {url} is not valid JSON: {exc}", file=sys.stderr)
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
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for match in CALL_RE.finditer(line):
            tool, field, value_list = match.group(1), match.group(2), match.group(3)
            if tool not in index:
                continue  # not every parenthesized word is a tool call; unknown names are just prose
            fields = index[tool]
            if field not in fields:
                continue  # not every documented field is enum-constrained; only check ones the manifest tracks
            if NEGATION_RE.search(line[: match.start()]):
                continue
            allowed = fields[field]
            for value in VALUE_RE.findall(value_list):
                if value not in allowed:
                    errors.append(
                        f"{path}:{n}: {tool}({field}=\"{value}\") - \"{value}\" is not a valid "
                        f"{field} for {tool} (allowed: {', '.join(sorted(allowed))}): {line.strip()}"
                    )
    return errors


def main() -> int:
    root = pathlib.Path(__file__).parent.parent.parent
    manifest = fetch_manifest()
    if manifest is None:
        return 0

    index = build_index(manifest)
    if not index:
        print("WARNING: fetched tool manifest has no tools; skipping validation", file=sys.stderr)
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
        print(f"\n{len(errors)} tool-call drift error(s) found in {len(doc_files)} files")
        return 1

    print(f"OK: {len(doc_files)} files validated against tool manifest ({len(index)} tools known)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
