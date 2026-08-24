"""S5 verification: is the population honest, and can the relation report zero?

BDL-061 S5 (`beadloom-mr2l.18`). `.17` shipped a claim that is deliberately a
**relation between two artifacts** rather than a flag on one, and a relation
check is the easiest vacuous check this epic has built: it can quietly have
nothing to relate. So this file attacks the population rather than the arithmetic.

Four questions, one group of classes each.

**Are the numbers recomputable?** Every denominator `docs spaces` prints is
recounted here from the filesystem and the tracker export by code that shares no
function with the one under test. Measured on this repository: to_be 190 / as_is
93 / working 55, 17 node declarations, 5 declaring epics, 37 of 57 with closed
beads, 52 unresolved. All five recount exactly.

**What is still excluded?** `.17` caught its denominator shrinking once, honestly,
and fixed it — an epic whose CONTEXT has no *Related Files* heading is now
counted as unresolved rather than dropped. Two shrinks below it survive: a TO-BE
directory that carries no `CONTEXT.md`/`BRIEF.md` at all leaves every count in
the report (61 directories hold intent here, 57 become epics), and an epic the
tracker export does not name is indistinguishable from one whose beads are open.
The second is BDL-UX #174's equation on the tracker: deleting records makes the
check quieter.

**Can a wrong WORKING declaration hide?** The exemption is a declaration and its
two failure modes are detected — where the two readers agree on what a path is.
They do not always: `check_sync` classifies a *docs-dir-relative* path and
`check_spaces` a *project-relative* one, so a root-declared exemption reaches
freshness and never reaches the report that exists to catch it.

**Does an exemption say so?** `_sync_summary`'s own docstring forbids a count
that means nothing, and the new `exempt` verdict is in none of its arithmetic.

Findings are asserted as they SHOULD behave and marked `xfail(strict=True)`: the
prediction is executable, and a fix reddens this suite instead of passing in
silence. Every finding is measured beside a neighbouring test that passes, so no
`xfail` here can be an artefact of a broken fixture (TESTS MUST BITE).
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner, Result

from beadloom.application.doc_spaces import (
    FINDING_NO_AS_IS,
    FINDING_WORKING_CONTRADICTED,
    SpacesReport,
    beads_by_epic,
    check_spaces,
    read_epic_intents,
)
from beadloom.application.gate import _step_doc_spaces, _sync_summary
from beadloom.doc_sync.engine import STATUS_EXEMPT, STATUS_OK, check_sync
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.doc_roots import (
    DEFAULT_KINDS,
    DEFAULT_ROOTS,
    SPACE_AS_IS,
    SPACE_TO_BE,
    SPACE_WORKING,
    default_doc_spaces,
    document_kind,
    path_matches,
    resolve_doc_spaces,
)
from tests.adopter_project import typescript_project

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Where the shipped flow writes an epic's planning documents.
_EPICS = ".claude/development/docs/features"


# --------------------------------------------------------------------------- #
# Fixtures and factories
# --------------------------------------------------------------------------- #


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
    documented: set[str] | None = None,
    declared: set[str] | None = None,
    beads: Mapping[str, tuple[str, ...]] | None = None,
) -> SpacesReport:
    """``check_spaces`` with the graph supplied as data, never as a database."""
    return check_spaces(
        root,
        spaces=resolve_doc_spaces(root),
        known_refs=frozenset(known or ()),
        documented_refs=frozenset(documented or ()),
        declared_doc_paths=frozenset(declared or ()),
        beads_by_epic=beads,
    )


def _db(root: Path, *, nodes: Mapping[str, str], docs: Mapping[str, str]) -> sqlite3.Connection:
    """A minimal index: ``ref_id -> source`` and ``ref_id -> declared document``."""
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    for ref_id, source in nodes.items():
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, "component", ref_id, source),
        )
    for ref_id, declared_path in docs.items():
        conn.execute(
            "INSERT INTO declared_docs (declared_path, doc_path, ref_id) VALUES (?, ?, ?)",
            (declared_path, declared_path.removeprefix("docs/"), ref_id),
        )
    conn.commit()
    return conn


def _pair(
    conn: sqlite3.Connection,
    *,
    doc_path: str,
    code_path: str,
    ref_id: str,
    code_hash: str = "baseline",
) -> None:
    """One ``sync_state`` row, spelled the way the indexer spells one.

    ``doc_path`` is relative to the **docs directory**, because that is what
    :func:`beadloom.doc_sync.doc_indexer.index_docs` writes, and a fixture whose
    path convention differs from the indexer's proves the fixture.
    """
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_path, code_path, ref_id, code_hash, "baseline", "2026-01-01", "ok"),
    )
    conn.commit()


def _tracker(root: Path, records: Sequence[Mapping[str, str]]) -> None:
    lines = "\n".join(json.dumps(dict(r)) for r in records)
    _write(root, ".beads/issues.jsonl", lines + "\n")


def _repo_beads() -> dict[str, tuple[str, ...]]:
    """This repository's own tracker export, grouped by epic key."""
    text = (REPO_ROOT / ".beads" / "issues.jsonl").read_text(encoding="utf-8")
    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    return beads_by_epic(records)


def _repo_report() -> SpacesReport:
    return _report(
        REPO_ROOT,
        known=_repo_known_refs(),
        documented=_repo_known_refs(),
        beads=_repo_beads(),
    )


