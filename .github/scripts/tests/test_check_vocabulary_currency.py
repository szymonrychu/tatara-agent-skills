"""Tests for check_vocabulary_currency.py (tatara-agent-skills#68).

The comparison layer is pure over two dicts - the committed snapshot and the
one re-derived from an operator checkout - so none of this needs a fake
tatara-operator tree. Only main() touches the generator, and that is
monkeypatched.

Three verdicts, and the middle one is the whole point of the script:

  CURRENT  the snapshot still says what the operator says
  DRIFTED  it does not, and a bump PR is the right answer
  SUSPECT  the derivation collapsed, and a bump PR would DELETE live vocabulary

SUSPECT exists because gen_platform_vocabulary.py derives by regex over Go
source - `State*`/`Agent*` const blocks, `var X = []string{...}` slices, and DTO
struct bodies. A refactor that moves one out from under a pattern makes the
generator return a short list, or die outright, and either is indistinguishable
from "the operator deleted 34 park reasons" unless something says so. A job that
auto-proposes that diff is worse than no job (issue #68 pre-mortem 4).

Two halves are tested separately, because they fail in different places:

  compare()  pure over two dicts, so the collapse shapes that REACH it are
             exercised directly, no fake operator tree needed
  main()     the collapse shapes that never reach it, because the generator
             die()s first - which is most of them, and which read as exit 1
             DRIFTED unless main() catches them
"""

import json

import pytest

import check_vocabulary_currency as cvc

SNAPSHOT = {
    "provenance": {"version": "v2.16.1", "commit": "eab7870"},
    "dtoFields": {
        "task": {"top": ["name", "kind", "goal"], "status": ["state", "parkReason"]},
        "repository": {"top": ["name", "url"], "status": ["phase"]},
    },
    "enums": {
        "state": ["new", "done"],
        "parkReason": ["no-outcome", "stage-deadline", "awaiting-human", "ci-pending"],
        "stateReason": ["declined", "false-positive"],
        "agentKind": ["implement", "review"],
    },
    "deadTerms": [{"term": "WorkItem", "note": "deleted CRD"}],
}


def derived(**overrides):
    """A copy of SNAPSHOT with dotted-path overrides applied, e.g.
    derived(**{"enums.parkReason": [...]})."""
    out = json.loads(json.dumps(SNAPSHOT))
    for path, value in overrides.items():
        node = out
        *parents, leaf = path.split(".")
        for key in parents:
            node = node[key]
        if value is cvc.ABSENT:
            del node[leaf]
        else:
            node[leaf] = value
    return out


# ---------------------------------------------------------------------------
# CURRENT
# ---------------------------------------------------------------------------


def test_identical_snapshots_are_current():
    verdict, report = cvc.compare(SNAPSHOT, derived())
    assert verdict == cvc.CURRENT
    assert report == []


def test_provenance_only_difference_is_current():
    """provenance is deliberately NOT compared. Every operator commit moves the
    commit sha, so comparing it would make the job permanently red and propose
    a daily bump PR that changes nothing an agent can read."""
    verdict, _ = cvc.compare(
        SNAPSHOT, derived(**{"provenance.version": "v3.10.0", "provenance.commit": "d22349a"})
    )
    assert verdict == cvc.CURRENT


# ---------------------------------------------------------------------------
# DRIFTED
# ---------------------------------------------------------------------------


def test_added_enum_value_is_drift():
    """The live shape of #68: the operator grew six park reasons and the
    snapshot never heard of them, so the blocking guard rejects correct text."""
    verdict, report = cvc.compare(
        SNAPSHOT,
        derived(**{"enums.parkReason": SNAPSHOT["enums"]["parkReason"] + ["merge-conflict"]}),
    )
    assert verdict == cvc.DRIFTED
    assert any("enums.parkReason" in line and "merge-conflict" in line for line in report)


def test_report_names_what_was_added_and_what_was_removed():
    verdict, report = cvc.compare(
        SNAPSHOT, derived(**{"enums.stateReason": ["declined", "doc-timeout"]})
    )
    assert verdict == cvc.DRIFTED
    line = next(line for line in report if "enums.stateReason" in line)
    assert "doc-timeout" in line and "false-positive" in line


