#!/usr/bin/env python3
"""Splice the owned CLAUDE.md contract block into every tatara repo's CLAUDE.md.

`template/CLAUDE-shared.md` is the source. Each consumer CLAUDE.md carries the
same BEGIN/END marker pair; everything between the markers is generated, and
everything outside them is that repo's own text and is never touched.

Two modes:

    sync_claude_contract.py --check TARGET...   nonzero exit if any drifted
    sync_claude_contract.py --write TARGET...   rewrite drifted targets

A target with NO markers is skipped, not created: a repo opts in by adding the
pair. A target with a broken pair (one marker, reversed, duplicated) is a hard
error - the script will not guess where the block starts in a file it does not
understand, and silently rewriting the wrong span of a contract file is worse
than failing the job.
"""

import argparse
import pathlib
import re
import sys

BEGIN_RE = re.compile(r"^<!-- BEGIN tatara-shared-contract\b.*-->$")
END_RE = re.compile(r"^<!-- END tatara-shared-contract -->$")

DEFAULT_FRAGMENT = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "template" / "CLAUDE-shared.md"
)


class ContractError(Exception):
    """The fragment or a target is malformed. Never recovered from."""


def _locate(text, path):
    """Return (begin_index, end_index) of the marker lines, or None if the file
    carries neither marker. Raises ContractError on any other shape."""
    lines = text.splitlines()
    begins = [i for i, line in enumerate(lines) if BEGIN_RE.match(line.strip())]
    ends = [i for i, line in enumerate(lines) if END_RE.match(line.strip())]

    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1:
        raise ContractError(
            f"{path}: expected exactly one BEGIN and one END tatara-shared-contract "
            f"marker, found {len(begins)} BEGIN and {len(ends)} END"
        )
    if ends[0] < begins[0]:
        raise ContractError(f"{path}: END marker precedes BEGIN marker")
    return begins[0], ends[0]


def load_block(fragment):
    """Read the fragment and return its marker-to-marker block, inclusive."""
    text = pathlib.Path(fragment).read_text()
    span = _locate(text, fragment)
    if span is None:
        raise ContractError(f"{fragment}: fragment carries no tatara-shared-contract markers")
    begin, end = span
    return "\n".join(text.splitlines()[begin : end + 1]) + "\n"


def splice(text, block, path):
    """Return `text` with its block replaced by `block`, or None if the target
    has no markers (opt-in: not our file to edit)."""
    span = _locate(text, path)
    if span is None:
        return None
    begin, end = span
    lines = text.splitlines(keepends=True)
    return "".join(lines[:begin]) + block + "".join(lines[end + 1 :])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift, write nothing")
    mode.add_argument("--write", action="store_true", help="rewrite drifted targets")
    parser.add_argument("--fragment", default=str(DEFAULT_FRAGMENT))
    parser.add_argument("targets", nargs="+", metavar="TARGET")
    args = parser.parse_args(argv)

    try:
        block = load_block(args.fragment)
    except (ContractError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = []
    drifted = []
    for name in args.targets:
        path = pathlib.Path(name)
        try:
            text = path.read_text()
        except OSError as exc:
            errors.append(f"{name}: {exc}")
            continue
        try:
            updated = splice(text, block, name)
        except ContractError as exc:
            errors.append(str(exc))
            continue
        if updated is None:
            print(f"SKIP: {name} (no tatara-shared-contract markers)")
            continue
        if updated == text:
            print(f"OK: {name}")
            continue
        drifted.append(name)
        if args.write:
            path.write_text(updated)
            print(f"WROTE: {name}")
        else:
            print(f"DRIFT: {name}", file=sys.stderr)

    for err in errors:
        print(f"ERROR: {err}", file=sys.stderr)
    if errors:
        return 1
    if args.check and drifted:
        print(
            f"ERROR: {len(drifted)} target(s) drifted from {args.fragment}. "
            f"Run with --write.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
