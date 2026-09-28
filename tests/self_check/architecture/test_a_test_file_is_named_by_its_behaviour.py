"""A test file is named by the behaviour it tests, never by the work item that wrote it.

``test_bead15_s3b_coverage.py`` says which slice of which epic produced the file.
It does not say what the file tests, and the slice is closed the day the file
lands: a reader looking for the tests of a behaviour cannot find this file by
name, and a reader who finds it learns nothing from its name. The same holds for
an epic id (``bdl050``), a tracker id (``beadloom_kug7``), a phase (``f3``) and a
wave (``wave3``).

The population is every file name under ``tests/`` that pytest collects or that a
scenario lives in: ``*.py`` and ``*.feature``, data trees excluded. Folder names
are not judged. A file name is split into tokens on ``_``, ``-`` and ``.``, and a
token is a work-item id when it is one of the shapes in :func:`work_item_ids`.
A token like ``s3`` is also the name of a storage service, so a file that means
the service is declared below rather than guessed at.

What is exempt is declared in :data:`NAMED_BY_WORK_ITEM`, each file with the
reason it was not renamed and the exit that renames it; an entry that no longer
names an offending file fails, so the list only shrinks.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tests.support.repository_root import REPO_ROOT, TESTS_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: The file kinds whose names are judged.
_JUDGED_SUFFIXES = frozenset({".py", ".feature"})

#: Trees under ``tests/`` that are data rather than suite.
_DATA_DIRS = frozenset({"fixtures", "__pycache__"})

#: One token that is a whole id: a bead (``bead15``), an epic (``bdl050``), a
#: slice (``s2``, ``s3b``), a phase (``f3``) or a wave (``wave3``).
_ID_TOKEN = re.compile(r"(?:bead|bdl|wave|s|f)\d+[a-z]?")

#: Two tokens that are one id: ``bdl_074``, ``bead_15``, ``beadloom_kug7``. A
#: tracker suffix carries a digit, so ``beadloom_init`` is not an id.
_ID_PAIRS = (
    ("bdl", re.compile(r"\d+")),
    ("bead", re.compile(r"\d+")),
    ("beadloom", re.compile(r"[a-z0-9]*\d[a-z0-9]*")),
)

_SPLIT = re.compile(r"[_.\-]")

_MIXED_SPLIT = (
    "Exit: the mixed-file split, which names each part by its behaviour as it "
    "moves the part to its node's folder."
)

#: Files still named by a work item, with the reason they were not renamed in
#: BDL-074 E2 and the exit that renames them. Paths relative to the repository.
NAMED_BY_WORK_ITEM: dict[str, str] = {
    "tests/integration/ai_agents/ai_techwriter/test_bdl050_hardening.py": (
        "A collection of edge cases of the tech-writer harness (round cap, "
        "budget, model, branch name, warnings), not one behaviour. " + _MIXED_SPLIT
    ),
    "tests/integration/doc_sync/audit/test_bdl062_seams.py": (
        "The seams between four beads' changes: three unrelated behaviours "
        "grouped by the epic that made them. " + _MIXED_SPLIT
    ),
    "tests/integration/graph/scenarios/test_bead14_s4_binding.py": (
        "Named by path in tests/acceptance/**, which another bead of the same "
        "wave is moving, and in tests/support. Exit: a bead after the "
        "acceptance relocation lands renames the four bead14 files together "
        "with those mentions."
    ),
    "tests/self_check/architecture/test_bead14_s4_binding.py": (
        "The self-check half of test_bead14_s4_binding.py; renamed with it. "
        "Exit: as for tests/integration/graph/scenarios/test_bead14_s4_binding.py."
    ),
    "tests/self_check/docs/test_bead14_s4_binding.py": (
        "The self-check half of test_bead14_s4_binding.py; renamed with it. "
        "Exit: as for tests/integration/graph/scenarios/test_bead14_s4_binding.py."
    ),
    "tests/self_check/process/test_bead14_s4_binding.py": (
        "The self-check half of test_bead14_s4_binding.py; renamed with it. "
        "Exit: as for tests/integration/graph/scenarios/test_bead14_s4_binding.py."
    ),
    "tests/integration/onboarding/scanner/test_bead06_misc_fixes.py": (
        "Four unrelated fixes (framework summaries, parenthesised ref ids, the "
        "parser fingerprint, the bootstrap skeleton count). " + _MIXED_SPLIT
    ),
    "tests/test_bead15_s3b_coverage.py": (
        "Module classification, directory-source depth and the freshness skip: "
        "three behaviours. " + _MIXED_SPLIT
    ),
    "tests/test_bead18_s5_relation.py": (
        "A slice's verification suite over the relation report, the tracker, the "
        "working declaration and the recorded findings. " + _MIXED_SPLIT
    ),
    "tests/self_check/docs/test_bead18_s5_relation.py": (
        "Two self-checks of different behaviours: the relation report's "
        "denominators and the shipped layout's excused pairs. " + _MIXED_SPLIT
    ),
    "tests/test_e2e_wave3.py": (
        "The pipeline end to end, the MCP tool count and the AGENTS.md tool list: "
        "three behaviours. " + _MIXED_SPLIT
    ),
    "tests/test_f3_gate_coverage.py": (
        "Coverage of the gate's error branches, the config-sync edges, "
        "determinism and failure parsing across several nodes. " + _MIXED_SPLIT
    ),
    "tests/test_s2_false_green_residue.py": (
        "One question asked of seven checks (rules, sync-check, the gate, doctor, "
        "lint, docs audit); each answer belongs to its check's node. " + _MIXED_SPLIT
    ),
    "tests/test_s2_lying_checks.py": (
        "Three checks that reported success without checking: incremental "
        "reindex, declared docs, read-only lint. " + _MIXED_SPLIT
    ),
    "tests/test_s2_move_regression.py": (
        "Package data, invocation, vendoring and CI paths after a package move, "
        "across the rule engine and the tech-writer harness. " + _MIXED_SPLIT
    ),
    "tests/self_check/architecture/test_s2_move_regression.py": (
        "Two self-checks of different behaviours: the ai_agents boundary rule and "
        "the tech-writer node's resolution. " + _MIXED_SPLIT
    ),
    "tests/test_s2_seam_crosscutting.py": (
        "Cross-cutting coverage of the database and the repository seam: "
        "connection lifetime, parity, the facade. " + _MIXED_SPLIT
    ),
    "tests/test_s3_config_check_residual.py": (
        "Six blind spots across the guard, suppression, the overlay upgrade and "
        "the composed artifact's states, over several onboarding nodes. " + _MIXED_SPLIT
    ),
    "tests/test_s3_decomposition.py": (
        "Import-path stability of two split packages (federation, rule engine) "
        "that belong to two nodes. " + _MIXED_SPLIT
    ),
    "tests/test_s4_decomposition.py": (
        "Import-path stability of four split packages (reindex, scanner, debt "
        "report, site dashboard) that belong to four nodes. " + _MIXED_SPLIT
    ),
    "tests/test_s4_cli_decomposition.py": (
        "The CLI surface, golden help text and the status command's layering: "
        "the last belongs to the application layer. " + _MIXED_SPLIT
    ),
    "tests/test_s4_the_instruments_agree.py": (
        "Six facts, each stated by two instruments of different nodes. " + _MIXED_SPLIT
    ),
    "tests/unit/graph/contracts/test_federate_f2_gate.py": (
        "A cross-cutting gate over contract verdicts, unknown protocols, "
        "determinism and export parity. " + _MIXED_SPLIT
    ),
}


def work_item_ids(file_name: str) -> list[str]:
    """The work-item ids a file name carries, in the order they appear."""
    tokens = [token for token in _SPLIT.split(file_name.lower()) if token]
    found: list[str] = []
    for index, token in enumerate(tokens):
        if _ID_TOKEN.fullmatch(token):
            found.append(token)
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else ""
        for head, tail in _ID_PAIRS:
            if token == head and tail.fullmatch(following):
                found.append(f"{token}_{following}")
    return found


def _judged_files() -> list[Path]:
    """Every file of the suite whose name is judged, data trees excluded."""
    return sorted(
        path
        for path in TESTS_ROOT.rglob("*")
        if path.suffix in _JUDGED_SUFFIXES
        and path.is_file()
        and not _DATA_DIRS.intersection(path.relative_to(TESTS_ROOT).parts)
    )


def _named_by_work_item() -> dict[str, list[str]]:
    return {
        path.relative_to(REPO_ROOT).as_posix(): ids
        for path in _judged_files()
        if (ids := work_item_ids(path.stem))
    }


class TestNoTestFileIsNamedByAWorkItem:
    def test_no_file_of_the_suite_is_named_by_a_work_item(self) -> None:
        judged = len(_judged_files())
        offenders = sorted(
            f"{path} ({', '.join(ids)})"
            for path, ids in _named_by_work_item().items()
            if path not in NAMED_BY_WORK_ITEM
        )

        assert offenders == [], (
            f"of {judged} file names judged under tests/, these carry a work-item "
            "id instead of the behaviour they test. Rename each after what it "
            f"tests (git mv), or split it if it tests several things: {offenders}"
        )

    def test_every_exemption_still_names_an_offending_file(self) -> None:
        offending = _named_by_work_item()
        unused = sorted(path for path in NAMED_BY_WORK_ITEM if path not in offending)

        assert unused == [], (
            "an exemption names a file that is gone or no longer carries a "
            f"work-item id; remove it: {unused}"
        )

    def test_every_exemption_states_a_reason_and_an_exit(self) -> None:
        silent = sorted(
            path
            for path, reason in NAMED_BY_WORK_ITEM.items()
            if "Exit:" not in reason or not reason.split("Exit:", 1)[0].strip()
        )

        assert silent == [], f"an exemption without a reason or an exit: {silent}"


class TestTheDetectorBites:
    """Each id shape, written fresh, is caught; a behaviour name is not."""

    def test_a_bead_and_a_slice_are_caught(self) -> None:
        assert work_item_ids("test_bead15_s3b_coverage") == ["bead15", "s3b"]

    def test_an_epic_a_phase_and_a_wave_are_caught(self) -> None:
        assert work_item_ids("test_bdl050_hardening") == ["bdl050"]
        assert work_item_ids("test_federate_f2_gate") == ["f2"]
        assert work_item_ids("test_e2e_wave3") == ["wave3"]

    def test_an_id_spelled_over_two_tokens_is_caught(self) -> None:
        assert work_item_ids("test_bdl_074_layout") == ["bdl_074"]
        assert work_item_ids("test_beadloom_kug7_standards") == ["beadloom_kug7"]
        assert work_item_ids("beadloom-2mj3-acceptance") == ["beadloom_2mj3"]

    def test_a_behaviour_name_is_not_caught(self) -> None:
        for name in (
            "test_an_excused_pair_says_so",
            "test_c4",
            "test_e2e_sync_honest",
            "test_source_coverage_n1_parity",
            "test_bead_creation_steps",
            "test_beadloom_init_writes_the_graph",
            "bead_creation",
            "test_utf8_output",
        ):
            assert work_item_ids(name) == [], name
