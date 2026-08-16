"""Regression tests for validate_vocabulary.py (tatara-agent-skills#56).

The guard pins the field paths, reason vocabularies and dead platform terms the
skills quote to tatara-operator's AGENT-FACING contract - the DTOs in
internal/restapi/dto.go, not the raw CRDs. Three checks, all scoped to markdown
code spans by validate_tool_calls._code_mask:

1. field paths   - `spec.X` never exists (the DTO is flat); `status.X` must be a
                   known DTO status field.
2. reason fields - a `<something>Reason=<value>` literal must name a real reason
                   FIELD, its value must be in that field's enum, and must NOT be
                   in the other field's enum (status.stateReason and
                   status.parkReason are disjoint on purpose).
3. dead terms    - a word-boundary denylist of platform nouns the operator
                   deleted.

Written to fail against the pre-fix corpus (which had 12 wrong field paths, 9
collapsed reason mentions and 2 WorkItem references) and pass after it.
"""

import json

import pytest

import validate_vocabulary as vv

VOCAB = {
    "provenance": {"version": "v0.0.0-test"},
    "dtoFields": {
        "task": {
            "top": ["name", "kind", "repositoryRef", "goal", "dedupKey", "documentsTasks"],
            "status": ["state", "stateReason", "parkReason", "notes", "issueRefs", "mrRefs"],
        },
        "repository": {"top": ["name", "url", "defaultBranch"], "status": ["phase"]},
    },
    "enums": {
        "state": ["new", "under-implementation", "done"],
        "parkReason": ["no-outcome", "stage-deadline", "awaiting-human"],
        "stateReason": ["declined", "false-positive", "doc-timeout"],
        "agentKind": ["implement", "review"],
    },
    "deadTerms": [
        {"term": "WorkItem", "note": "deleted CRD"},
        {"term": "handover", "note": "renamed to takeover"},
    ],
}


def write(tmp_path, text):
    path = tmp_path / "SKILL.md"
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. Field paths. The DTO has no spec envelope, and status fields are allow-listed.
# ---------------------------------------------------------------------------


def test_spec_envelope_in_fenced_block_is_an_error(tmp_path):
    """`spec.kind` is the shape Procedure 1 used. The DTO is flat: there is no
    spec envelope at all, so EVERY spec.X is wrong regardless of the suffix."""
    path = write(tmp_path, "```\ntask_get()\n  -> Read spec.kind, spec.repo\n```\n")
    errors = vv.validate_file(path, VOCAB)
    assert errors, "spec.X in a fenced block must be an error"
    assert any("spec.kind" in e for e in errors)
    assert any("spec.repo" in e for e in errors)


def test_spec_error_names_the_flat_replacement_when_one_exists(tmp_path):
    """`spec.kind` has an obvious flat counterpart; say so, so the fix is
    mechanical rather than a hunt through dto.go."""
    path = write(tmp_path, "```\nspec.kind\n```\n")
    errors = vv.validate_file(path, VOCAB)
    assert any("`kind`" in e for e in errors), errors


def test_spec_envelope_in_inline_backticks_is_an_error(tmp_path):
    path = write(tmp_path, "Read it from `spec.documentsTasks` with task_get().\n")
    assert vv.validate_file(path, VOCAB)


def test_spec_envelope_in_bare_prose_is_not_flagged(tmp_path):
    """The false-positive guard inherited from validate_tool_calls: ordinary
    prose is not a documented field path."""
    path = write(tmp_path, "A helm chart spec.template is not our data model.\n")
    assert vv.validate_file(path, VOCAB) == []


def test_unknown_status_field_is_an_error(tmp_path):
    """`status.stage` is what #521 deleted; the field is `status.state`."""
    path = write(tmp_path, "```\ntask_get() -> check status.stage\n```\n")
    errors = vv.validate_file(path, VOCAB)
    assert errors and any("status.stage" in e for e in errors)


