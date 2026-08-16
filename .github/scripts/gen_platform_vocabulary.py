#!/usr/bin/env python3
"""Regenerate .github/platform-vocabulary.json from a tatara-operator checkout.

    python3 .github/scripts/gen_platform_vocabulary.py /path/to/tatara-operator

This is NOT run in CI. It exists so the vendored snapshot that
validate_vocabulary.py checks against is REPRODUCIBLE from the operator's own
source rather than hand-transcribed, and so refreshing it after an operator
lifecycle change is a one-command chore with a diff a reviewer can read.

Why a vendored snapshot rather than a fetched artifact (tatara-agent-skills#56
proposed A1, "the operator publishes a release artifact pinned exactly as
tool-manifest.json is"):

  - tatara-cli's release.yml runs `gh release create/upload`, which is what
    makes the tool-manifest pin work. tatara-operator's release.yml publishes a
    Docker image and two Helm charts to Harbor and propagates helmfile pins -
    it creates no GitHub Release and uploads no asset. A1 is therefore not the
    same proven shape; it means standing up release-artifact publishing inside
    a CD train CLAUDE.md warns is not idempotent.
  - With A1's mandated hard-fail-on-fetch, this repo's CI would be red from the
    moment the guard lands until an operator release published the artifact.

SOURCE OF TRUTH IS THE DTO, NOT THE CRD. task_get/project_get/repo_list are
served by internal/restapi/handlers.go, which marshals the DTOs in
internal/restapi/dto.go ("TaskDTO is the stable JSON shape for a Task CRD").
The DTO is flat: there is no `spec` envelope in anything an agent ever reads,
so pinning the skills to api/v1alpha1/*_types.go would pin them one layer too
deep and bless `spec.repositoryRef`, which no response contains.

Dead terms are the one hand-curated list here, ported from
tatara-documentation/scripts/check-stale-terms.sh. They are NOT trusted blind:
every candidate below is verified to have zero word-boundary hits in the
operator's api/ and internal/ trees, and the generator FAILS if one is still
alive. That verification is what keeps the list honest - `deployedVersion`,
`turnsCompleted`, `issueOutcome` and `Subtask` all sit on the documentation
repo's list and are all still live operator identifiers, so that list does not
transfer wholesale.
"""

import json
import pathlib
import re
import subprocess
import sys

OUTPUT_FILE = ".github/platform-vocabulary.json"

DTO_SOURCE = "internal/restapi/dto.go"
STATE_SOURCE = "api/v1alpha1/task_types.go"
REASON_SOURCE = "internal/stage/stage.go"

# The DTO structs an agent can actually receive, and the key each is recorded
# under. Nested *DTO struct fields are expanded into dotted paths, so
# ProjectDTO's `agent agentDTO` becomes agent.model, agent.turnTimeoutSeconds...
ROOT_STRUCTS = {
    "TaskDTO": "task",
    "ProjectDTO": "project",
    "RepositoryDTO": "repository",
}

# Platform nouns the operator deleted, with the reason the term is dead. Each
# is verified absent from the operator checkout before it is written out.
#
# THIS LIST IS NOT APPEND-ONLY (the policy check-stale-terms.sh states, and the
# reason `parkReason` had to come off its list: #521 un-retired it). A term that
# comes back must come off, and the verification below turns that from a
# judgement call into a build failure.
DEAD_TERM_CANDIDATES = [
    ("WorkItem", "deleted CRD; a Task is project-scoped and names its repos via repositoryRef"),
    ("lifecycleState", "deleted status field; #521 replaced it with status.state"),
    ("cascadeStage", "deleted status field; #521 replaced the cascade with the state table"),
    ("deployArtifact", "deleted status field"),
    ("implementOutcome", "deleted status field; outcomes are submit_outcome payloads"),
    ("reviewVerdict", "deleted status field; the verdict is a submit_outcome argument"),
    ("prOutcome", "deleted status field"),
    ("changeSummary", "deleted status field; change_significance carries the level"),
    ("pendingInterjections", "deleted status field"),
    ("implementContext", "deleted status field"),
    ("implementGiveUps", "deleted status field"),
]

STRUCT_RE = re.compile(r"^type\s+(\w+)\s+struct\s*\{(.*?)^\}", re.DOTALL | re.MULTILINE)
FIELD_RE = re.compile(r"^\s*(\w+)\s+([^\s`]+)\s+`json:\"([^\"]+)\"")
CONST_RE = re.compile(r'^\s*(\w+)\s*=\s*"([^"]*)"', re.MULTILINE)
SLICE_RE = re.compile(r"^var\s+(\w+)\s*=\s*\[\]string\{(.*?)^\}", re.DOTALL | re.MULTILINE)


