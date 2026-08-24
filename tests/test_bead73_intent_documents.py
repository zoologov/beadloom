"""A TO-BE directory that carries no intent document is counted, with its reason.

BDL-061 S5, bead `beadloom-mr2l.73` (finding BDL-061.18-1). `read_epic_intents`
derived epics from directories holding a TO-BE document and then required a
`CONTEXT.md` or `BRIEF.md` inside. A directory with neither was appended to
nothing — absent from ``epics``, from ``unresolved_epics`` and from every NOT
CHECKED line — while its documents stayed in the TO-BE population. One report
stated two incompatible sizes for one tree: 61 directories hold intent on this
repository and 57 became epics.

Three routes reached that same drop, and each is closed here:

1. **No intent document at all.** Three `SUMMARY.md`-only feature directories,
   and `.claude/development` itself — which holds `ROADMAP.md` and the issue log,
   the documents `beadloom-mr2l.72` is about.
2. **An intent document that cannot be decoded.** `_read` answered ``None`` and
   the caller continued, so a cp1251 planning document removed its epic instead
   of reporting itself. That is the shape `.68` gave the ledger.
3. **A hardcoded pair of file names** while every root around them is
   configuration. TRUE HERE IS NOT TRUE: an adopter whose planning document is
   named anything else lost 100% of its epics and the gate printed a plausible
   `0 of 0 epic(s) with closed beads`.

The fix has the shape `.17` already applied one layer up, where an epic whose
CONTEXT carries no *Related Files* heading became unresolved rather than absent:
a directory with no readable intent document is an unresolved epic carrying its
own reason, never an absence.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml

from beadloom.application.doc_spaces import (
    FINDING_INTENT_UNREADABLE,
    UNRESOLVED_NO_INTENT_DOCUMENT,
    UNRESOLVED_NO_NODE_DECLARED,
    UNRESOLVED_UNREADABLE_INTENT,
    check_spaces,
)
from beadloom.application.gate import _step_doc_spaces
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.doc_roots import (
    DEFAULT_INTENT_DOCUMENTS,
    SPACE_TO_BE,
    resolve_doc_spaces,
)
from tests.adopter_project import typescript_project

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from beadloom.application.doc_spaces import SpacesReport

#: Where the shipped flow writes an epic's planning documents.
_EPICS = ".claude/development/docs/features"


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _config(root: Path, block: Mapping[str, object]) -> None:
    _write(root, ".beadloom/config.yml", yaml.safe_dump({"doc_roots": dict(block)}))


def _context(refs: str) -> str:
    return f"# CONTEXT\n\n## Goal\n\nShip it.\n\n## Related Files\n\n{refs}\n"


def _report(
    root: Path,
    *,
    known: set[str] | None = None,
    beads: Mapping[str, tuple[str, ...]] | None = None,
) -> SpacesReport:
    return check_spaces(
        root,
        spaces=resolve_doc_spaces(root),
        known_refs=frozenset(known or ()),
        documented_refs=frozenset(known or ()),
        declared_doc_paths=frozenset(),
        beads_by_epic=beads,
    )


class TestADirectoryWithNoIntentDocumentIsStillAnEpic:
    """Route 1: the drop that leaves no trace in any field of the report."""

    def test_it_is_counted_and_named_unresolved(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/SUMMARY.md", "# SUMMARY\n\nwhat happened.\n")

        report = _report(tmp_path, beads={"BDL-1": ("closed",)})

        assert report.epics == 1
        assert report.unresolved_epics == ("BDL-1",)

    def test_it_carries_its_own_reason(self, tmp_path: Path) -> None:
        """"Unresolved" covers two different situations and must not blur them."""
        _write(tmp_path, f"{_EPICS}/BDL-1/SUMMARY.md", "# SUMMARY\n\nwhat happened.\n")
        _write(tmp_path, f"{_EPICS}/BDL-2/CONTEXT.md", "# CONTEXT\n\n## Goal\n\nShip.\n")

        report = _report(tmp_path, beads={"BDL-1": ("closed",), "BDL-2": ("closed",)})

        assert dict(report.unresolved_reasons) == {
            "BDL-1": UNRESOLVED_NO_INTENT_DOCUMENT,
            "BDL-2": UNRESOLVED_NO_NODE_DECLARED,
        }

    def test_it_is_not_a_finding(self, tmp_path: Path) -> None:
        """A directory that is not an epic is not thereby a defect.

        `.claude/development` holds the ROADMAP and the issue log and is not a
        feature; reporting it would make the everyday line a list of things
        nobody intends to change. It is counted and named, which is the claim.
        """
        _write(tmp_path, f"{_EPICS}/BDL-1/SUMMARY.md", "# SUMMARY\n\nwhat happened.\n")

        report = _report(tmp_path, beads={"BDL-1": ("closed",)})

        assert report.findings == ()

    def test_the_epic_that_does_declare_is_unaffected(self, tmp_path: Path) -> None:
        """The control: widening the population does not move the relation."""
        _write(tmp_path, f"{_EPICS}/BDL-1/SUMMARY.md", "# SUMMARY\n\nwhat happened.\n")
        _write(tmp_path, f"{_EPICS}/BDL-2/CONTEXT.md", _context("`billing`"))

        report = _report(
            tmp_path, known={"billing"}, beads={"BDL-2": ("closed",)}
        )

        assert report.refs_checked == 1
        assert report.epics == 2


class TestAnUndecodableIntentDocumentReportsItself:
    """Route 2: a decode failure that removed an epic instead of naming one."""

    def test_the_epic_is_counted_rather_than_dropped(self, tmp_path: Path) -> None:
        path = tmp_path / _EPICS / "BDL-1" / "CONTEXT.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes("# CONTEXT\n\n## Related Files\n\n`биллинг`\n".encode("cp1251"))

        report = _report(tmp_path, beads={"BDL-1": ("closed",)})

        assert report.epics == 1
        assert report.unresolved_reasons["BDL-1"] == UNRESOLVED_UNREADABLE_INTENT

    def test_the_document_is_reported_as_the_defect_it_is(self, tmp_path: Path) -> None:
        """Unlike a missing document, an unreadable one IS a defect to fix."""
        path = tmp_path / _EPICS / "BDL-1" / "CONTEXT.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes("# CONTEXT\n\n## Related Files\n\n`биллинг`\n".encode("cp1251"))

        report = _report(tmp_path, beads={"BDL-1": ("closed",)})

        assert [f.rule for f in report.findings] == [FINDING_INTENT_UNREADABLE]
        assert report.findings[0].path.endswith("BDL-1/CONTEXT.md")

    def test_a_decodable_document_is_not_reported(self, tmp_path: Path) -> None:
        """The control: the handler is as wide as the call and no wider."""
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(tmp_path, known={"billing"}, beads={"BDL-1": ("closed",)})

        assert report.findings == ()


class TestTheIntentDocumentNamesAreConfiguration:
    """Route 3: TRUE HERE IS NOT TRUE, on a project that is not this one."""

    def test_the_shipped_names_are_the_flow_s_own(self) -> None:
        assert DEFAULT_INTENT_DOCUMENTS == ("CONTEXT.md", "BRIEF.md")

    def test_an_adopter_whose_document_has_another_name_is_not_zero_epics(
        self, tmp_path: Path
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _config(project.root, {"to_be": {"roots": ["design/*/*.md"]}})
        _write(project.root, "design/ORD-4/OVERVIEW.md", _context("`checkout`"))

        report = _report(project.root, known={"checkout"}, beads={"ORD-4": ("closed",)})

        assert report.epics == 1

    def test_declaring_the_name_makes_its_declarations_readable(
        self, tmp_path: Path
    ) -> None:
        """Counting the epic is honest; reading its declaration is the remedy."""
        project = typescript_project(tmp_path / "orders-web")
        _config(
            project.root,
            {"to_be": {"roots": ["design/*/*.md"], "intent_documents": ["OVERVIEW.md"]}},
        )
        _write(project.root, "design/ORD-4/OVERVIEW.md", _context("`checkout`"))

        spaces = resolve_doc_spaces(project.root)
        report = _report(project.root, known={"checkout"}, beads={"ORD-4": ("closed",)})

        assert spaces.intent_documents == ("OVERVIEW.md",)
        assert report.refs_checked == 1
        assert report.unresolved_epics == ()

    def test_a_declared_name_replaces_the_shipped_pair_rather_than_joining_it(
        self, tmp_path: Path
    ) -> None:
        """A project's convention is a statement, not an addition to ours."""
        _config(tmp_path, {"to_be": {"intent_documents": ["OVERVIEW.md"]}})
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(tmp_path, known={"billing"}, beads={"BDL-1": ("closed",)})

        assert report.refs_checked == 0
        assert report.unresolved_reasons["BDL-1"] == UNRESOLVED_NO_INTENT_DOCUMENT


