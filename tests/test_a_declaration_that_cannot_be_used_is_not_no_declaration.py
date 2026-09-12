"""A project that opted in and mistyped a key must not be told it opted out.

BDL-069, ``beadloom-rqma.7``. Both of this project's DECLARED legs — the
``readme-pair`` one this epic shipped and the ``issue-log`` one it was modelled
on — read their block out of ``.beadloom/config.yml`` and refused a malformed
one to ``logging``, which the Gate does not render. Four ways of misdeclaring
each reached the same verdict as declaring nothing at all.

Measured at HEAD on a foreign two-package project, ``beadloom ci`` after each
edit to ``.beadloom/config.yml``::

    A  source + follower, both real     PASS  1 pair(s) held, 6 block(s) compared
    B  source alone                     SKIP  no document pair is declared
    C  source + `followr:`              SKIP  no document pair is declared
    D  `../README.ru.md` + follower     SKIP  no document pair is declared
    E  `document_pairs: README.md`      SKIP  no document pair is declared
    F  source names a missing file      FAIL  UNREADABLE: NOPE.ru.md

B through E were byte-identical to the line a project that declares nothing
gets, and the whole gate exited 0. F is the case this epic got right and is the
shape the other four are held to here: the declaration pointed at nothing and
the leg said so, by name.

**The count is the point, not the wording.** A skip reworded to "possibly
nothing was declared" is the same defect in softer words, so every assertion
below is against the opt-out's OWN verdict and against a stated number of
unusable entries — rewording one line cannot pass them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.gate import _step_issue_numbers, _step_readme_pair
from beadloom.doc_sync.document_pairs import check_document_pairs
from beadloom.doc_sync.issue_numbers import check_issue_numbers

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.gate import GateStep

_BASE_CONFIG = "languages:\n- .py\n"

#: The reviewer's B, C, D and E, verbatim in the shape the table measured them,
#: each paired with the token a reader needs to see in the verdict to find it.
PAIR_MISDECLARATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "B the follower key is absent",
        "document_pairs:\n  - source: README.ru.md\n",
        "follower",
    ),
    (
        "C the follower key is misspelled",
        "document_pairs:\n  - source: README.ru.md\n    followr: README.md\n",
        "followr",
    ),
    (
        "D the source escapes the project root",
        "document_pairs:\n  - source: ../README.ru.md\n    follower: README.md\n",
        "../README.ru.md",
    ),
    ("E the block is a scalar", "document_pairs: README.md\n", "document_pairs"),
)

#: The same four ways for ``issue_log:``, which is BDL-UX #270 — the defect in
#: the neighbouring leg, fixed here rather than left as a second copy of the
#: rule about to be born.
LOG_MISDECLARATIONS: tuple[tuple[str, str, str], ...] = (
    ("the path key is misspelled", "issue_log:\n  paths: ISSUES.md\n  ledger: issues\n", "path"),
    ("the ledger key is misspelled", "issue_log:\n  path: ISSUES.md\n  ledgr: issues\n", "ledger"),
    ("the block is a scalar", "issue_log: ISSUES.md\n", "issue_log"),
    (
        "an entry is not a string",
        "issue_log:\n  path: [ISSUES.md]\n  ledger: issues\n",
        "path",
    ),
)


def _project(root: Path, config: str) -> Path:
    """A project root whose config declares *config* and which holds two READMEs."""
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(_BASE_CONFIG + config, encoding="utf-8")
    (root / "README.md").write_text("# Title\n\nA paragraph.\n", encoding="utf-8")
    (root / "README.ru.md").write_text("# Title\n\nAbzac.\n", encoding="utf-8")
    (root / "ISSUES.md").write_text("1. an entry\n", encoding="utf-8")
    return root


def _verdict(step: GateStep) -> tuple[bool, bool, str]:
    return (step.passed, step.skipped, step.summary)


class TestAMisdeclaredDocumentPair:
    """``readme-pair`` under the four ways of getting the declaration wrong."""

    @pytest.mark.parametrize(
        ("label", "config", "token"), PAIR_MISDECLARATIONS, ids=lambda v: v
    )
    def test_it_is_told_apart_from_no_declaration(
        self, tmp_path: Path, label: str, config: str, token: str
    ) -> None:
        """Against the opt-out's own verdict, so rewording the skip cannot pass it."""
        opted_out = _step_readme_pair(_project(tmp_path / "none", ""))
        broken = _step_readme_pair(_project(tmp_path / "broken", config))
        assert _verdict(broken) != _verdict(opted_out), (
            f"{label}: a project that opted in is told it opted out"
        )

    @pytest.mark.parametrize(
        ("label", "config", "token"), PAIR_MISDECLARATIONS, ids=lambda v: v
    )
    def test_it_names_what_was_unusable(
        self, tmp_path: Path, label: str, config: str, token: str
    ) -> None:
        """The key or the path that could not be used is in the verdict, not in a log."""
        step = _step_readme_pair(_project(tmp_path, config))
        spoken = step.summary + " ".join(str(f["why"]) for f in step.findings)
        assert token in spoken, f"{label}: the verdict does not name {token!r}"

    @pytest.mark.parametrize(
        ("label", "config", "token"), PAIR_MISDECLARATIONS, ids=lambda v: v
    )
    def test_it_carries_the_count(
        self, tmp_path: Path, label: str, config: str, token: str
    ) -> None:
        """One declaration was written and one was unusable, and the line says both."""
        step = _step_readme_pair(_project(tmp_path, config))
        assert "1 entr(ies) declared, 1 unusable" in step.summary, label

    @pytest.mark.parametrize(
        ("label", "config", "token"), PAIR_MISDECLARATIONS, ids=lambda v: v
    )
    def test_the_report_counts_it_as_a_refusal(
        self, tmp_path: Path, label: str, config: str, token: str
    ) -> None:
        """The count the line prints is read off the report, not recomputed."""
        report = check_document_pairs(_project(tmp_path, config))
        assert report.declared is True, label
        assert report.entries_declared == 1, label
        assert len(report.refusals) == 1, label

    def test_a_usable_entry_beside_an_unusable_one_is_still_compared(
        self, tmp_path: Path
    ) -> None:
        """A refusal drops its own entry and nothing else."""
        root = _project(
            tmp_path,
            "document_pairs:\n"
            "  - source: README.ru.md\n"
            "    follower: README.md\n"
            "  - source: README.ru.md\n",
        )
        step = _step_readme_pair(root)
        assert step.passed is False
        assert "2 entr(ies) declared, 1 unusable" in step.summary
        assert "1 pair(s) held" in step.summary

    def test_a_project_that_declares_nothing_keeps_its_skip(self, tmp_path: Path) -> None:
        """The epic's binding constraint: an adopter who opted out is not judged."""
        step = _step_readme_pair(_project(tmp_path, ""))
        assert step.skipped is True
        assert "no document pair is declared" in step.summary

    def test_a_well_formed_pair_still_passes(self, tmp_path: Path) -> None:
        """Case A of the table keeps its verdict."""
        root = _project(
            tmp_path, "document_pairs:\n  - source: README.ru.md\n    follower: README.md\n"
        )
        step = _step_readme_pair(root)
        assert (step.passed, step.skipped) == (True, False)
        assert "1 pair(s) held" in step.summary

    def test_a_declaration_pointing_at_a_missing_file_still_fails(self, tmp_path: Path) -> None:
        """Case F keeps its verdict: a usable declaration naming an unreadable file."""
        root = _project(
            tmp_path, "document_pairs:\n  - source: NOPE.ru.md\n    follower: README.md\n"
        )
        step = _step_readme_pair(root)
        assert step.passed is False
        assert "UNREADABLE: NOPE.ru.md" in step.summary

    def test_an_unreadable_config_is_neither_a_declaration_nor_its_absence(
        self, tmp_path: Path
    ) -> None:
        """Whether the project opted in is unknown, and the line says so.

        It does not block: a config that will not parse may hold no
        ``document_pairs:`` key at all, and reddening a project that never opted
        in is the one thing this epic forbids. It is a WARN rather than a green,
        because the leg could not read the population it reports on.

        This is a statement about the STEP and not about ``beadloom ci``, which
        ends in ``infrastructure/scan_paths.py`` on a YAML syntax error before
        either leg runs (BDL-UX #287, filed rather than fixed here: the raise is
        outside this bead's declared scope). The branch is kept because folding
        it into absence would re-create the defect on the day #287 is closed.
        """
        root = _project(tmp_path, "")
        (root / ".beadloom" / "config.yml").write_text(
            "document_pairs: [\n", encoding="utf-8"
        )
        step = _step_readme_pair(root)
        assert step.passed is True
        assert step.not_verified is True
        assert "no document pair is declared" not in step.summary
        assert "could not be read" in step.summary


