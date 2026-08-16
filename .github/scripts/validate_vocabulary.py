#!/usr/bin/env python3
"""Validate that skill-documented platform vocabulary matches tatara-operator's
agent-facing data model (DTO field paths, the two reason vocabularies, and
platform nouns the operator deleted).

validate_tool_calls.py pins every documented `tool(field="value")` literal to
tatara-cli's tool manifest, and its docstring names the hole it closes: "a skill
naming a renamed/removed tool or a stale enum value reads fine to a human
reviewer and fails only at agent runtime". The identical hole exists one layer
down - nothing pinned the FIELD PATHS and REASON NAMES the skills quote to the
operator - and it had drifted (tatara-agent-skills#56): Procedure 1, the orient
sequence every agent runs at turn 0, named six fields no response contains.

SOURCE OF TRUTH IS THE DTO, NOT THE CRD. task_get/project_get/repo_list are
served by internal/restapi/handlers.go, which marshals the DTOs in
internal/restapi/dto.go ("TaskDTO is the stable JSON shape for a Task CRD").
Those DTOs are FLAT: `kind`, `repositoryRef`, `goal`, `dedupKey` and
`documentsTasks` are top-level, and there is no `spec` envelope in anything an
agent ever reads. Pinning to api/v1alpha1/*_types.go instead would bless
`spec.repositoryRef`, which is just as absent from a real response as the
`spec.repo` it would have replaced.

The vocabulary is a VENDORED SNAPSHOT (.github/platform-vocabulary.json),
regenerated from an operator checkout by gen_platform_vocabulary.py rather than
fetched at CI time - see that script's docstring for why the tool-manifest's
fetch-and-pin shape does not transfer (the operator publishes no GitHub Release
assets at all, and a hard-fail-on-fetch guard would be red from the moment it
landed until the first such release existed).

THREE CHECKS, all scoped to markdown code by validate_tool_calls._code_mask -
a fenced ``` block, a 4-space indented block, or an inline `backtick` span.
That scoping is reused rather than reimplemented, and it is the same measured
precedent: every genuine documented call in this corpus is written that way.

  1. FIELD PATHS (allow-list). `spec.X` is ALWAYS an error - the DTO has no spec
     envelope - and `status.X` must name a field some DTO status actually
     carries. This is the self-maintaining half: a field the operator deletes
     reds the build on the next snapshot refresh, without anyone remembering to
     add it to a list.
  2. REASON FIELDS. A `<something>Reason=<value>` literal must name a real field
     (`parkReason` or `stateReason`), its value must be in that field's enum,
     and it must NOT be in the other's. stage.go partitions the F.5 closed set
     for a reason; `stageReason=no-outcome` collapsed both halves into a field
     name that is neither, eight times. The match is case-sensitive on the
     capital R, so the restapi's own `reason=head-moved` response literal - a
     real, unrelated thing - is left alone.
  3. DEAD TERMS (denylist). Word-boundary, case-insensitive. Hand-curated in the
     generator, but every entry is verified there to have zero hits in the
     operator's api/ and internal/ trees, so the list cannot rot into blessing a
     term that came back.

LINE-LEVEL SUPPRESSION, ported from tatara-documentation/scripts/
check-stale-terms.sh: text that must legitimately NAME a dead thing (to say it
was removed) carries an HTML comment naming what it exempts, comma-separated:

    `status.stage` was deleted by #521. <!-- vocab-ok: status.stage -->

The marker must NAME every literal it exempts - a blanket `<!-- vocab-ok -->`
exempts nothing - so it can never silently hide an unrelated second defect on
the same line. As with that script's list, THIS ONE IS NOT APPEND-ONLY.

A missing, unparseable or structurally incomplete snapshot FAILS THE RUN, the
same fail-closed policy validate_tool_calls.py was hardened to
(tatara-agent-skills#46): a check that cannot load its source of truth must not
look, in CI, identical to a repo with zero drift.

Not in scope, and deliberately: state-name literals. `parked` and `implementing`
read as ordinary English (`a parked Task`, `while implementing`) far more often
than as a claim about status.state, so a word-boundary check on them would be a
false-positive machine. Those hits stay a review-time judgement.
"""