def test_single_removal_is_drift_not_suspect():
    """One value going away is an ordinary operator change and the bump PR is
    the correct response. Only a collapse is SUSPECT."""
    verdict, _ = cvc.compare(
        SNAPSHOT, derived(**{"enums.parkReason": SNAPSHOT["enums"]["parkReason"][:3]})
    )
    assert verdict == cvc.DRIFTED


def test_dto_status_leaf_change_is_drift():
    verdict, report = cvc.compare(
        SNAPSHOT, derived(**{"dtoFields.task.status": ["state", "parkReason", "mrRefs"]})
    )
    assert verdict == cvc.DRIFTED
    assert any("dtoFields.task.status" in line for line in report)


def test_dead_terms_change_is_drift():
    verdict, report = cvc.compare(
        SNAPSHOT, derived(deadTerms=[{"term": "WorkItem", "note": "deleted CRD"},
                                     {"term": "lifecycleState", "note": "deleted status field"}])
    )
    assert verdict == cvc.DRIFTED
    assert any("deadTerms" in line for line in report)


def test_a_new_enum_appearing_is_drift():
    """The operator adding a whole enum is an addition, not a collapse."""
    verdict, _ = cvc.compare(SNAPSHOT, derived(**{"enums.originKind": ["takeover"]}))
    assert verdict == cvc.DRIFTED


# ---------------------------------------------------------------------------
# SUSPECT - the shrink guard (#68 pre-mortem 4)
# ---------------------------------------------------------------------------


def test_empty_derivation_is_suspect():
    """The two collapse shapes that actually REACH compare(). Everything else
    in gen_platform_vocabulary.py die()s first - see the main() tests below.

    `agent_kinds = const_values(reasons_src, "Agent")` is the only derived list
    with no die() guard, so `Agent*` consts becoming typed derives to []; and
    dto_fields() records a status of [] for a DTO whose status type stops
    resolving. A naive job would open a PR deleting the whole enum."""
    verdict, report = cvc.compare(SNAPSHOT, derived(**{"enums.agentKind": []}))
    assert verdict == cvc.SUSPECT
    assert any("SUSPECT" in line and "enums.agentKind" in line for line in report)

    verdict, _ = cvc.compare(SNAPSHOT, derived(**{"dtoFields.task.status": []}))
    assert verdict == cvc.SUSPECT


def test_losing_more_than_half_is_suspect():
    verdict, _ = cvc.compare(SNAPSHOT, derived(**{"enums.parkReason": ["no-outcome"]}))
    assert verdict == cvc.SUSPECT


def test_losing_exactly_half_is_still_drift():
    """The boundary, pinned: `len(derived) * 2 < len(committed)`. Halving a
    four-value enum is a large but legible operator change."""
    verdict, _ = cvc.compare(
        SNAPSHOT, derived(**{"enums.parkReason": ["no-outcome", "stage-deadline"]})
    )
    assert verdict == cvc.DRIFTED


def test_a_missing_section_is_suspect():
    """A generator that stops emitting `enums` at all must not read as "the
    operator deleted every enum"."""
    verdict, _ = cvc.compare(SNAPSHOT, derived(enums=cvc.ABSENT))
    assert verdict == cvc.SUSPECT


def test_a_missing_dto_is_suspect():
    verdict, _ = cvc.compare(SNAPSHOT, derived(**{"dtoFields.repository": cvc.ABSENT}))
    assert verdict == cvc.SUSPECT


def test_every_leaf_shedding_exactly_half_is_suspect_on_the_aggregate():
    """The shape the per-leaf rule structurally cannot see. Each leaf loses
    EXACTLY half, so `len(after) * 2 < len(before)` is false everywhere, and a
    per-leaf-only guard proposes a PR deleting half the vocabulary.

    The aggregate has to sit at a lower threshold than the per-leaf rule to
    exist at all: if the total loses more than half, some single leaf must have
    too, so a half-on-half aggregate is arithmetic rather than a check."""
    before = {"enums": {"a": ["1", "2", "3", "4"], "b": ["1", "2"], "c": ["1", "2", "3", "4"]}}
    after = {"enums": {"a": ["1", "2"], "b": ["1"], "c": ["1", "2"]}}
    verdict, report = cvc.compare(before, after)
    assert verdict == cvc.SUSPECT
    assert any("SUSPECT" in line and "total members 10 -> 5" in line for line in report), report