def test_known_status_fields_are_clean(tmp_path):
    """Union across every DTO: task status and repository status alike."""
    path = write(
        tmp_path,
        "```\nstatus.state, status.notes, status.issueRefs, status.mrRefs, status.phase\n```\n",
    )
    assert vv.validate_file(path, VOCAB) == []


def test_singular_issue_ref_is_an_error(tmp_path):
    """`status.issueRef` (singular) is the deleted spelling; the DTO field is
    `issueRefs`."""
    path = write(tmp_path, "```\nstatus.issueRef\n```\n")
    assert vv.validate_file(path, VOCAB)


# ---------------------------------------------------------------------------
# 2. Reason fields: real field, real value, and the two vocabularies stay disjoint.
# ---------------------------------------------------------------------------


def test_unknown_reason_field_is_an_error(tmp_path):
    """`stageReason` is neither field. It is the collapse this issue is about,
    and it appeared 8 times, always inside an inline backtick span."""
    path = write(tmp_path, "The Task ages out at `stageReason=no-outcome`, and dies.\n")
    errors = vv.validate_file(path, VOCAB)
    assert errors and any("stageReason" in e for e in errors)


def test_correct_park_reason_is_clean(tmp_path):
    path = write(tmp_path, "The Task ages out at `parkReason=no-outcome`, and dies.\n")
    assert vv.validate_file(path, VOCAB) == []


def test_park_value_on_state_reason_is_an_error(tmp_path):
    """Disjointness, the sharp end: `no-outcome` is a parkReason, so naming it
    as a stateReason is wrong even though both fields exist."""
    path = write(tmp_path, "It parks at `stateReason=no-outcome`.\n")
    errors = vv.validate_file(path, VOCAB)
    assert errors and any("parkReason" in e for e in errors), errors


def test_state_value_on_park_reason_is_an_error(tmp_path):
    path = write(tmp_path, "It parks at `parkReason=declined`.\n")
    assert vv.validate_file(path, VOCAB)


def test_value_in_neither_vocabulary_is_an_error(tmp_path):
    path = write(tmp_path, "It parks at `parkReason=invented-reason`.\n")
    assert vv.validate_file(path, VOCAB)


def test_bare_reason_field_is_not_checked(tmp_path):
    """`reason=head-moved` is a real, correct restapi response literal
    (internal/restapi/outcome.go) and is NOT a Task reason field. Only a
    capital-R `<x>Reason=` token is a claim about the Task data model."""
    path = write(tmp_path, "returns a non-error result carrying `reason=head-moved`\n")
    assert vv.validate_file(path, VOCAB) == []


def test_reason_literal_in_bare_prose_is_not_flagged(tmp_path):
    path = write(tmp_path, "Some prose writes stageReason=no-outcome uncoded.\n")
    assert vv.validate_file(path, VOCAB) == []


# ---------------------------------------------------------------------------
# 3. Dead terms.
# ---------------------------------------------------------------------------


def test_dead_term_in_code_span_is_an_error(tmp_path):
    path = write(tmp_path, "scoped to the repos named in the Task's `WorkItem` ledger\n")
    errors = vv.validate_file(path, VOCAB)
    assert errors and any("WorkItem" in e for e in errors)


def test_dead_term_match_is_case_insensitive(tmp_path):
    path = write(tmp_path, "the `workItem` ledger\n")
    assert vv.validate_file(path, VOCAB)


def test_dead_term_needs_a_word_boundary(tmp_path):
    """`handover` is dead; `handoverride` would be a substring hit, and a
    substring is not a term."""
    path = write(tmp_path, "the `handovertaking` sentinel\n")
    assert vv.validate_file(path, VOCAB) == []


def test_dead_term_in_bare_prose_is_not_flagged(tmp_path):
    path = write(tmp_path, "A generic handover between two humans is fine English.\n")
    assert vv.validate_file(path, VOCAB) == []


