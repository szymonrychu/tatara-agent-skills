"""Regression tests for the two structural blind spots in validate_tool_calls.py
(tatara-agent-skills#46):

1. An unrecognized tool name inside a documented call was silently `continue`d
   past instead of erroring (:98-99) - the exact case a reaped/renamed tool
   produces, and the one the script's own docstring says is in scope.
2. `fetch_manifest()` returning None on a fetch failure made `main()` return 0
   (:118-119) - validation is skipped entirely rather than failing closed.

Both tests are written to fail against the pre-fix script and pass after the
fix. Run against origin/main (`git stash` the fix, or `git show
f2f3942:.github/scripts/validate_tool_calls.py`) to see them red.
"""

import urllib.error

import validate_tool_calls as vtc

INDEX = {
    "submit_outcome": {"action": {"approved", "declined", "submitted"}},
}


# ---------------------------------------------------------------------------
# Defect 1: unknown tool name must be a hard error, scoped to markdown-code-
# formatted calls (fenced blocks, indented code blocks, inline backtick
# spans) so ordinary prose doesn't drown the build in false positives.
# ---------------------------------------------------------------------------


def test_unknown_tool_in_fenced_block_is_an_error(tmp_path):
    """A reaped/renamed tool name inside a ``` fenced block - the shape every
    genuine documented call in the real corpus uses - must be flagged."""
    skill = tmp_path / "SKILL.md"
    skill.write_text('# doc\n\n```\ndecline_implementation(reason="blocked")\n```\n')
    errors = vtc.validate_file(skill, INDEX)
    assert errors, "unknown tool name in a fenced code block must be an error"
    assert any("decline_implementation" in e for e in errors)


def test_unknown_tool_in_inline_backticks_is_an_error(tmp_path):
    """A reaped tool name referenced as an inline `code span` - the other real
    shape used throughout the corpus - must also be flagged."""
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        '# doc\n\nDo not call `decline_implementation(reason="blocked")` any more.\n'
    )
    errors = vtc.validate_file(skill, INDEX)
    assert errors, "unknown tool name in an inline backtick span must be an error"


def test_unknown_tool_in_indented_code_block_is_an_error(tmp_path):
    """A reaped tool name in a 4-space indented code block (the shape used by
    e.g. tatara-mcp-scm/SKILL.md and tatara-implement-gate/SKILL.md) must also
    be flagged."""
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "# doc\n\n"
        "Some intro text.\n\n"
        '    decline_implementation(reason="blocked")\n\n'
        "More text.\n"
    )
    errors = vtc.validate_file(skill, INDEX)
    assert errors, "unknown tool name in an indented code block must be an error"


def test_unknown_name_in_bare_prose_is_not_flagged(tmp_path):
    """The false-positive guard: a parenthesized, quoted-looking phrase that is
    NOT written as markdown code (no fence, no indent, no backticks) is
    ordinary prose, not a documented tool call, and must stay unchecked - this
    is the exact failure mode the naive `continue` -> `error` flip would
    introduce."""
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "# doc\n\n"
        'Some prose might read like made_up_name(field="value") without ever '
        "meaning to document a tool call.\n"
    )
    errors = vtc.validate_file(skill, INDEX)
    assert errors == [], "bare prose must not be treated as a tool-call reference"


def test_known_tool_valid_enum_in_fenced_block_is_clean(tmp_path):
    """Regression guard: a real, valid call keeps validating clean."""
    skill = tmp_path / "SKILL.md"
    skill.write_text('```\nsubmit_outcome(action="approved")\n```\n')
    errors = vtc.validate_file(skill, INDEX)
    assert errors == []


def test_known_tool_invalid_enum_in_fenced_block_is_still_an_error(tmp_path):
    """Regression guard: the pre-existing enum-literal check still fires."""
    skill = tmp_path / "SKILL.md"
    skill.write_text('```\nsubmit_outcome(action="bogus")\n```\n')
    errors = vtc.validate_file(skill, INDEX)
    assert errors, "invalid enum literal for a known tool must still be an error"


# ---------------------------------------------------------------------------
# Defect 2: a manifest fetch failure must fail the run, not silently pass it.
# ---------------------------------------------------------------------------


def test_fetch_failure_fails_the_run(monkeypatch, capsys):
    """Simulate a network/CDN failure on the manifest fetch and confirm
    main() fails closed (non-zero exit) instead of returning 0."""

    def boom(*_args, **_kwargs):
        raise urllib.error.URLError("simulated network failure")

    monkeypatch.setattr(vtc.urllib.request, "urlopen", boom)

    rc = vtc.main()

    assert rc != 0, "a manifest fetch failure must fail the run, not return 0"


def test_fetch_manifest_returns_none_on_failure(monkeypatch):
    """fetch_manifest() itself still reports failure as None (main() is what
    turns that into a hard failure) - pin this so the two units stay decoupled
    and testable independently."""

    def boom(*_args, **_kwargs):
        raise urllib.error.URLError("simulated network failure")

    monkeypatch.setattr(vtc.urllib.request, "urlopen", boom)

    assert vtc.fetch_manifest() is None