import difflib
import json
import pathlib
import re
import sys

from validate_tool_calls import _code_mask, _line_number

VOCABULARY_FILE = ".github/platform-vocabulary.json"

REQUIRED_SECTIONS = ("dtoFields", "enums", "deadTerms")
REASON_FIELDS = ("parkReason", "stateReason")

# `spec.x` / `status.x`. Only the first segment after the envelope is captured -
# `spec.scm.owner` reports as `spec.scm`, which is the part that is wrong.
FIELD_RE = re.compile(r"\b(spec|status)\.([A-Za-z][A-Za-z0-9_]*)")

# `<something>Reason=<value>`, case-SENSITIVE on the capital R so the restapi's
# `reason=head-moved` result literal (internal/restapi/outcome.go) is not a
# claim about the Task data model and is not checked here.
REASON_RE = re.compile(r"\b([a-z][A-Za-z0-9]*Reason)\s*=\s*([a-z][a-z0-9-]*)")

MARKER_RE = re.compile(r"<!--\s*vocab-ok:([^>]*?)-->")


def load_vocabulary() -> dict | None:
    """Read the vendored snapshot. Returns None - which main() turns into a
    non-zero exit - when it is missing, unparseable, or missing a section the
    checks need, so a broken snapshot can never validate the corpus clean."""
    path = pathlib.Path(VOCABULARY_FILE)
    if not path.is_absolute():
        path = pathlib.Path(__file__).parent.parent.parent / path
    try:
        vocab = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"ERROR: could not read {path}: {exc}", file=sys.stderr)
        return None
    except json.JSONDecodeError as exc:
        print(f"ERROR: {path} is not valid JSON: {exc}", file=sys.stderr)
        return None

    missing = [s for s in REQUIRED_SECTIONS if not vocab.get(s)]
    if missing:
        print(
            f"ERROR: {path} is missing required section(s): {', '.join(missing)}",
            file=sys.stderr,
        )
        return None
    for field in REASON_FIELDS:
        if not vocab["enums"].get(field):
            print(f"ERROR: {path}: enums.{field} is empty or absent", file=sys.stderr)
            return None
    return vocab


def _status_fields(vocab: dict) -> set[str]:
    """Union of status field names across every DTO - the checker cannot tell
    which object a given `status.x` refers to, so any DTO's status field is
    accepted."""
    return {
        name
        for dto in vocab["dtoFields"].values()
        for name in dto.get("status", [])
    }


def _flat_paths(vocab: dict) -> dict[str, str]:
    """last path segment (lowercased) -> full flat DTO path, for suggesting the
    replacement when a `spec.x` names something that does exist, flat."""
    out = {}
    for dto in vocab["dtoFields"].values():
        for path in dto.get("top", []):
            out.setdefault(path.rsplit(".", 1)[-1].lower(), path)
    return out


def _exempted(line: str) -> set[str]:
    """Lowercased literals named by every `<!-- vocab-ok: ... -->` on the line.
    A marker naming nothing exempts nothing."""
    out = set()
    for marker in MARKER_RE.findall(line):
        for part in marker.split(","):
            part = part.strip().lower()
            if part:
                out.add(part)
    return out


def _suggest(name: str, candidates) -> str:
    close = difflib.get_close_matches(name, sorted(candidates), n=1, cutoff=0.7)
    return f", did you mean `status.{close[0]}`?" if close else ""