def test_the_aggregate_does_not_fire_on_one_ordinary_removal():
    """It has to stay quiet on the drift the job is supposed to auto-propose,
    or the bump PR never opens and this is #56's manual chore again."""
    thinner = derived(**{"enums.parkReason": SNAPSHOT["enums"]["parkReason"][:3]})
    assert cvc.compare(SNAPSHOT, thinner)[0] == cvc.DRIFTED


def test_suspect_wins_over_drift():
    """A run that is BOTH short one value somewhere and collapsed elsewhere
    must not report the proposable verdict."""
    verdict, _ = cvc.compare(
        SNAPSHOT,
        derived(**{
            "enums.parkReason": [],
            "enums.stateReason": ["declined", "false-positive", "doc-timeout"],
        }),
    )
    assert verdict == cvc.SUSPECT


# ---------------------------------------------------------------------------
# Exit codes. The workflow branches on these, so they are the contract.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "override,expected",
    [
        ({}, cvc.CURRENT),
        ({"enums.parkReason": SNAPSHOT["enums"]["parkReason"] + ["merge-conflict"]}, cvc.DRIFTED),
        ({"enums.parkReason": []}, cvc.SUSPECT),
    ],
)
def test_main_returns_the_verdict_as_its_exit_code(monkeypatch, tmp_path, override, expected):
    snapshot = tmp_path / "platform-vocabulary.json"
    snapshot.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    monkeypatch.setattr(cvc, "VOCABULARY_FILE", str(snapshot))
    monkeypatch.setattr(cvc, "build", lambda root: derived(**override))
    assert cvc.main(["check_vocabulary_currency.py", str(tmp_path)]) == expected


def test_main_without_a_checkout_path_is_an_error_not_a_suspect_derivation(tmp_path):
    """ERROR, not SUSPECT: the workflow prints "the generator derived a
    collapsed vocabulary" on SUSPECT, and a bad argv would make that a false
    accusation against tatara-operator's source."""
    assert cvc.main(["check_vocabulary_currency.py"]) == cvc.ERROR


def test_main_fails_closed_on_an_unreadable_snapshot(monkeypatch, tmp_path):
    """The #46 policy. This job gates nothing, so a run that cannot compare and
    still reports green is a currency check that silently stopped checking."""
    monkeypatch.setattr(cvc, "VOCABULARY_FILE", str(tmp_path / "nope.json"))
    monkeypatch.setattr(cvc, "build", lambda root: derived())
    assert cvc.main(["check_vocabulary_currency.py", str(tmp_path)]) == cvc.ERROR


def _snapshot_at(monkeypatch, tmp_path):
    path = tmp_path / "platform-vocabulary.json"
    path.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    monkeypatch.setattr(cvc, "VOCABULARY_FILE", str(path))


def test_a_generator_that_dies_is_suspect_not_drift(monkeypatch, tmp_path):
    """THE reachability test. Almost every collapse gen_platform_vocabulary.py
    can suffer - a renamed source file, `var ParkReasons` moving out from under
    SLICE_RE, a ROOT_STRUCT rename - goes through its die(), which is
    sys.exit(1). Uncaught, that IS the DRIFTED exit code, so the shrink guard
    would never fire for the case it was written for and the workflow would
    take the propose-a-bump branch."""
    _snapshot_at(monkeypatch, tmp_path)

    def dies(root):
        print("ERROR: internal/stage/stage.go: var ParkReasons not found")
        raise SystemExit(1)

    monkeypatch.setattr(cvc, "build", dies)
    assert cvc.main(["check_vocabulary_currency.py", str(tmp_path)]) == cvc.SUSPECT


def test_an_unexpected_generator_exception_is_suspect(monkeypatch, tmp_path):
    """A traceback out of build() must not reach the propose-a-bump branch
    either - that branch re-runs the generator and pushes whatever it wrote."""
    _snapshot_at(monkeypatch, tmp_path)

    def explodes(root):
        raise RuntimeError("regex broke")

    monkeypatch.setattr(cvc, "build", explodes)
    assert cvc.main(["check_vocabulary_currency.py", str(tmp_path)]) == cvc.SUSPECT


def test_a_generator_exiting_zero_with_no_vocabulary_is_suspect(monkeypatch, tmp_path):
    _snapshot_at(monkeypatch, tmp_path)
    monkeypatch.setattr(cvc, "build", lambda root: {})
    assert cvc.main(["check_vocabulary_currency.py", str(tmp_path)]) == cvc.SUSPECT