# ---------------------------------------------------------------------------
# Escape hatch, ported from tatara-documentation/scripts/check-stale-terms.sh.
# ---------------------------------------------------------------------------


def test_vocab_ok_marker_suppresses_the_named_term(tmp_path):
    path = write(tmp_path, "the `WorkItem` CRD was deleted <!-- vocab-ok: WorkItem -->\n")
    assert vv.validate_file(path, VOCAB) == []


def test_vocab_ok_marker_suppresses_a_named_field_path(tmp_path):
    path = write(tmp_path, "`status.stage` is gone <!-- vocab-ok: status.stage -->\n")
    assert vv.validate_file(path, VOCAB) == []


def test_vocab_ok_marker_naming_another_term_does_not_suppress(tmp_path):
    """Every marker must NAME what it exempts; an unrelated name leaves the hit
    standing, so a marker cannot silently hide a second, real defect."""
    path = write(tmp_path, "the `WorkItem` CRD <!-- vocab-ok: handover -->\n")
    assert vv.validate_file(path, VOCAB)


def test_blanket_vocab_ok_marker_exempts_nothing(tmp_path):
    path = write(tmp_path, "the `WorkItem` CRD <!-- vocab-ok -->\n")
    assert vv.validate_file(path, VOCAB)


def test_vocab_ok_marker_accepts_a_comma_separated_list(tmp_path):
    path = write(
        tmp_path,
        "`spec.kind` and `WorkItem` are gone <!-- vocab-ok: spec.kind, WorkItem -->\n",
    )
    assert vv.validate_file(path, VOCAB) == []


# ---------------------------------------------------------------------------
# Fail-closed on the vocabulary snapshot itself (inherits #46's policy).
# ---------------------------------------------------------------------------


def test_missing_vocabulary_file_fails_the_run(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(vv, "VOCABULARY_FILE", str(tmp_path / "nope.json"))
    assert vv.main() != 0, "a missing vocabulary snapshot must fail the run"


def test_unparseable_vocabulary_file_fails_the_run(monkeypatch, tmp_path):
    bad = tmp_path / "platform-vocabulary.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(vv, "VOCABULARY_FILE", str(bad))
    assert vv.main() != 0, "an unparseable vocabulary snapshot must fail the run"


def test_vocabulary_missing_a_required_section_fails_the_run(monkeypatch, tmp_path):
    """A snapshot that parses but carries no dtoFields would validate every file
    clean - the same silent no-op #46 hardened against."""
    thin = tmp_path / "platform-vocabulary.json"
    thin.write_text(json.dumps({"provenance": {}}), encoding="utf-8")
    monkeypatch.setattr(vv, "VOCABULARY_FILE", str(thin))
    assert vv.main() != 0


# ---------------------------------------------------------------------------
# The shipped snapshot and the live corpus.
# ---------------------------------------------------------------------------


def test_shipped_vocabulary_snapshot_is_well_formed():
    vocab = vv.load_vocabulary()
    assert vocab is not None
    assert vocab["provenance"]["version"].startswith("v")
    assert vocab["dtoFields"]["task"]["top"], "TaskDTO top-level fields must be recorded"
    assert "state" in vocab["dtoFields"]["task"]["status"]
    assert "no-outcome" in vocab["enums"]["parkReason"]
    assert "no-outcome" not in vocab["enums"]["stateReason"]


def test_shipped_reason_vocabularies_are_disjoint():
    """The operator comment this guard encodes: the two vocabularies are
    disjoint on purpose. If a future snapshot breaks that, the disjointness
    check silently becomes a contradiction."""
    vocab = vv.load_vocabulary()
    park = set(vocab["enums"]["parkReason"])
    state = set(vocab["enums"]["stateReason"])
    assert park.isdisjoint(state), sorted(park & state)


def test_live_corpus_is_clean():
    """The end-to-end assertion: every skill, template and agent file in the
    repo validates against the shipped snapshot."""
    assert vv.main() == 0
