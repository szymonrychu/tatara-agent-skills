#!/usr/bin/env python3
"""Report whether .github/platform-vocabulary.json still matches tatara-operator.

    python3 .github/scripts/check_vocabulary_currency.py /path/to/tatara-operator

Run by the scheduled `vocabulary-currency` workflow, never by lint.yml: this
gates no PR, and it is the only thing in the repo that can notice the snapshot
going stale (tatara-agent-skills#68).

WHY IT EXISTS. validate_vocabulary.py reads a vendored snapshot and hard-fails
on a value it does not recognise. That is the right blocking behaviour, but a
snapshot with no currency mechanism inverts it: #56 took the snapshot at
operator v2.16.1, the operator reached v3.10.0, and the guard built to stop
skills drifting from the operator's data model was rejecting skill text that
MATCHED it - `parkReason=merge-conflict` and five siblings. Its sibling guard,
validate_tool_calls.py, refetches tatara-cli's manifest on every run; the
operator publishes no GitHub Release assets, so that shape does not transfer
and this cron is the substitute.

FAILS CLOSED, and note that this is the OPPOSITE of the policy on
tatara-observability's reconcile_metric_provenance.py, which documents a failed
operator clone as a neutral skip. That is correct there because it gates
unrelated PRs and a fleet condition must not red somebody else's merge. Here
nothing is gated, so a run that cannot compare and still reports green is a
currency check that has silently stopped checking - the #46 lesson, one layer
up. Every failure mode below is non-zero.

FOUR EXIT CODES, and the third is the one worth reading twice:

  0 CURRENT  the snapshot still says what the operator says
  1 DRIFTED  it does not, and regenerating it is the right answer
  2 SUSPECT  the derivation collapsed; regenerating it would DELETE live
             vocabulary, so the caller must open nothing and get a human
  3 ERROR    this script could not run at all - bad argv, unreadable snapshot.
             Kept distinct from SUSPECT so the caller does not accuse
             tatara-operator's source of a fault in its own invocation.

SUSPECT is #68's pre-mortem 4. gen_platform_vocabulary.py derives by regex over
Go source in three named operator files - `State*`/`Agent*` const blocks,
`var X = []string{...}` slices, and DTO struct bodies. A refactor that moves one
out from under a pattern makes the generator return an empty or short list,
which is indistinguishable from "the operator deleted 34 park reasons" unless
something says so. A job that auto-proposes that diff is worse than no job.

SUSPECT COVERS THE GENERATOR DYING, NOT JUST SHRINKING. Most of those refactors
never produce a short list at all: gen_platform_vocabulary.die() is sys.exit(1),
and 1 is DRIFTED, so an uncaught die() would send the caller down the
propose-a-bump branch for exactly the collapse this verdict exists to stop.
build() is therefore called inside a catch-all.

The shrink guard is two rules, because one leaf is not the only way to collapse:
a per-leaf "lost more than half", and an aggregate "lost more than half of all
members at once" for the pattern change that shortens every list a little.
LIMIT, stated plainly: a single leaf losing 6 of 17 trips neither, so a
derivation that half-breaks one DTO still reads as ordinary drift. The bump PR
is not auto-merged and carries a validate_vocabulary.py run in its body, which
is what catches that case; the guard here is not the last line.

PROVENANCE IS NOT COMPARED. Only dtoFields, enums and deadTerms - the parts
validate_vocabulary.py actually reads. Comparing provenance would make every
operator commit "drift", so this job would be red daily and its bump PR would
change nothing an agent can see, which is how a channel gets muted.
"""

import json
import pathlib
import sys

from gen_platform_vocabulary import build

VOCABULARY_FILE = ".github/platform-vocabulary.json"

COMPARED_SECTIONS = ("dtoFields", "enums", "deadTerms")

CURRENT = 0
DRIFTED = 1
SUSPECT = 2
ERROR = 3

# Sentinel for the test helper: distinguishes "override this key to []" from
# "delete this key entirely", which are the two different collapse shapes.
ABSENT = object()


def _leaves(node, prefix: str) -> dict[str, list]:
    """Every list-valued leaf under a compared section, by dotted path.

    dtoFields nests two levels (`dtoFields.task.status`), enums one
    (`enums.parkReason`), deadTerms none. Walking generically rather than
    hand-listing the paths means an enum the operator adds later is compared
    the day it appears, instead of the day someone remembers to list it here.
    """
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            out.update(_leaves(value, f"{prefix}.{key}"))
        return out
    return {prefix: node if isinstance(node, list) else [node]}


