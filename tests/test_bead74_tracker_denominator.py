"""An epic the tracker export forgot is unverifiable, not compliant.

BDL-061 S5, bead `beadloom-mr2l.74` (findings BDL-061.18-2 and .18-3).
``beads_by_epic.get(key, ())`` made two different facts into one empty tuple:
*the export has no record of this epic* and *this epic's beads are all open*.
Both were skipped and only the second was an honest skip.

It drifts by ordinary use rather than by mistake. ``bd close`` writes only the
local database, so ``.beads/issues.jsonl`` and the tracker disagree until
somebody syncs the export deliberately — and until they do, the relation reports
zero and calls it a pass. Measured by `.18`: removing an epic's records took the
gate step from one finding to none with ``passed`` True and ``not_verified``
unchanged, because 52 epics declare no node and that one boolean was already
saturated for an unrelated reason. A saturated boolean carries no information;
the state gets its own channel here — a count, a list of names, a finding, and a
clause in the gate line.

The second finding is the same fact from the other side: ``docs spaces`` prefers
``bd list --all --json`` while the gate reads only the export, so the two
answered differently about one tree at one commit. Each now says which tracker it
read, and an epic neither can resolve is reported by both.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.application.doc_spaces import (
    FINDING_EPIC_NOT_IN_TRACKER,
    FINDING_NO_AS_IS,
    TRACKER_BD,
    TRACKER_EXPORT,
    TRACKER_UNREADABLE,
    check_spaces,
    read_epic_intents,
    read_tracker_export,
)
from beadloom.application.gate import _step_doc_spaces
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.doc_roots import default_doc_spaces, resolve_doc_spaces

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    import pytest

    from beadloom.application.doc_spaces import SpacesReport

#: Where the shipped flow writes an epic's planning documents.
_EPICS = ".claude/development/docs/features"


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _context(refs: str) -> str:
    return f"# CONTEXT\n\n## Goal\n\nShip it.\n\n## Related Files\n\n{refs}\n"


def _tracker(root: Path, records: Sequence[Mapping[str, str]]) -> None:
    lines = "\n".join(json.dumps(dict(r)) for r in records)
    _write(root, ".beads/issues.jsonl", lines + "\n")


def _index(root: Path, *, nodes: Mapping[str, str]) -> None:
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    for ref_id, source in nodes.items():
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, "component", ref_id, source),
        )
    conn.commit()
    conn.close()


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


class TestAnEpicTheExportForgotIsUnverifiable:
    """Three states where there was one: known, unknown, and no tracker at all."""

    def test_an_epic_the_export_does_not_name_is_counted_as_unknown(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(tmp_path, known={"billing"}, beads={"BDL-OTHER": ("closed",)})

        assert report.epics_without_bead_status == 1

    def test_it_is_named_and_not_only_counted(self, tmp_path: Path) -> None:
        """A count says how many; the summary has to be able to say which."""
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(tmp_path, known={"billing"}, beads={"BDL-OTHER": ("closed",)})

        assert report.epics_unknown_to_tracker == ("BDL-1",)

    def test_an_epic_whose_beads_are_open_is_neither_unknown_nor_named(
        self, tmp_path: Path
    ) -> None:
        """The control: an open epic is genuinely not yet a finding."""
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(
            tmp_path, known={"billing"}, beads={"BDL-1": ("open", "in_progress")}
        )

        assert report.epics_without_bead_status == 0
        assert report.epics_unknown_to_tracker == ()
        assert report.findings == ()

    def test_a_tracker_nobody_could_read_is_a_different_cause(self, tmp_path: Path) -> None:
        """One global cause, reported once, rather than a name per epic."""
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(tmp_path, known={"billing"}, beads=None)

        assert report.epics_without_bead_status == 1
        assert report.epics_unknown_to_tracker == ()
        assert report.findings == ()

    def test_the_reason_travels_with_the_epic_it_belongs_to(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        unknown = read_epic_intents(
            tmp_path,
            spaces=default_doc_spaces(),
            known_refs=frozenset({"billing"}),
            beads_by_epic={"BDL-OTHER": ("closed",)},
        )
        unreadable = read_epic_intents(
            tmp_path,
            spaces=default_doc_spaces(),
            known_refs=frozenset({"billing"}),
            beads_by_epic=None,
        )

        assert unknown[0].unknown_status_reason == TRACKER_EXPORT
        assert unreadable[0].unknown_status_reason == TRACKER_UNREADABLE


class TestDeletingRecordsDoesNotMakeTheCheckQuieter:
    """BDL-UX #174's equation, on the denominator nobody was watching.

    A declaring epic the tracker cannot resolve is reported as unverifiable, so
    the finding count does not fall when its records leave the export. An epic
    that declares nothing is NOT reported: it is already counted and named in
    the *declare no node* clause, and reporting it twice under two names would
    make the everyday line unreadable.
    """

    @staticmethod
    def _project(tmp_path: Path) -> Path:
        _write(tmp_path, f"{_EPICS}/PROJ-1/CONTEXT.md", _context("`billing`"))
        _write(tmp_path, f"{_EPICS}/PROJ-9/CONTEXT.md", _context("nothing here"))
        _index(tmp_path, nodes={"billing": "src/billing.py"})
        return tmp_path

    def test_the_finding_count_does_not_fall_when_the_export_forgets_an_epic(
        self, tmp_path: Path
    ) -> None:
        root = self._project(tmp_path)
        records = [
            {"title": "[PROJ-1.1][dev] ship it", "status": "closed"},
            {"title": "[PROJ-2.1][dev] elsewhere", "status": "closed"},
        ]
        _tracker(root, records)
        before = _step_doc_spaces(root)

        _tracker(root, records[1:])
        after = _step_doc_spaces(root)

        assert [f["rule"] for f in before.findings] == [FINDING_NO_AS_IS]
        assert [f["rule"] for f in after.findings] == [FINDING_EPIC_NOT_IN_TRACKER]

    def test_the_gate_line_names_the_epic_the_export_forgot(self, tmp_path: Path) -> None:
        root = self._project(tmp_path)
        _tracker(root, [{"title": "[PROJ-2.1][dev] elsewhere", "status": "closed"}])

        step = _step_doc_spaces(root)

        assert "PROJ-1" in step.summary
        assert step.not_verified is True

    def test_an_epic_that_declares_nothing_is_not_reported_twice(
        self, tmp_path: Path
    ) -> None:
        """PROJ-9 is unknown to the export in both states and is never a finding."""
        root = self._project(tmp_path)
        _tracker(root, [{"title": "[PROJ-1.1][dev] ship it", "status": "closed"}])

        step = _step_doc_spaces(root)

        assert not any("PROJ-9" in str(f.get("why", "")) for f in step.findings)

    def test_the_step_still_reports_the_relation_it_did_check(
        self, tmp_path: Path
    ) -> None:
        """The control: the epic the export DOES name is held against AS-IS."""
        root = self._project(tmp_path)
        _tracker(root, [{"title": "[PROJ-1.1][dev] ship it", "status": "closed"}])

        step = _step_doc_spaces(root)

        assert "1 node declaration(s)" in step.summary


class TestBothSurfacesSayWhichTrackerTheyRead:
    """One number, two sources — and each surface names the one it used.

    The gate reads the committed export because it must answer the same in a
    fresh CI checkout with no tracker installed; the command prefers ``bd``
    because a developer's local database is the more current of the two. They
    can therefore differ on one tree at one moment, and BDL-UX #171's shape is
    that a difference nobody prints is a difference nobody can act on.
    """

    def test_the_export_read_names_itself(self, tmp_path: Path) -> None:
        _tracker(tmp_path, [{"title": "[PROJ-1.1][dev] ship it", "status": "closed"}])

        read = read_tracker_export(tmp_path)

        assert read.source == TRACKER_EXPORT
        assert read.statuses == {"PROJ-1": ("closed",)}

    def test_an_absent_export_says_so_rather_than_answering_nothing(
        self, tmp_path: Path
    ) -> None:
        read = read_tracker_export(tmp_path)

        assert read.statuses is None
        assert read.source == TRACKER_UNREADABLE

    def test_the_gate_line_names_the_tracker_it_read(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/PROJ-1/CONTEXT.md", _context("`billing`"))
        _index(tmp_path, nodes={"billing": "src/billing.py"})
        _tracker(tmp_path, [{"title": "[PROJ-1.1][dev] ship it", "status": "closed"}])

        step = _step_doc_spaces(tmp_path)

        assert TRACKER_EXPORT in step.summary

    def test_the_command_names_the_tracker_it_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = json.loads(_cli(tmp_path, monkeypatch, closed="PROJ-1").output)

        assert payload["tracker_source"] == TRACKER_BD

    def test_the_command_and_the_gate_report_the_same_count_on_one_tree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`bd` knows PROJ-1 closed and the export does not; both report once."""
        cli = json.loads(_cli(tmp_path, monkeypatch, closed="PROJ-1").output)
        gate = _step_doc_spaces(tmp_path)

        assert cli["refs_checked"] == 1
        assert [f["rule"] for f in cli["findings"]] == [FINDING_NO_AS_IS]
        assert [f["rule"] for f in gate.findings] == [FINDING_EPIC_NOT_IN_TRACKER]
        assert len(gate.findings) == len(cli["findings"])


def _cli(root: Path, monkeypatch: pytest.MonkeyPatch, *, closed: str) -> object:
    """``docs spaces --json`` with ``bd`` answering that *closed*'s bead closed."""
    from click.testing import CliRunner

    from beadloom.services import bd_seam
    from beadloom.services.cli import main

    _write(root, f"{_EPICS}/PROJ-1/CONTEXT.md", _context("`billing`"))
    _index(root, nodes={"billing": "src/billing.py"})
    _tracker(root, [{"title": "[PROJ-2.1][dev] elsewhere", "status": "closed"}])

    class _Result:
        returncode = 0
        stdout = json.dumps([{"title": f"[{closed}.1][dev] ship it", "status": "closed"}])
        stderr = ""
        ok = True

    monkeypatch.setattr(bd_seam, "run_bd", lambda *a, **k: _Result())
    return CliRunner().invoke(main, ["docs", "spaces", "--json", "--project", str(root)])