def _repo_known_refs() -> set[str]:
    """Ref ids read from the committed graph YAML, not from an index.

    The database is a build artifact whose freshness is the thing under test
    elsewhere; the YAML is the declaration.
    """
    refs: set[str] = set()
    for path in (REPO_ROOT / ".beadloom" / "_graph").glob("*.yml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for node in data.get("nodes", []) or []:
            if isinstance(node, dict) and isinstance(node.get("ref_id"), str):
                refs.add(node["ref_id"])
    return refs


def _independent_population(root: Path) -> dict[str, int]:
    """Recount the three spaces without calling anything under test.

    Kind first, then root, spelled out here rather than imported so a defect in
    the classifier cannot agree with itself.
    """
    kinds = {kind.upper(): space for space, ks in DEFAULT_KINDS.items() for kind in ks}
    found: dict[str, set[Path]] = {}
    for declared, patterns in DEFAULT_ROOTS.items():
        found[declared] = {p for pat in patterns for p in root.glob(pat) if p.is_file()}
    counts = dict.fromkeys(DEFAULT_ROOTS, 0)
    everything = {p for paths in found.values() for p in paths}
    for path in everything:
        stem = path.name.rpartition(".")[0].upper()
        space: str | None = kinds.get(stem)
        if space is None:
            space = next((s for s, paths in found.items() if path in paths), None)
        if space is not None:
            counts[space] += 1
    return counts


# --------------------------------------------------------------------------- #
# Is the population honest?
# --------------------------------------------------------------------------- #


class TestTheDenominatorsAreRecomputable:
    """Every number the report prints, recounted by code that is not the code.

    A relation check reports a clean result about the work it looked at; the
    number that matters is how much work that was. `.17` reported these figures
    and this class is the independent half of A GREEN COUNT IS NOT A CHECKED
    COUNT — the count is not disputed, the denominator behind it is.
    """

    def test_the_three_populations_match_an_independent_count(self) -> None:
        report = _repo_report()

        assert dict(report.populations) == _independent_population(REPO_ROOT)

    def test_the_populations_are_not_trivially_zero(self) -> None:
        """The recount above is worthless if both sides are empty."""
        counts = _independent_population(REPO_ROOT)

        assert counts[SPACE_TO_BE] > 100
        assert counts[SPACE_AS_IS] > 50
        assert counts[SPACE_WORKING] > 10

    def test_the_declaring_and_unresolved_buckets_partition_the_epics(self) -> None:
        """No epic may be in neither bucket — that is where a denominator hides."""
        report = _repo_report()

        assert report.epics_declaring_nodes + report.epics_declaring_nothing == report.epics

    def test_the_declarations_checked_are_recountable_from_the_documents(self) -> None:
        """``refs_checked`` recounted from the CONTEXT sections and the export."""
        beads = _repo_beads()
        known = _repo_known_refs()
        expected = 0
        for directory in sorted((REPO_ROOT / _EPICS).iterdir()):
            document = directory / "CONTEXT.md"
            if not document.is_file():
                document = directory / "BRIEF.md"
            if not document.is_file():
                continue
            if not any(s == "closed" for s in beads.get(directory.name, ())):
                continue
            expected += len(_declared_in_section(document.read_text(encoding="utf-8"), known))

        assert _repo_report().refs_checked == expected

    def test_the_epics_with_closed_beads_are_recountable_from_the_export(self) -> None:
        beads = _repo_beads()
        report = _repo_report()
        closed = [key for key, statuses in beads.items() if "closed" in statuses]

        assert report.epics_with_closed_beads == sum(
            1 for key in closed if (REPO_ROOT / _EPICS / key).is_dir()
        )

    def test_the_relation_reports_that_it_related_something(self) -> None:
        """The premise of every count above: it is not a vacuous run."""
        assert _repo_report().relation_checked is True


def _declared_in_section(text: str, known: set[str]) -> list[str]:
    """Backticked known refs under a related-files heading — recounted here."""
    import re

    refs: list[str] = []
    inside = False
    for line in text.splitlines():
        heading = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
        if heading is not None:
            title = heading.group(1).lower()
            inside = any(w in title for w in ("related file", "related code", "primary ref"))
            continue
        if not inside:
            continue
        for match in re.finditer(r"`([A-Za-z0-9][A-Za-z0-9._-]*)`", line):
            if match.group(1) in known and match.group(1) not in refs:
                refs.append(match.group(1))
    return refs


# --------------------------------------------------------------------------- #
# FINDING .18-1 — a directory that carries no intent document leaves the report
# --------------------------------------------------------------------------- #


class TestADirectoryThatHoldsIntentReachesTheDenominator:
    """`.17` fixed the shrink one layer up; this is the layer below it.

    An epic whose CONTEXT carries no *Related Files* heading is now counted and
    named unresolved. An epic whose directory carries no ``CONTEXT.md`` or
    ``BRIEF.md`` at all is in no count whatsoever — its documents are in the
    TO-BE population, its directory is in none of ``epics``,
    ``unresolved_epics`` or a NOT CHECKED line. The two counts in one report
    disagree about the same tree.
    """

    def test_a_directory_with_an_intent_document_is_an_epic(self) -> None:
        """The control: the mechanism works when the file name is the one wired in."""
        root = _tmp()
        _write(root, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(root, known={"billing"}, beads={"BDL-1": ("closed",)})

        assert report.epics == 1

    def test_a_directory_whose_documents_name_no_intent_file_is_still_an_epic(self) -> None:
        """FINDING BDL-061.18-1, closed by `beadloom-mr2l.73`.

        A TO-BE directory carrying no `CONTEXT.md` and no `BRIEF.md` was dropped
        from every count in the report — not `epics`, not `unresolved_epics`,
        not a NOT CHECKED line — while its documents stayed in the TO-BE
        population, so one report stated two incompatible sizes for one tree.
        Measured here: 61 directories held a TO-BE document and 57 became epics;
        `.claude/development` and three `SUMMARY.md`-only feature directories
        were invisible. It is an unresolved epic with its own reason now, which
        is the shape `.17` applied one layer up.
        """
        root = _tmp()
        _write(root, f"{_EPICS}/BDL-1/SUMMARY.md", "# SUMMARY\n\nwhat happened.\n")

        report = _report(root, beads={"BDL-1": ("closed",)})

        assert report.epics == 1
        assert report.unresolved_epics == ("BDL-1",)

    def test_an_undecodable_intent_document_is_a_finding_and_not_a_disappearance(self) -> None:
        """FINDING BDL-061.18-1 through the decode handler, closed by `.73`.

        `_read` answers `None` for a document it cannot decode and the caller
        continued, so an epic whose CONTEXT.md is cp1251 was not an epic at all.
        It is now reported as `intent_document_unreadable` — a finding about the
        document, which is the shape `.68` gave the ledger.
        """
        root = _tmp()
        path = root / _EPICS / "BDL-1" / "CONTEXT.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes("# CONTEXT\n\n## Related Files\n\n`биллинг`\n".encode("cp1251"))

        report = _report(root, beads={"BDL-1": ("closed",)})

        assert report.epics == 1

    def test_an_adopter_whose_intent_document_has_another_name_is_not_zero_epics(self) -> None:
        """FINDING BDL-061.18-1 on an adopter's tree, closed by `.73`.

        The intent document names were hardcoded to `CONTEXT.md`/`BRIEF.md`
        while every root around them is configuration. TRUE HERE IS NOT TRUE: an
        adopter whose planning document is named otherwise had 100% of its epics
        vanish and the gate printed a plausible `0 of 0 epic(s) with closed
        beads`. The directory is counted whatever its documents are called, and
        the names moved into `doc_roots.to_be.intent_documents` beside the kinds
        they are drawn from.
        """
        root = _tmp()
        project = typescript_project(root / "orders-web")
        _config(project.root, {"to_be": {"roots": ["design/*/*.md"]}})
        _write(project.root, "design/ORD-4/OVERVIEW.md", _context("`checkout`"))

        report = _report(project.root, known={"checkout"}, beads={"ORD-4": ("closed",)})

        assert report.epics == 1

    def test_every_directory_holding_a_to_be_document_is_counted_here(self) -> None:
        """FINDING BDL-061.18-1 on the real tree, closed by `beadloom-mr2l.73`.

        61 directories contribute a document to the TO-BE population and 57 were
        counted as epics; the four that were not appeared in no field of the
        report and in no line of the gate summary. The two sizes are one size
        now, and this test is the one that holds them together.
        """
        spaces = resolve_doc_spaces(REPO_ROOT)
        directories = {p.parent for p in spaces.documents_in(REPO_ROOT, SPACE_TO_BE)}

        assert _repo_report().epics == len(directories)


#: Roots handed out by :func:`_tmp`, removed after each test by the fixture
#: below. A factory rather than the ``tmp_path`` fixture because several helpers
#: here are static and take no fixtures.
_HANDED_OUT: list[Path] = []


def _tmp() -> Path:
    """A throwaway project root, removed when the test that asked for it ends."""
    path = Path(tempfile.mkdtemp(prefix="beadloom-s5-"))
    _HANDED_OUT.append(path)
    return path


@pytest.fixture(autouse=True)
def _remove_handed_out_roots() -> Iterator[None]:
    """Keep the tests independent of each other and of the machine's temp dir."""
    yield
    while _HANDED_OUT:
        shutil.rmtree(_HANDED_OUT.pop(), ignore_errors=True)


# --------------------------------------------------------------------------- #
# FINDING .18-2 — the tracker export is a denominator nobody watches
# --------------------------------------------------------------------------- #


class TestAnEpicTheTrackerDoesNotNameIsNotAnEpicWithOpenBeads:
    """`beads_by_epic.get(key, ())` conflates two different facts.

    "The export has no record of this epic" and "this epic's beads are all open"
    produce the same empty tuple, so an epic that leaves the export leaves the
    checked population and nothing says so. Nothing an editor deletes may make a
    check quieter (BDL-UX #174, this epic's `.57`), and `bd close` writes only
    the local database, so the export drifts by ordinary use rather than by
    sabotage.
    """

    def test_an_epic_whose_beads_are_open_is_not_checked_and_that_is_correct(self) -> None:
        """The control: an open epic is genuinely not yet a finding."""
        root = _tmp()
        _write(root, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(root, known={"billing"}, beads={"BDL-1": ("open", "in_progress")})

        assert report.findings == ()
        assert report.refs_checked == 0

    def test_no_tracker_at_all_is_reported_rather_than_assumed(self) -> None:
        """The control for the other direction: a whole missing tracker is named."""
        root = _tmp()
        _write(root, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(root, known={"billing"}, beads=None)

        assert report.epics_without_bead_status == 1

    def test_an_epic_missing_from_the_export_is_counted_as_unknown(self) -> None:
        """FINDING BDL-061.18-2, closed by `beadloom-mr2l.74`.

        An epic the tracker export does not name was indistinguishable from one
        whose beads are all open: both the empty tuple, both skipped, and only
        the second an honest skip. Measured on this repository: 20 of 57 epic
        directories were unknown to `.beads/issues.jsonl`, and every one of the
        37 the export DID name had a closed bead — so `37 of 57 epic(s) with
        closed beads` was really `37 of 57 epics the export still names`. It is
        now `None` with its reason, counted in `epics_without_bead_status`.
        """
        root = _tmp()
        _write(root, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))

        report = _report(root, known={"billing"}, beads={"BDL-OTHER": ("closed",)})

        assert report.epics_without_bead_status == 1

    def test_this_repository_names_the_epics_its_export_forgot(self) -> None:
        """FINDING BDL-061.18-2 on the real tree, closed by `.74` and `.73`.

        23 of the 60 directories under the feature root are absent from the
        tracker export and not one was reported as unverifiable. `.74` gave the
        state its own channel and `.73` widened the population to every
        directory holding intent, which is why this leg needed both.
        """
        beads = _repo_beads()
        directories = [p.name for p in sorted((REPO_ROOT / _EPICS).iterdir()) if p.is_dir()]
        forgotten = [name for name in directories if name not in beads]

        assert _repo_report().epics_without_bead_status >= len(forgotten)

    def test_deleting_an_epics_records_does_not_make_the_gate_quieter(self) -> None:
        """FINDING BDL-061.18-2 at the gate, closed by `beadloom-mr2l.74`.

        Removing an epic's records from `.beads/issues.jsonl` took the doc-spaces
        step from one finding to none with `passed` True and `not_verified`
        unchanged — it was already True for an unrelated reason (52 epics
        declare no node), so the one honest signal was saturated and carried no
        information about the deletion. The state has its own channel now: the
        epic is named in the summary and, because it declares a node, reported
        as `epic_not_in_tracker`.
        """
        root = _tmp()
        _write(root, f"{_EPICS}/PROJ-1/CONTEXT.md", _context("`billing`"))
        # A second epic that declares nothing, so `not_verified` is already True
        # before the deletion — which is the state this repository is in, and the
        # reason the one honest signal carries no information about it.
        _write(root, f"{_EPICS}/PROJ-9/CONTEXT.md", _context("nothing here"))
        _db(root, nodes={"billing": "src/billing.py"}, docs={})
        records = [
            {"title": "[PROJ-1.1][dev] ship it", "status": "closed"},
            {"title": "[PROJ-2.1][dev] elsewhere", "status": "closed"},
        ]
        _tracker(root, records)
        before = _step_doc_spaces(root)

        _tracker(root, records[1:])
        after = _step_doc_spaces(root)

        assert before.not_verified is True
        assert len(before.findings) == 1
        assert "PROJ-1" in after.summary or len(after.findings) == len(before.findings)


# --------------------------------------------------------------------------- #
# FINDING .18-3 — one number, two sources of truth
# --------------------------------------------------------------------------- #


class TestTheCommandAndTheGateReadOneTracker:
    """`docs spaces` prefers ``bd``; the gate step reads only the export.

    Two readers of one fact is the shape BDL-UX #171 records, and here they can
    disagree on the same tree at the same moment: one prints a finding the other
    does not have.
    """

    @staticmethod
    def _project() -> Path:
        root = _tmp()
        _write(root, f"{_EPICS}/PROJ-1/CONTEXT.md", _context("`billing`"))
        _db(root, nodes={"billing": "src/billing.py"}, docs={})
        _tracker(root, [{"title": "[PROJ-2.1][dev] elsewhere", "status": "closed"}])
        return root

    @staticmethod
    def _cli(root: Path, monkeypatch: pytest.MonkeyPatch, payload: list[dict[str, str]]) -> Result:
        from beadloom.services import bd_seam
        from beadloom.services.cli import main

        class _Result:
            returncode = 0
            stdout = json.dumps(payload)
            stderr = ""
            ok = True

        monkeypatch.setattr(bd_seam, "run_bd", lambda *a, **k: _Result())
        runner = CliRunner()
        return runner.invoke(main, ["docs", "spaces", "--json", "--project", str(root)])

    def test_the_command_reads_the_tracker_binary_when_it_answers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The premise: ``bd`` is preferred and its answer reaches the report."""
        root = self._project()

        result = self._cli(
            root, monkeypatch, [{"title": "[PROJ-1.1][dev] ship it", "status": "closed"}]
        )

        assert result.exit_code == 0
        assert json.loads(result.output)["refs_checked"] == 1

    def test_the_command_and_the_gate_agree_on_one_tree(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FINDING BDL-061.18-3, closed by `beadloom-mr2l.74`.

        `docs spaces` prefers `bd list --all --json` and `_step_doc_spaces` reads
        only `.beads/issues.jsonl`, so the two answered differently about one
        tree: 17 declarations and one finding against 4 and none, at one commit.
        They still read different trackers — deliberately, since the gate must
        answer the same in a fresh CI checkout — and each now says which, and an
        epic its tracker cannot resolve is reported rather than skipped. So the
        two report the same number of things needing attention.
        """
        root = self._project()

        cli = json.loads(
            self._cli(
                root, monkeypatch, [{"title": "[PROJ-1.1][dev] ship it", "status": "closed"}]
            ).output
        )
        gate = _step_doc_spaces(root)

        assert cli["refs_checked"] == 1
        assert len(gate.findings) == len(cli["findings"])


# --------------------------------------------------------------------------- #
# FINDING .18-4 — a WORKING declaration that hides between two readers
# --------------------------------------------------------------------------- #


class TestAWrongWorkingDeclarationIsDetectable:
    """The exemption is a declaration, and a declaration can be wrong.

    Two detectors exist for that — an exemption that excuses nothing, and one
    the graph contradicts — and both work where the two readers agree on what a
    path is. ``check_sync`` is handed a **docs-dir-relative** path (the shape
    ``index_docs`` writes) and ``check_spaces`` a **project-relative** one. Kind
    agrees on both spellings because a stem has no prefix; roots do not.
    """

    @staticmethod
    def _stale_project(root: Path, doc_rel: str) -> sqlite3.Connection:
        """A project whose one declared document is stale against its code."""
        _write(root, "src/billing.py", "def charge() -> None:\n    return None\n")
        _write(root, f"docs/{doc_rel}", "# billing\n")
        conn = _db(
            root,
            nodes={"billing": "src/billing.py"},
            docs={"billing": f"docs/{doc_rel}"},
        )
        _pair(conn, doc_path=doc_rel, code_path="src/billing.py", ref_id="billing")
        return conn

    def test_a_kind_declared_exemption_silences_a_pair_and_is_reported(self) -> None:
        """The control, and it passes: the detector works on the kind route."""
        root = _tmp()
        conn = self._stale_project(root, "ACTIVE.md")

        rows = check_sync(conn, root)
        report = _report(root, declared={"docs/ACTIVE.md"}, beads={})

        assert [r["status"] for r in rows if r["doc_path"] == "ACTIVE.md"] == [STATUS_EXEMPT]
        assert [f.rule for f in report.findings] == [FINDING_WORKING_CONTRADICTED]

    def test_a_document_of_no_declared_kind_is_held_against_its_code(self) -> None:
        """The other control: without a declaration nothing is excused."""
        root = _tmp()
        conn = self._stale_project(root, "guides/ci.md")

        rows = check_sync(conn, root)

        assert [r["status"] for r in rows if r["doc_path"] == "guides/ci.md"] == ["stale"]

    def test_a_working_root_spelled_like_its_neighbours_reaches_freshness(self) -> None:
        """FINDING BDL-061.18-4, closed by `beadloom-mr2l.75`.

        A WORKING root spelled the way every other root in `doc_roots` is
        spelled — project-relative — had no effect on freshness, because
        `check_sync` classified the docs-dir-relative path `guides/ci.md`
        against the pattern `docs/guides/*.md`. One configuration string meant
        two different things depending on which reader held it. It now reaches
        freshness through `DocSpaces.project_path`.
        """
        root = _tmp()
        _config(
            root,
            {
                "working": {
                    "roots": ["docs/guides/*.md"],
                    "exempt_from_freshness": True,
                    "reason": "generated release notes, regenerated per tag",
                }
            },
        )
        conn = self._stale_project(root, "guides/ci.md")

        rows = check_sync(conn, root)

        assert [r["status"] for r in rows if r["doc_path"] == "guides/ci.md"] == [STATUS_EXEMPT]

    def test_a_root_declared_exemption_that_silences_a_pair_is_contradicted(self) -> None:
        """FINDING BDL-061.18-4, the dangerous direction, closed by `.75`.

        The docs-dir-relative spelling silenced freshness and the check built to
        catch a wrong WORKING declaration could not see it: `working_documents`
        classified `docs/guides/ci.md` project-relative, found AS-IS, and
        reported no contradiction for the very document `check_sync` had just
        excused. Measured in a clean-room worktree at `f67fc36`: three stale
        documents, `beadloom sync-check` rc 2 -> rc 0, six pairs exempt, zero
        `working_declaration_contradicted`.

        **The roots below are re-spelled project-relative**, which is the whole
        of the fix and therefore changes what this fixture has to say. The old
        spelling encoded the broken vocabulary — `guides/*.md` meant a directory
        under `docs/` to one reader and a top-level one to the other — and under
        one vocabulary it means what it says and excuses nothing here; that case
        is pinned in
        `tests/test_bead75_one_path_vocabulary.py::TestADocsDirRelativeRootMeansWhatItSays`.
        The assertion is untouched, and it is the assertion that matters: a
        declaration that silences a pair is a declaration the report names.
        """
        root = _tmp()
        _config(
            root,
            {
                "working": {
                    # The gate defeat itself: the documentation tree declared
                    # WORKING. It still excuses the pair — the exemption is a
                    # declaration and honouring it is the point — and the report
                    # now classifies the same file the same way, so it is named.
                    "roots": ["docs/**/*.md"],
                    "exempt_from_freshness": True,
                    "reason": "generated release notes, regenerated per tag",
                },
            },
        )
        conn = self._stale_project(root, "guides/ci.md")

        rows = check_sync(conn, root)
        report = _report(root, declared={"docs/guides/ci.md"}, beads={})

        assert [r["status"] for r in rows if r["doc_path"] == "guides/ci.md"] == [STATUS_EXEMPT]
        assert [f.rule for f in report.findings] == [FINDING_WORKING_CONTRADICTED]

    def test_the_two_readers_are_handed_two_spellings_of_one_document(self) -> None:
        """The root cause, stated as data rather than as an argument."""
        spaces = default_doc_spaces()

        assert spaces.space_of("docs/guides/ci.md") == SPACE_AS_IS
        assert spaces.space_of("guides/ci.md") is None


# --------------------------------------------------------------------------- #
# FINDING .18-5 — an excused pair that never says it was excused
# --------------------------------------------------------------------------- #


class TestAnExcusedPairSaysSo:
    """`_sync_summary`'s docstring is the specification the new verdict broke.

    It promises a line that says how many pairs were checked and found fresh and
    how many could not be checked at all, because a bare ``N pair(s) fresh`` was
    true of a run in which six pairs had just been deleted (BDL-UX #174). The
    `exempt` verdict is in neither half of that arithmetic.
    """

    @staticmethod
    def _rows(exempt: int, ok: int) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = [
            {"status": STATUS_OK, "doc_path": f"ok-{i}.md"} for i in range(ok)
        ]
        rows += [
            {
                "status": STATUS_EXEMPT,
                "doc_path": f"ACTIVE-{i}.md",
                "reason": "working_space",
            }
            for i in range(exempt)
        ]
        return rows

    def test_the_line_states_the_pairs_it_found_fresh(self) -> None:
        """The control: the fresh half of the promise is kept."""
        from beadloom.doc_sync.surface_ledger import SurfaceVerdict

        line = _sync_summary(self._rows(0, 5), [], SurfaceVerdict(True, False, ""))

        assert line == "5 pair(s) fresh"

    def test_the_line_states_the_pairs_it_excused(self) -> None:
        """FINDING BDL-061.18-5, closed by `beadloom-mr2l.76`.

        An `exempt` pair appeared in no count the gate or the CLI printed.
        Measured in a clean room with one WORKING document declared: 341 pairs =
        326 ok + 11 exempt + 4 incomplete, reported as `total 341, ok 326,
        stale 0, missing 0, unverified 0, unchecked 0`, and the gate printed
        `326 pair(s) fresh` where the same tree without the declaration printed
        326 of 330. That is the failure `_sync_summary`'s own docstring was
        written against, reintroduced by a verdict added after it. The line now
        names the count and the declared reason.
        """
        from beadloom.doc_sync.surface_ledger import SurfaceVerdict

        line = _sync_summary(self._rows(6, 5), [], SurfaceVerdict(True, False, ""))

        assert "exempt" in line
        assert "6" in line

    def test_the_json_summary_accounts_for_every_pair_it_counted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FINDING BDL-061.18-5 in the JSON, closed by `beadloom-mr2l.76`.

        `#148`'s surface: the summary carried total, ok, stale, missing,
        unverified, unchecked, surface_drift and declared_docs, and the verdicts
        did not add up to the total because `exempt` had no key — a consumer
        computing `total - ok` read unexplained pairs. `exempt` and `incomplete`
        are counted now, and `unchecked` stays out of the sum because it counts
        nodes rather than pairs.
        """
        from beadloom.services.cli import main

        root = _tmp()
        _write(root, "src/billing.py", "def charge() -> None:\n    return None\n")
        _write(root, "docs/ACTIVE.md", "# ACTIVE\n")
        conn = _db(root, nodes={"billing": "src/billing.py"}, docs={"billing": "docs/ACTIVE.md"})
        _pair(conn, doc_path="ACTIVE.md", code_path="src/billing.py", ref_id="billing")
        conn.close()
        monkeypatch.chdir(root)

        result = CliRunner().invoke(main, ["sync-check", "--json"])
        summary = json.loads(result.output)["summary"]

        assert summary["total"] == sum(
            summary[key] for key in ("ok", "stale", "missing", "unverified", "unchecked", "exempt")
        )

    def test_the_shipped_layout_excuses_no_pair_at_all(self) -> None:
        """Measured, and it is why the omission has been invisible.

        ``index_docs`` walks the docs directory alone, so a document outside it
        never enters ``sync_state``. The shipped ``ACTIVE.md`` lives under the
        planning tree, so the shipped exemption excuses nothing here: freshness
        never looked at those files. The report nonetheless prints "55 WORKING
        document(s) exempt", which counts documents rather than excused pairs —
        a true sentence about a population that was never in the check.
        """
        report = _repo_report()
        db_path = REPO_ROOT / ".beadloom" / "beadloom.db"
        if not db_path.is_file():  # pragma: no cover - the index is a build artifact
            pytest.skip("no index built; this leg reads the real sync_state")
        conn = open_db(db_path)
        pairs = conn.execute("SELECT doc_path FROM sync_state").fetchall()
        spaces = resolve_doc_spaces(REPO_ROOT)
        excused = [p for (p,) in pairs if spaces.space_of(str(p)) == SPACE_WORKING]
        conn.close()

        assert report.working_documents > 0
        assert excused == []


# --------------------------------------------------------------------------- #
# Repointing the roots — the epic's signature failure, and it does not occur
# --------------------------------------------------------------------------- #


class TestRepointingTheRootsDoesNotBuySilence:
    """`.14` proved `scenario-coverage` survives a path change by going 68 -> 1.

    The relation's equivalent is that a repointed root moves the population
    rather than emptying it, and that an empty population is a NAMED skip rather
    than a pass. Both hold, and both are measured against a project that is not
    this one.
    """

    @pytest.fixture()
    def adopter(self, tmp_path: Path) -> Path:
        project = typescript_project(tmp_path / "orders-web")
        _config(
            project.root,
            {"to_be": {"roots": ["design/*/*.md"]}, "as_is": {"roots": ["handbook/**/*.md"]}},
        )
        return project.root

    def test_the_relation_follows_the_configured_tree(self, adopter: Path) -> None:
        _write(adopter, "design/ORD-4/CONTEXT.md", _context("`checkout`"))

        report = _report(adopter, known={"checkout"}, beads={"ORD-4": ("closed",)})

        assert [f.rule for f in report.findings] == [FINDING_NO_AS_IS]
        assert report.refs_checked == 1

    def test_a_decoy_at_the_shipped_default_is_not_read(self, adopter: Path) -> None:
        _write(adopter, "design/ORD-4/CONTEXT.md", _context("`checkout`"))
        _write(adopter, f"{_EPICS}/DECOY/CONTEXT.md", _context("`checkout`"))

        report = _report(adopter, known={"checkout"}, beads={"ORD-4": ("closed",)})

        assert report.epics == 1

    def test_an_empty_population_is_a_named_skip_and_not_a_pass(self, tmp_path: Path) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _config(project.root, {"to_be": {"roots": ["design/*/*.md"]}})
        _db(project.root, nodes={"checkout": "src/checkout.ts"}, docs={})

        step = _step_doc_spaces(project.root)

        assert step.skipped is True
        assert "design/*/*.md" in step.summary

    def test_the_skip_names_the_root_it_looked_under_even_when_there_is_none(
        self, tmp_path: Path
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _config(project.root, {"to_be": {"roots": []}})
        _db(project.root, nodes={"checkout": "src/checkout.ts"}, docs={})

        step = _step_doc_spaces(project.root)

        assert step.skipped is True
        assert "no root declared" in step.summary

    def test_a_repointed_root_that_finds_work_reports_the_finding_not_a_zero(
        self, adopter: Path
    ) -> None:
        """The `.14` analogue: the number moves, it does not vanish."""
        for key in ("ORD-1", "ORD-2", "ORD-3"):
            _write(adopter, f"design/{key}/CONTEXT.md", _context("`checkout`"))
        _db(adopter, nodes={"checkout": "src/checkout.ts"}, docs={})
        _tracker(
            adopter,
            [
                {"title": f"[{k}.1][dev] ship", "status": "closed"}
                for k in ("ORD-1", "ORD-2", "ORD-3")
            ],
        )

        step = _step_doc_spaces(adopter)

        assert step.skipped is False
        assert len(step.findings) == 3


# --------------------------------------------------------------------------- #
# Unverifiable is not clean — the counterpart that is absent, and the empty one
# --------------------------------------------------------------------------- #


class TestATOBEDocumentWithNoAsIsCounterpart:
    """Distinguishing "no counterpart" from "an empty counterpart".

    The relation reads `declared_docs`, deliberately: a node whose only document
    was deleted must still count as declaring one, else deleting the file makes
    the check quieter. The cost of that choice is that the relation alone cannot
    tell a real document from a declared path with nothing behind it. The
    composite gate can, and these tests pin WHICH check does it, so a later
    change that makes the relation the only reader is caught here.
    """

    def test_the_relation_alone_cannot_see_that_the_document_is_absent(self) -> None:
        root = _tmp()
        _write(root, f"{_EPICS}/PROJ-1/CONTEXT.md", _context("`billing`"))

        report = _report(
            root, known={"billing"}, documented={"billing"}, beads={"PROJ-1": ("closed",)}
        )

        assert report.findings == ()
        assert report.refs_checked == 1

    def test_sync_check_reports_the_absent_document_as_missing(self) -> None:
        root = _tmp()
        _write(root, "src/billing.py", "def charge() -> None:\n    return None\n")
        conn = _db(
            root,
            nodes={"billing": "src/billing.py"},
            docs={"billing": "docs/billing.md"},
        )
        _pair(conn, doc_path="billing.md", code_path="src/billing.py", ref_id="billing")

        rows = check_sync(conn, root)

        assert [r["status"] for r in rows if r["doc_path"] == "billing.md"] == ["missing"]

    def test_an_empty_counterpart_is_stale_rather_than_fresh(self) -> None:
        root = _tmp()
        _write(root, "src/billing.py", "def charge() -> None:\n    return None\n")
        _write(root, "docs/billing.md", "")
        conn = _db(root, nodes={"billing": "src/billing.py"}, docs={"billing": "docs/billing.md"})
        _pair(conn, doc_path="billing.md", code_path="src/billing.py", ref_id="billing")

        rows = check_sync(conn, root)

        assert [r["status"] for r in rows if r["doc_path"] == "billing.md"] == ["stale"]


# --------------------------------------------------------------------------- #
# Edges the vocabulary has to survive
# --------------------------------------------------------------------------- #


class TestTheVocabularyEdges:
    @pytest.mark.parametrize(
        ("path", "pattern", "expected"),
        [
            ("notes.md", "*.md", True),
            ("vendor/lib/notes.md", "*.md", False),
            ("docs/a.md", "docs/**/*.md", True),
            ("docs/a/b/c.md", "docs/**/*.md", True),
            ("docs/a.md", "docs/*?.md", True),
            ("docs/.md", "docs/*?.md", False),
            ("docs/anything", "docs/**", True),
            ("a+b/c.md", "a+b/*.md", True),
            ("Документы/PRD.md", "Документы/*.md", True),
            ("docs/a.md", "DOCS/*.md", False),
        ],
    )
    def test_a_root_glob_reaches_exactly_what_path_glob_reaches(
        self, path: str, pattern: str, expected: bool
    ) -> None:
        assert path_matches(path, pattern) is expected

    @pytest.mark.parametrize(
        ("path", "kind"),
        [
            ("PRD.md", "PRD"),
            ("dir/PRD.md", "PRD"),
            ("archive.tar.gz", "archive.tar"),
            ("", ""),
            ("dir/", ""),
            (".md", ".md"),
            ("  PRD.md  ", "PRD"),
        ],
    )
    def test_the_kind_is_the_stem_whatever_the_path_looks_like(self, path: str, kind: str) -> None:
        assert document_kind(path) == kind

    def test_two_roots_naming_one_file_count_it_once(self, tmp_path: Path) -> None:
        _config(tmp_path, {"to_be": {"roots": ["plans/*.md", "plans/PRD.md"]}})
        _write(tmp_path, "plans/PRD.md", "# PRD\n")

        found = resolve_doc_spaces(tmp_path).documents_in(tmp_path, SPACE_TO_BE)

        assert len(found) == 1

    def test_a_single_string_root_is_read_as_one_root(self, tmp_path: Path) -> None:
        _config(tmp_path, {"to_be": {"roots": "plans/*.md"}})
        _write(tmp_path, "plans/PRD.md", "# PRD\n")

        spaces = resolve_doc_spaces(tmp_path)

        assert spaces.roots[SPACE_TO_BE] == ("plans/*.md",)
        assert len(spaces.documents_in(tmp_path, SPACE_TO_BE)) == 1

    def test_a_config_that_is_not_a_mapping_is_the_shipped_default(self, tmp_path: Path) -> None:
        _write(tmp_path, ".beadloom/config.yml", "- one\n- two\n")

        spaces = resolve_doc_spaces(tmp_path)

        assert spaces.roots == dict(DEFAULT_ROOTS)
        assert spaces.config_errors == ()

    def test_an_unreadable_config_is_a_named_error_and_not_a_crash(self, tmp_path: Path) -> None:
        _write(tmp_path, ".beadloom/config.yml", "doc_roots: [unclosed\n")

        spaces = resolve_doc_spaces(tmp_path)

        assert spaces.config_errors
        assert "unreadable" in spaces.config_errors[0]

    def test_a_working_document_under_an_as_is_root_is_still_working(self, tmp_path: Path) -> None:
        _write(tmp_path, "docs/ACTIVE.md", "# ACTIVE\n")

        spaces = default_doc_spaces()

        assert [p.name for p in spaces.working_documents(tmp_path)] == ["ACTIVE.md"]
        assert spaces.documents_in(tmp_path, SPACE_AS_IS) == []

    def test_two_epics_of_one_key_merge_rather_than_overwrite(self) -> None:
        grouped = beads_by_epic(
            [
                {"title": "[PROJ-1.1][dev] a", "status": "closed"},
                {"title": "[PROJ-1.2][test] b", "status": "open"},
            ]
        )

        assert grouped["PROJ-1"] == ("closed", "open")

    def test_a_status_that_is_not_a_string_is_empty_rather_than_closed(self) -> None:
        grouped = beads_by_epic([{"title": "[PROJ-1.1][dev] a", "status": None}])

        assert grouped["PROJ-1"] == ("",)

    def test_an_epic_key_with_no_documents_is_not_invented(self, tmp_path: Path) -> None:
        report = _report(tmp_path, beads={"PROJ-9": ("closed",)})

        assert report.epics == 0
        assert report.relation_checked is False

    def test_reading_intents_needs_no_tracker_at_all(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/PROJ-1/CONTEXT.md", _context("`billing`"))

        intents = read_epic_intents(
            tmp_path,
            spaces=default_doc_spaces(),
            known_refs=frozenset({"billing"}),
            beads_by_epic=None,
        )

        assert [i.key for i in intents] == ["PROJ-1"]
        assert intents[0].bead_statuses is None
        assert intents[0].has_closed_bead is False


# --------------------------------------------------------------------------- #
# The suite this file belongs to
# --------------------------------------------------------------------------- #


class TestTheFindingsAreExecutable:
    """A finding stated only in prose is a finding nobody re-measures.

    `.14` left three `xfail(strict=True)` statements and `.57` closed nine of
    `.10`'s; the convention is that a fix reddens the suite. This test keeps the
    convention honest by refusing to let the findings quietly become comments.

    A finding is executable in one of two states, and this counts BOTH: still
    open, as a strict `xfail` whose reason names it, or closed, as a passing
    test whose docstring names it and the bead that closed it. The total may not
    fall — deleting a closed finding's test would lose the only executable
    record that the defect is gone, which is the same loss as deleting an open
    one, one step later.
    """

    #: Twelve findings were filed by `.18`, and twelve statements must remain.
    _FILED = 12

    def _statements(self) -> tuple[list[tuple[str, pytest.MarkDecorator]], list[str]]:
        import inspect

        import tests.test_bead18_s5_relation as module

        marks: list[tuple[str, pytest.MarkDecorator]] = []
        closed: list[str] = []
        for _, obj in inspect.getmembers(module, inspect.isclass):
            for name, function in inspect.getmembers(obj, inspect.isfunction):
                if not name.startswith("test_"):
                    continue
                xfails = [
                    mark
                    for mark in getattr(function, "pytestmark", [])
                    if mark.name == "xfail"
                ]
                marks.extend((name, mark) for mark in xfails)
                if not xfails and "FINDING BDL-061.18-" in (function.__doc__ or ""):
                    closed.append(name)
        return marks, closed

    def test_every_xfail_here_is_strict_and_names_its_finding(self) -> None:
        marks, _ = self._statements()

        for name, mark in marks:
            assert mark.kwargs.get("strict") is True, name
            assert "FINDING BDL-061.18-" in mark.kwargs.get("reason", ""), name

    def test_no_finding_left_the_file_when_it_was_fixed(self) -> None:
        marks, closed = self._statements()

        assert len(marks) + len(closed) >= self._FILED