def validate_file(path: pathlib.Path, vocab: dict) -> list[str]:
    errors = []
    text = path.read_text(encoding="utf-8")
    mask = _code_mask(text)
    lines = text.splitlines()

    line_starts = [0]
    for line in text.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))

    status_fields = _status_fields(vocab)
    flat_paths = _flat_paths(vocab)
    enums = vocab["enums"]

    def report(offset: int, literal: str, message: str) -> None:
        n = _line_number(line_starts, offset)
        line = lines[n - 1]
        if literal.lower() in _exempted(line):
            return
        errors.append(f"{path}:{n}: {message}: {line.strip()}")

    # 1. Field paths.
    for match in FIELD_RE.finditer(text):
        if not mask[match.start()]:
            continue
        envelope, field = match.group(1), match.group(2)
        literal = f"{envelope}.{field}"
        if envelope == "spec":
            flat = flat_paths.get(field.lower())
            hint = (
                f" - the DTO is flat, use `{flat}`"
                if flat
                else " - the DTO is flat and carries no such field"
            )
            report(
                match.start(),
                literal,
                f"`{literal}` - no agent-visible response has a `spec` envelope"
                f" (internal/restapi/dto.go){hint}",
            )
        elif field not in status_fields:
            report(
                match.start(),
                literal,
                f"`{literal}` - no DTO status carries `{field}`"
                f"{_suggest(field, status_fields)}",
            )

    # 2. Reason fields, and the disjointness stage.go keeps on purpose.
    for match in REASON_RE.finditer(text):
        if not mask[match.start()]:
            continue
        field, value = match.group(1), match.group(2)
        if field not in REASON_FIELDS:
            owner = next((f for f in REASON_FIELDS if value in enums[f]), None)
            hint = f" - `{value}` is a `{owner}`" if owner else ""
            report(
                match.start(),
                field,
                f"`{field}` is not a Task reason field; the two are "
                f"`{'` and `'.join(REASON_FIELDS)}`{hint}",
            )
            continue
        if value in enums[field]:
            continue
        other = next((f for f in REASON_FIELDS if f != field and value in enums[f]), None)
        detail = (
            f"it is a `{other}` - the two vocabularies are disjoint on purpose"
            if other
            else f"not in the {field} enum ({len(enums[field])} values)"
        )
        report(match.start(), f"{field}={value}", f"`{field}={value}` - {detail}")

    # 3. Dead terms.
    for entry in vocab["deadTerms"]:
        term = entry["term"]
        for match in re.finditer(rf"\b{re.escape(term)}\b", text, re.IGNORECASE):
            if not mask[match.start()]:
                continue
            report(
                match.start(),
                term,
                f"`{term}` no longer exists in tatara-operator - {entry['note']}",
            )

    return errors


def main() -> int:
    vocab = load_vocabulary()
    if vocab is None:
        print(
            "ERROR: vocabulary validation failed closed - no snapshot to validate "
            "against (tatara-agent-skills#46 policy). Regenerate it with "
            "`python3 .github/scripts/gen_platform_vocabulary.py <operator-checkout>`",
            file=sys.stderr,
        )
        return 1

    root = pathlib.Path(__file__).parent.parent.parent
    doc_files = sorted(root.glob("skills/**/**/SKILL.md"))
    doc_files += sorted(root.glob("template/SKILL.md"))
    doc_files += sorted(root.glob(".claude/agents/*.md"))

    errors = []
    for path in doc_files:
        errors.extend(validate_file(path, vocab))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"\n{len(errors)} platform-vocabulary drift error(s) found in "
            f"{len(doc_files)} files"
        )
        return 1

    provenance = vocab["provenance"]
    print(
        f"OK: {len(doc_files)} files validated against tatara-operator "
        f"{provenance['version']} ({provenance['commit'][:7]}): "
        f"{len(_status_fields(vocab))} status fields, "
        f"{len(vocab['enums']['parkReason'])} park reasons, "
        f"{len(vocab['enums']['stateReason'])} state reasons, "
        f"{len(vocab['deadTerms'])} dead terms"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
