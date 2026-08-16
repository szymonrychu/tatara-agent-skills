"""Tests for sync_claude_contract.py (tatara-agent-skills#57).

The script splices one owned block into every repo's CLAUDE.md. The failure
modes that matter are all about NOT corrupting a file it does not fully
understand: a half-marked file, a reversed pair, a duplicated marker, or a
target that never opted in. Each of those must stop the run rather than guess.
"""

import pytest

import sync_claude_contract as scc

BLOCK = (
    "<!-- BEGIN tatara-shared-contract (generated) -->\n"
    "## Hard rules\n"
    "\n"
    "1. **KISS.**\n"
    "<!-- END tatara-shared-contract -->\n"
)

BEGIN = "<!-- BEGIN tatara-shared-contract (generated) -->"
END = "<!-- END tatara-shared-contract -->"


def target(body):
    return f"# CLAUDE.md - x\n\npreamble\n\n{body}\n## Local\n\nlocal text\n"


# ---------------------------------------------------------------------------
# The fragment itself
# ---------------------------------------------------------------------------


def test_fragment_without_markers_is_an_error(tmp_path):
    frag = tmp_path / "CLAUDE-shared.md"
    frag.write_text("## Hard rules\n\n1. **KISS.**\n")
    with pytest.raises(scc.ContractError):
        scc.load_block(frag)


def test_fragment_block_is_marker_to_marker_inclusive(tmp_path):
    frag = tmp_path / "CLAUDE-shared.md"
    frag.write_text("leading junk\n" + BLOCK + "trailing junk\n")
    assert scc.load_block(frag) == BLOCK


# ---------------------------------------------------------------------------
# Splicing
# ---------------------------------------------------------------------------


def test_splice_replaces_block_and_preserves_surroundings():
    stale = target(
        f"{BEGIN}\n## Hard rules\n\n1. **Something old.**\n{END}\n"
    )
    out = scc.splice(stale, BLOCK, "CLAUDE.md")
    assert out.startswith("# CLAUDE.md - x\n\npreamble\n\n")
    assert out.endswith("## Local\n\nlocal text\n")
    assert "Something old" not in out
    assert "1. **KISS.**" in out


def test_splice_is_idempotent():
    once = scc.splice(target(BLOCK), BLOCK, "CLAUDE.md")
    assert scc.splice(once, BLOCK, "CLAUDE.md") == once


def test_target_with_no_markers_is_skipped_not_created():
    """A repo opts in by adding the markers. The sync never invents them."""
    plain = "# CLAUDE.md - x\n\nno markers here\n"
    assert scc.splice(plain, BLOCK, "CLAUDE.md") is None


@pytest.mark.parametrize(
    "body",
    [
        f"{BEGIN}\n## Hard rules\n",  # BEGIN with no END
        f"## Hard rules\n{END}\n",  # END with no BEGIN
        f"{END}\n## Hard rules\n{BEGIN}\n",  # reversed
        f"{BEGIN}\n{BEGIN}\n## Hard rules\n{END}\n",  # duplicate BEGIN
        f"{BEGIN}\n## Hard rules\n{END}\n{END}\n",  # duplicate END
    ],
    ids=["begin-only", "end-only", "reversed", "dup-begin", "dup-end"],
)
def test_malformed_markers_are_a_hard_error(body):
    with pytest.raises(scc.ContractError):
        scc.splice(target(body), BLOCK, "CLAUDE.md")


# ---------------------------------------------------------------------------
# main(): --check must not write, --write must
# ---------------------------------------------------------------------------


def write_pair(tmp_path, target_body):
    frag = tmp_path / "CLAUDE-shared.md"
    frag.write_text(BLOCK)
    tgt = tmp_path / "CLAUDE.md"
    tgt.write_text(target(target_body))
    return frag, tgt


def test_check_passes_when_in_sync(tmp_path, capsys):
    frag, tgt = write_pair(tmp_path, BLOCK)
    before = tgt.read_text()
    assert scc.main(["--check", "--fragment", str(frag), str(tgt)]) == 0
    assert tgt.read_text() == before


def test_check_fails_on_drift_without_writing(tmp_path):
    frag, tgt = write_pair(
        tmp_path, f"{BEGIN}\n## Hard rules\n\n1. **Drifted.**\n{END}\n"
    )
    before = tgt.read_text()
    assert scc.main(["--check", "--fragment", str(frag), str(tgt)]) != 0
    assert tgt.read_text() == before


def test_write_updates_a_drifted_target(tmp_path):
    frag, tgt = write_pair(
        tmp_path, f"{BEGIN}\n## Hard rules\n\n1. **Drifted.**\n{END}\n"
    )
    assert scc.main(["--write", "--fragment", str(frag), str(tgt)]) == 0
    assert "1. **KISS.**" in tgt.read_text()
    assert scc.main(["--check", "--fragment", str(frag), str(tgt)]) == 0


def test_missing_target_file_is_an_error_not_a_create(tmp_path):
    frag = tmp_path / "CLAUDE-shared.md"
    frag.write_text(BLOCK)
    missing = tmp_path / "nope" / "CLAUDE.md"
    assert scc.main(["--write", "--fragment", str(frag), str(missing)]) != 0
    assert not missing.exists()


def test_malformed_target_fails_check_and_write(tmp_path):
    frag, tgt = write_pair(tmp_path, f"{BEGIN}\n## Hard rules\n")
    assert scc.main(["--check", "--fragment", str(frag), str(tgt)]) != 0
    assert scc.main(["--write", "--fragment", str(frag), str(tgt)]) != 0


def test_write_reports_changed_targets_on_stdout(tmp_path, capsys):
    frag, tgt = write_pair(
        tmp_path, f"{BEGIN}\n## Hard rules\n\n1. **Drifted.**\n{END}\n"
    )
    scc.main(["--write", "--fragment", str(frag), str(tgt)])
    assert "CLAUDE.md" in capsys.readouterr().out