def die(message: str) -> "NoReturn":  # noqa: F821
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def read(root: pathlib.Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        die(f"{path} not found - is {root} a tatara-operator checkout?")
    return path.read_text(encoding="utf-8")


def parse_structs(text: str) -> dict[str, list[tuple[str, str]]]:
    """Go struct name -> [(json tag name, Go type), ...], declaration order."""
    structs = {}
    for match in STRUCT_RE.finditer(text):
        fields = []
        for line in match.group(2).splitlines():
            field = FIELD_RE.match(line)
            if field:
                fields.append((field.group(3).split(",")[0], field.group(2)))
        structs[match.group(1)] = fields
    return structs


def expand(structs: dict, name: str, prefix: str = "") -> list[str]:
    """Flatten a DTO struct into dotted JSON paths. A field whose Go type is
    another struct in this file is recursed into; anything else (a scalar, a
    slice, an apimachinery or api/v1alpha1 type) is a leaf."""
    out = []
    for json_name, go_type in structs.get(name, []):
        nested = go_type.lstrip("*[]")
        if nested in structs:
            out.extend(expand(structs, nested, f"{prefix}{json_name}."))
        else:
            out.append(f"{prefix}{json_name}")
    return out


def dto_fields(text: str) -> dict[str, dict[str, list[str]]]:
    structs = parse_structs(text)
    out = {}
    for struct_name, key in ROOT_STRUCTS.items():
        if struct_name not in structs:
            die(f"{DTO_SOURCE}: {struct_name} not found")
        top, status = [], []
        for json_name, go_type in structs[struct_name]:
            nested = go_type.lstrip("*[]")
            if json_name == "status":
                status = expand(structs, nested) if nested in structs else []
            elif nested in structs:
                top.extend(expand(structs, nested, f"{json_name}."))
            else:
                top.append(json_name)
        if not top:
            die(f"{DTO_SOURCE}: {struct_name} parsed to zero top-level fields")
        out[key] = {"top": top, "status": status}
    return out


def const_values(text: str, prefix: str) -> list[str]:
    """String constants whose Go identifier starts with `prefix`, in order."""
    return [value for name, value in CONST_RE.findall(text) if name.startswith(prefix)]


def const_map(text: str) -> dict[str, str]:
    return dict(CONST_RE.findall(text))


def slice_members(text: str, var_name: str, consts: dict[str, str]) -> list[str]:
    """Resolve `var X = []string{ReasonA, ReasonB}` to its string values."""
    for name, body in SLICE_RE.findall(text):
        if name != var_name:
            continue
        # Strip line comments first: a commented-out `// ReasonB, ReasonC` would
        # otherwise be tokenized as live members and silently keep a retired
        # reason blessed - the one way this generator could produce a WRONG
        # answer rather than dying loudly.
        body = re.sub(r"//[^\n]*", "", body)
        members = []
        for token in re.findall(r"\b(\w+),", body):
            if token not in consts:
                die(f"{REASON_SOURCE}: {var_name} member {token} is not a string const")
            members.append(consts[token])
        if not members:
            die(f"{REASON_SOURCE}: {var_name} parsed to zero members")
        return members
    die(f"{REASON_SOURCE}: var {var_name} not found")


def verify_dead(root: pathlib.Path) -> list[dict]:
    """Keep the denylist honest: a term with any word-boundary hit in the
    operator's api/ or internal/ trees is NOT dead and must not be listed."""
    alive = []
    terms = []
    for term, note in DEAD_TERM_CANDIDATES:
        hits = subprocess.run(
            ["grep", "-rioE", rf"\b{re.escape(term)}\b", "api/", "internal/"],
            cwd=root,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if hits:
            alive.append(f"{term} ({len(hits.splitlines())} hits)")
        else:
            terms.append({"term": term, "note": note})
    if alive:
        die(
            "these dead-term candidates are still live in the operator and must "
            f"be removed from DEAD_TERM_CANDIDATES: {', '.join(alive)}"
        )
    return terms


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    root = pathlib.Path(argv[1]).resolve()

    dto = read(root, DTO_SOURCE)
    states_src = read(root, STATE_SOURCE)
    reasons_src = read(root, REASON_SOURCE)
    consts = const_map(reasons_src)

    states = const_values(states_src, "State")
    if not states:
        die(f"{STATE_SOURCE}: no State* constants found")
    agent_kinds = const_values(reasons_src, "Agent")

    park = slice_members(reasons_src, "ParkReasons", consts)
    state_reasons = slice_members(reasons_src, "RejectReasons", consts) + slice_members(
        reasons_src, "DoneReasons", consts
    )
    overlap = sorted(set(park) & set(state_reasons))
    if overlap:
        die(
            "parkReason and stateReason must stay disjoint (stage.go: the F.5 "
            f"closed set is a partition), but these appear in both: {overlap}"
        )

    describe = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
    )

    vocab = {
        "provenance": {
            "repo": "szymonrychu/tatara-operator",
            "version": describe.stdout.strip() or "unknown",
            "commit": commit.stdout.strip() or "unknown",
            "generator": ".github/scripts/gen_platform_vocabulary.py",
            "sources": {
                "dtoFields": DTO_SOURCE,
                "state": STATE_SOURCE,
                "parkReason": f"{REASON_SOURCE} (ParkReasons)",
                "stateReason": f"{REASON_SOURCE} (RejectReasons + DoneReasons)",
                "agentKind": REASON_SOURCE,
                "deadTerms": "hand-curated, verified absent from api/ and internal/",
            },
        },
        "dtoFields": dto_fields(dto),
        "enums": {
            "state": states,
            "parkReason": park,
            "stateReason": state_reasons,
            "agentKind": agent_kinds,
        },
        "deadTerms": verify_dead(root),
    }

    out = pathlib.Path(__file__).parent.parent.parent / OUTPUT_FILE
    out.write_text(json.dumps(vocab, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: wrote {OUTPUT_FILE} from {vocab['provenance']['repo']} "
        f"{vocab['provenance']['version']} ({vocab['provenance']['commit'][:7]}): "
        f"{len(states)} states, {len(park)} park reasons, "
        f"{len(state_reasons)} state reasons, {len(agent_kinds)} agent kinds, "
        f"{len(vocab['deadTerms'])} dead terms"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
