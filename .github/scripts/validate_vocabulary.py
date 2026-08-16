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
     carries. `status.X` is the self-maintaining half: a status field the
     operator deletes reds the build on the next snapshot refresh, without
     anyone remembering to add it to a list.
     LIMIT, stated plainly: the flat top-level names (`repositoryRef`,
     `dedupKey`, `documentsTasks`) are recorded in the snapshot and used to
     SUGGEST a replacement, but they are not themselves checked - a bare word
     in prose carries no marker saying it is meant as a field. If the operator
     renames one, this guard stays green. Same for the `state` and `agentKind`
     enums: recorded for provenance, not yet checked, because a bare state name
     in backticks is indistinguishable from ordinary English.
  2. REASON FIELDS. A `<something>Reason=<value>` literal must name a real field
     (`parkReason` or `stateReason`), its value must be in that field's enum,
     and it must NOT be in the other's. stage.go partitions the F.5 closed set
     for a reason; `stageReason=no-outcome` collapsed both halves into a field
     name that is neither, eight times. The match is case-sensitive on the
     capital R, so the restapi's own `reason=head-moved` response literal - a
     real, unrelated thing - is left alone, and an unknown `*Reason=` field is
     reported only when its VALUE is one of ours, so the wrapper's
     `stopReason=end_turn` is not this guard's business.
  3. DEAD TERMS (denylist). Word-boundary, case-insensitive, and scanned in
     PROSE as well as code - see the comment on that check for why it is the one
     exception to the scoping above. Hand-curated in the generator, but every
     entry is verified there to have zero hits in the operator's api/ and
     internal/ trees, so the list cannot rot into blessing a term that came
     back, and a test pins every entry to a camelCase identifier so the prose
     scan can never fire on an English word.

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

Residual false positive, accepted: a Kubernetes/Helm path that genuinely STARTS
with the envelope - `spec.template.spec.containers` in a kubectl example - is
reported, because it is indistinguishable from a claim about our own data model.
The lookbehind on FIELD_RE kills the common cases (quoted source paths,
jsonpath, Go selectors); this one wants a marker, and the error message says so.
"""

import difflib
import json
import pathlib
import re
import sys

from validate_tool_calls import _code_mask, _line_number

VOCABULARY_FILE = ".github/platform-vocabulary.json"

REQUIRED_SECTIONS = ("provenance", "dtoFields", "enums", "deadTerms")
REASON_FIELDS = ("parkReason", "stateReason")

HATCH = "suppress with <!-- vocab-ok: %s --> on this line if it is deliberate"

# `spec.x` / `status.x`. Only the first segment after the envelope is captured -
# `spec.scm.owner` reports as `spec.scm`, which is the part that is wrong.
#
# The lookbehind requires the envelope to START its dotted token. Without it
# `internal/restapi/status.go`, `foo.spec.ts` and `jsonpath='{.spec.nodeName}'`
# all report as field paths - and this is a fleet whose subject IS a Kubernetes
# operator, so quoted source paths and kubectl snippets are ordinary PR content.
FIELD_RE = re.compile(r"(?<![\w./-])(spec|status)\.([A-Za-z][A-Za-z0-9_]*)")

# `<something>Reason = <value>`, case-SENSITIVE on the capital R so the
# restapi's `reason=head-moved` result literal (internal/restapi/outcome.go) is
# not read as a claim about the Task data model.
#
# Two branches: a quoted value after `=` or `:` (the `field="value"` shape this
# corpus actually writes, and the JSON shape a documented response uses), or a
# bare value after `=` only. A bare value after `:` is not matched - that is
# ordinary English punctuation, not a literal.
REASON_RE = re.compile(
    r'"?\b([a-z][A-Za-z0-9]*Reason)\b"?\s*[=:]\s*"([a-z][a-z0-9-]*)"'
    r"|\b([a-z][A-Za-z0-9]*Reason)\s*=\s*([a-z][a-z0-9-]*)"
)

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
    accepted. A nested status object is recorded as dotted leaves, so its
    parent name is admitted too; without that, the first operator change that
    nests one turns `status.<parent>` into a false positive."""
    return {
        segment
        for dto in vocab["dtoFields"].values()
        for name in dto.get("status", [])
        for segment in (name, name.split(".", 1)[0])
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
        """`literal` is both what the marker must NAME to suppress this hit and
        what the message tells the author to write - the two can never drift
        apart, so a marker cannot suppress more than it names."""
        n = _line_number(line_starts, offset)
        line = lines[n - 1]
        if literal.lower() in _exempted(line):
            return
        errors.append(f"{path}:{n}: {message} [{HATCH % literal}]: {line.strip()}")

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
        field = match.group(1) or match.group(3)
        value = match.group(2) or match.group(4)
        literal = f"{field}={value}"
        owner = next((f for f in REASON_FIELDS if value in enums[f]), None)
        if field not in REASON_FIELDS:
            # An unknown `*Reason=` field is only a claim about the TASK data
            # model when it carries one of our values. `stopReason=end_turn` is
            # the Claude API's, `skipReason=already-ingested` is the ingester's,
            # and owning every camelCase *Reason token in the fleet would be an
            # assumption about the future rather than a measurement.
            if owner is None:
                continue
            report(
                match.start(),
                literal,
                f"`{field}` is not a Task reason field; the two are "
                f"`{'` and `'.join(REASON_FIELDS)}` - `{value}` is a `{owner}`",
            )
            continue
        if value in enums[field]:
            continue
        detail = (
            f"it is a `{owner}` - the two vocabularies are disjoint on purpose"
            if owner
            else f"not in the {field} enum ({len(enums[field])} values)"
        )
        report(match.start(), literal, f"`{literal}` - {detail}")

    # 3. Dead terms - checked in PROSE TOO, unlike the two checks above.
    #
    # This is the one place the code-span scoping is deliberately NOT reused.
    # Both `WorkItem` occurrences this guard was written for were bare prose
    # ("no repo target for a project-scoped WorkItem with no branch"), so a
    # masked scan would have caught 0 of 2. A dead noun is English-shaped and
    # gets written in sentences - which is why check-stale-terms.sh, the script
    # this list and its marker are ported from, greps prose. The safety comes
    # from the denylist holding only camelCase platform identifiers (never a
    # word), pinned by a test, plus the per-line marker.
    for entry in vocab["deadTerms"]:
        term = entry["term"]
        for match in re.finditer(rf"\b{re.escape(term)}\b", text, re.IGNORECASE):
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

    # Wider than validate_tool_calls.py's walk, which takes SKILL.md only: the
    # reference/*.md and *-prompt.md files a skill points an agent at are loaded
    # into a context window just the same, and 24 of them were unscanned.
    # Deliberately NOT the repo root - MEMORY.md and CONTENT-TYPES.md describe
    # deleted things on purpose and must stay free to name them.
    root = pathlib.Path(__file__).parent.parent.parent
    doc_files = sorted(
        set(root.glob("skills/**/*.md"))
        | set(root.glob("template/**/*.md"))
        | set(root.glob(".claude/agents/*.md"))
    )

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