class TestAMisdeclaredIssueLog:
    """``issue-log`` under the same four ways — BDL-UX #270, the neighbouring leg."""

    @pytest.mark.parametrize(("label", "config", "token"), LOG_MISDECLARATIONS, ids=lambda v: v)
    def test_it_is_told_apart_from_no_declaration(
        self, tmp_path: Path, label: str, config: str, token: str
    ) -> None:
        opted_out = _step_issue_numbers(_project(tmp_path / "none", ""))
        broken = _step_issue_numbers(_project(tmp_path / "broken", config))
        assert _verdict(broken) != _verdict(opted_out), (
            f"{label}: a project that opted in is told it opted out"
        )

    @pytest.mark.parametrize(("label", "config", "token"), LOG_MISDECLARATIONS, ids=lambda v: v)
    def test_it_names_what_was_unusable(
        self, tmp_path: Path, label: str, config: str, token: str
    ) -> None:
        step = _step_issue_numbers(_project(tmp_path, config))
        spoken = step.summary + " ".join(str(f["why"]) for f in step.findings)
        assert token in spoken, f"{label}: the verdict does not name {token!r}"

    @pytest.mark.parametrize(("label", "config", "token"), LOG_MISDECLARATIONS, ids=lambda v: v)
    def test_it_carries_the_count(
        self, tmp_path: Path, label: str, config: str, token: str
    ) -> None:
        step = _step_issue_numbers(_project(tmp_path, config))
        assert "1 entr(ies) declared, 1 unusable" in step.summary, label

    @pytest.mark.parametrize(("label", "config", "token"), LOG_MISDECLARATIONS, ids=lambda v: v)
    def test_the_report_counts_it_as_a_refusal(
        self, tmp_path: Path, label: str, config: str, token: str
    ) -> None:
        report = check_issue_numbers(_project(tmp_path, config))
        assert report.declared is True, label
        assert report.entries_declared == 1, label
        assert len(report.refusals) == 1, label

    def test_a_project_that_declares_nothing_keeps_its_skip(self, tmp_path: Path) -> None:
        step = _step_issue_numbers(_project(tmp_path, ""))
        assert step.skipped is True
        assert "no issue log is declared" in step.summary

    def test_a_well_formed_declaration_still_runs_the_legs(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "issue_log:\n  path: ISSUES.md\n  ledger: issues\n")
        step = _step_issue_numbers(root)
        assert step.skipped is False
        assert "entr(ies) uniquely numbered" in step.summary

    def test_an_unreadable_config_is_neither_a_declaration_nor_its_absence(
        self, tmp_path: Path
    ) -> None:
        """The step's answer, which is not `beadloom ci`'s — see the twin above."""
        root = _project(tmp_path, "")
        (root / ".beadloom" / "config.yml").write_text("issue_log: [\n", encoding="utf-8")
        step = _step_issue_numbers(root)
        assert step.passed is True
        assert step.not_verified is True
        assert "no issue log is declared" not in step.summary
        assert "could not be read" in step.summary