class TestTheSurfacesSayWhyAnEpicIsUnresolved:
    """A count of 56 says nothing about the four that are a different case."""

    @staticmethod
    def _project(root: Path) -> Path:
        _write(root, f"{_EPICS}/PROJ-1/CONTEXT.md", "# CONTEXT\n\n## Goal\n\nShip.\n")
        _write(root, f"{_EPICS}/PROJ-2/SUMMARY.md", "# SUMMARY\n")
        (root / ".beadloom").mkdir(parents=True, exist_ok=True)
        conn = open_db(root / ".beadloom" / "beadloom.db")
        create_schema(conn)
        conn.commit()
        conn.close()
        _write(root, ".beads/issues.jsonl", "")
        return root

    def test_the_gate_line_counts_the_directories_that_carry_no_intent_document(
        self, tmp_path: Path
    ) -> None:
        step = _step_doc_spaces(self._project(tmp_path))

        assert "2 epic(s) declare no node" in step.summary
        assert "1 carry no readable intent document" in step.summary

    def test_the_json_carries_the_reason_for_each_unresolved_epic(
        self, tmp_path: Path
    ) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        root = self._project(tmp_path)

        result = CliRunner().invoke(
            main, ["docs", "spaces", "--json", "--project", str(root)]
        )

        assert json.loads(result.output)["unresolved_reasons"] == {
            "PROJ-1": UNRESOLVED_NO_NODE_DECLARED,
            "PROJ-2": UNRESOLVED_NO_INTENT_DOCUMENT,
        }


class TestTheTwoSizesOfOneTreeAgree:
    """The report stated two sizes for one tree; here they are held together."""

    def test_every_directory_holding_a_to_be_document_is_an_epic(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))
        _write(tmp_path, f"{_EPICS}/BDL-2/SUMMARY.md", "# SUMMARY\n")
        _write(tmp_path, ".claude/development/ROADMAP.md", "# ROADMAP\n")

        spaces = resolve_doc_spaces(tmp_path)
        directories = {p.parent for p in spaces.documents_in(tmp_path, SPACE_TO_BE)}
        report = _report(tmp_path, known={"billing"}, beads={})

        assert len(directories) == 3
        assert report.epics == len(directories)

    def test_the_buckets_still_partition_the_epics(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))
        _write(tmp_path, f"{_EPICS}/BDL-2/SUMMARY.md", "# SUMMARY\n")

        report = _report(tmp_path, known={"billing"}, beads={})

        assert report.epics_declaring_nodes + report.epics_declaring_nothing == report.epics