def _describe(path: str, before: list, after: list) -> str:
    added = [json.dumps(x) if isinstance(x, dict) else x for x in after if x not in before]
    removed = [json.dumps(x) if isinstance(x, dict) else x for x in before if x not in after]
    parts = []
    if added:
        parts.append(f"+{len(added)}: {' '.join(map(str, added))}")
    if removed:
        parts.append(f"-{len(removed)}: {' '.join(map(str, removed))}")
    if not parts:
        # Same members, different order or multiplicity. The snapshot records
        # declaration order, and stateReason is RejectReasons + DoneReasons
        # with no dedup, so both are diffs a reviewer should see.
        parts.append("reordered or reduplicated")
    return f"{path} ({len(before)} -> {len(after)}) {'; '.join(parts)}"


def compare(committed: dict, derived: dict) -> tuple[int, list[str]]:
    """(verdict, report lines). Pure over two snapshots - no filesystem, no git."""
    old, new = {}, {}
    for section in COMPARED_SECTIONS:
        old.update(_leaves(committed.get(section, {}), section))
        new.update(_leaves(derived.get(section, {}), section))

    drift, suspect = [], []
    for path in sorted(set(old) | set(new)):
        before, after = old.get(path, []), new.get(path, [])
        if before == after:
            continue
        line = _describe(path, before, after)
        # Lost more than half its members - or all of them, including the whole
        # key going away. Not "the operator deleted these"; "the regex stopped
        # matching". A legitimate mass deletion lands here too and also wants a
        # human, which is the correct direction for a job that gates nothing.
        if before and len(after) * 2 < len(before):
            suspect.append(f"SUSPECT {line}")
        else:
            drift.append(line)

    # Aggregate, at a LOWER threshold than the per-leaf rule - and it has to be
    # lower or it is arithmetic, not a check: if the total loses more than half
    # then some single leaf must have too, so a half-threshold aggregate can
    # never fire on its own. The shape it exists for is every list shedding
    # about half at once, which trips no per-leaf rule at all.
    #
    # A quarter of everything is far outside what one operator release does
    # (the whole vocabulary is ~130 members) and squarely inside what a
    # pattern regression does.
    total_before = sum(len(v) for v in old.values())
    total_after = sum(len(v) for v in new.values())
    if total_before and total_after * 4 < total_before * 3:
        suspect.append(
            f"SUSPECT total members {total_before} -> {total_after}: the whole "
            "derivation lost more than a quarter of its members at once"
        )

    if suspect:
        return SUSPECT, suspect + drift
    if drift:
        return DRIFTED, drift
    return CURRENT, []


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return ERROR
    root = pathlib.Path(argv[1]).resolve()

    path = pathlib.Path(VOCABULARY_FILE)
    if not path.is_absolute():
        path = pathlib.Path(__file__).parent.parent.parent / path
    try:
        committed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not read the committed snapshot {path}: {exc}", file=sys.stderr)
        return ERROR

    # Catch-all, and SystemExit is the point of it: gen_platform_vocabulary.die()
    # is sys.exit(1), and 1 is DRIFTED. A renamed operator source file or a
    # `var ParkReasons` moved out from under SLICE_RE would otherwise send the
    # caller down the propose-a-bump branch, which re-runs the generator and
    # pushes whatever it managed to write.
    try:
        derived = build(root)
    except SystemExit as exc:
        print(
            f"ERROR: gen_platform_vocabulary.py could not derive from {root} "
            f"(exit {exc.code}) - see its message above",
            file=sys.stderr,
        )
        return SUSPECT
    except Exception as exc:  # noqa: BLE001 - any failure here is a collapse
        print(f"ERROR: gen_platform_vocabulary.py raised {exc!r}", file=sys.stderr)
        return SUSPECT

    verdict, report = compare(committed, derived)

    pinned = committed.get("provenance", {})
    live = derived.get("provenance", {})
    print(
        f"snapshot pinned at {pinned.get('version', '?')} ({pinned.get('commit', '?')[:7]}), "
        f"operator checkout at {live.get('version', '?')} ({live.get('commit', '?')[:7]})"
    )
    for line in report:
        print(f"  {line}")

    if verdict == CURRENT:
        print(f"OK: {VOCABULARY_FILE} is current (provenance is deliberately not compared)")
    elif verdict == DRIFTED:
        print(
            f"\nDRIFTED: {len(report)} difference(s). Refresh with "
            f"`python3 .github/scripts/gen_platform_vocabulary.py <operator-checkout>`"
        )
    else:
        print(
            "\nSUSPECT: a derived list collapsed. Do NOT propose this as a bump - "
            "check whether gen_platform_vocabulary.py's patterns still match "
            "tatara-operator's source before touching the snapshot.",
            file=sys.stderr,
        )
    return verdict


if __name__ == "__main__":
    sys.exit(main(sys.argv))
