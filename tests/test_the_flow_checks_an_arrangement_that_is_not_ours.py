"""BDL-068 S6 — the slice's checks, run against a flow that is not this one's.

S6's subject is the flow's own documents and roles, so its characteristic risk is
a check that passes because THIS repository happens to be arranged the right way.
BDL-UX #240 is the measured precedent: a defect in the typed leg's path filter was
invisible here because Beadloom is src-layout, and it survived the bead that built
the surface.

``tests/adopter_flow.py`` is the substitutable input, the way ``.33`` made the
platform one (``PathFlavour``), S3 made the CI room one (``room_simulation``) and
``.42`` made the project layout one. Each arrangement it holds is a choice the
shipped flow permits: which tools a project composes adapters for, where its
planning documents live, which column of its bead table carries the bead id, how
it spells an alignment row, whether its graph is one file or one per node, and
whether it declares an issue log at all.

Three findings are pinned as ``xfail(strict=True)`` with ``FINDING BDL-068.S6-N``
in the reason, the convention ``.18`` set and ``.22`` carried. Everything else was
written after the behaviour and is a boundary guard: it holds the population each
check entered where the check states it correctly today, so a later change that
narrows one is reported rather than absorbed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.gate import _step_issue_numbers
from beadloom.application.waves import BeadRecord, WaveEnvironment, WorkItemAxes
from beadloom.application.waves.media_checks import (
    _check_focus_document,
    _check_graph_files,
)
from beadloom.application.waves.models import GraphFile, GraphInput
from beadloom.doc_sync.issue_numbers import (
    allocate_number,
    check_issue_numbers,
    read_claims,
)
from beadloom.onboarding.flow_config import FlowConfig
from beadloom.onboarding.graph_files import each_graph_file
from beadloom.onboarding.graph_layout import layout_of
from beadloom.onboarding.role_composer import ROLE_NAMES
from beadloom.onboarding.role_map import role_map_report
from beadloom.services.commands.waves import _focus_documents
from tests.adopter_flow import (
    BEAD_IN_THE_SECOND_COLUMN,
    CURSOR_ONLY,
    DOCS_ELSEWHERE,
    NO_ISSUE_LOG,
    ONE_FILE,
    ONE_PER_NODE,
    OURS,
    SHORT_ALIGNMENT_ROWS,
    SINGLE_FILE_GRAPH,
    FlowArrangement,
    build_flow,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.waves.models import FocusDocument

#: Ways a project can declare an issue log and get it wrong. Every one of them is
#: a project that opted IN, and every one is reported as a project that did not.
BROKEN_DECLARATIONS: tuple[tuple[str, str], ...] = (
    ("the path key is misspelled", "issue_log:\n  paths: ISSUES.md\n  ledger: issues\n"),
    ("the ledger key is misspelled", "issue_log:\n  path: ISSUES.md\n  ledgr: issues\n"),
    ("the block will not parse", "issue_log:\n  path: [unclosed\n"),
    ("the block is a scalar", "issue_log: ISSUES.md\n"),
)


def _plan_focus(root: Path, active: Path, work_item: str) -> tuple[FocusDocument, ...] | None:
    axes = WorkItemAxes(work_item=work_item, document=str(active.relative_to(root)))
    return _focus_documents(root, axes)


def _records(*bead_ids: str) -> list[BeadRecord]:
    return [BeadRecord(bead_id=bead_id, title=bead_id) for bead_id in bead_ids]


class TestTheIssueLogStepUnderAProjectThatOptedIn:
    """Whether a misdeclared log can be told from no declaration at all.

    The step's own docstring earns its right to block on this sentence: "It cannot
    redden a project that has not opted in. The log is DECLARED in
    ``.beadloom/config.yml``; an adopter who declares none gets a named skip." The
    skip is correct and the question is what else reaches it.
    """

    def test_a_project_that_declares_nothing_is_skipped_by_name(self, tmp_path: Path) -> None:
        """The behaviour the step promises, on the arrangement that asks for it."""
        step = _step_issue_numbers(_built(NO_ISSUE_LOG, tmp_path))
        assert step.skipped is True
        assert "no issue log is declared" in step.summary

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-3 (BDL-UX #270): four ways of misdeclaring `issue_log:` reach the "
            "same gate verdict as declaring none — `skipped — no issue log is "
            "declared`. The refusal goes to `logging`, which the Gate does not "
            "render, so a project that opted in and mistyped one key is told it "
            "opted out"
        ),
    )
    @pytest.mark.parametrize(("label", "config"), BROKEN_DECLARATIONS, ids=lambda v: v)
    def test_a_broken_declaration_does_not_read_as_no_declaration(
        self, tmp_path: Path, label: str, config: str
    ) -> None:
        """Compared against the opt-out's own verdict, so rewording one cannot pass it."""
        opted_out = _step_issue_numbers(_built(NO_ISSUE_LOG, tmp_path / "none"))
        root = _built(OURS, tmp_path / "broken")
        (root / ".beadloom" / "config.yml").write_text(config, encoding="utf-8")
        broken = _step_issue_numbers(root)
        assert (broken.skipped, broken.summary) != (opted_out.skipped, opted_out.summary), (
            f"{label}: a project that opted in is told it opted out"
        )

    @pytest.mark.parametrize(("label", "config"), BROKEN_DECLARATIONS, ids=lambda v: v)
    def test_each_broken_declaration_is_the_one_recorded(
        self, tmp_path: Path, label: str, config: str
    ) -> None:
        """The red above is red for the reason claimed, and for no other."""
        root = _built(OURS, tmp_path)
        (root / ".beadloom" / "config.yml").write_text(config, encoding="utf-8")
        assert check_issue_numbers(root).declared is False, label
        assert _step_issue_numbers(root).skipped is True, label


class TestTheLedgerAndTheAllocatorAgreeOnWhatAClaimIs:
    """The claim file is the allocation, so a claim it cannot see is a free number.

    ``read_claims`` accepts a file whose stem is entirely digits and drops every
    other ``.md`` in the ledger without reporting one. The module's own docstring
    invites the name it drops: the claim file "is where the incident's body grows
    when the log becomes a composed view of the ledger", and a body grows a title.
    """

    def test_a_numbered_claim_file_is_read(self, tmp_path: Path) -> None:
        root = _built(OURS, tmp_path, log_entries=2)
        ledger = root / "issues"
        ledger.mkdir()
        (ledger / "0003.md").write_text("# 3\n\n**Holder:** bead-A\n", encoding="utf-8")
        assert [claim.number for claim in read_claims(ledger)] == [3]

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-4 (BDL-UX #271): a ledger file whose stem is not purely numeric "
            "is dropped by `read_claims` without report, so `allocate_number` "
            "re-issues the number it holds — the collision the allocator exists to "
            "make impossible, produced by the allocator"
        ),
    )
    def test_a_number_a_claim_file_holds_is_never_allocated_again(self, tmp_path: Path) -> None:
        root = _built(OURS, tmp_path, log_entries=2)
        ledger = root / "issues"
        ledger.mkdir()
        (ledger / "0003-the-clean-room-convention.md").write_text(
            "# 3\n\n**Holder:** bead-A\n", encoding="utf-8"
        )
        assert allocate_number(root, holder="bead-B").number != 3

    def test_the_collision_is_the_one_recorded(self, tmp_path: Path) -> None:
        """Two writers hold #3, and the check names neither of them for it."""
        root = _built(OURS, tmp_path, log_entries=2)
        ledger = root / "issues"
        ledger.mkdir()
        titled = ledger / "0003-the-clean-room-convention.md"
        titled.write_text("# 3\n\n**Holder:** bead-A\n", encoding="utf-8")

        assert read_claims(ledger) == ()
        claim = allocate_number(root, holder="bead-B")
        assert claim.number == 3
        assert titled.exists()
        assert sorted(path.name for path in ledger.iterdir()) == [
            "0003-the-clean-room-convention.md",
            "0003.md",
        ]
        report = check_issue_numbers(root)
        assert report.claims == 1
        assert [finding.check for finding in report.findings] == ["unwritten-claim"]


class TestTheIssueLogVerdictStatesThePopulationItEntered:
    """``beadloom-l9ee``'s finding, held where it was closed.

    The ``unclaimed-number`` leg passes over every entry below the ledger's floor.
    Measured on this repository on 2026-09-09, before ``.66`` closed it: 240
    entries, floor 262, so the leg entered five of them and the verdict read "No
    duplicate, unwritten or unclaimed number" — a clean list over a population two
    per cent the size of the one its header named. Written after the behaviour, so
    it is a boundary guard: it holds the statement rather than having produced it.
    """

    def test_a_clean_verdict_over_a_floor_limited_log_states_the_population(
        self, tmp_path: Path
    ) -> None:
        root = _built(OURS, tmp_path, log_entries=240)
        claim = allocate_number(root, holder="bead-A")
        log = root / "ISSUES.md"
        log.write_text(
            log.read_text(encoding="utf-8") + f"{claim.number}. the new entry\n",
            encoding="utf-8",
        )
        report = check_issue_numbers(root)
        assert report.passed is True
        assert report.entries == 241
        assert report.entries_below_floor == 240
        summary = _step_issue_numbers(root).summary
        assert "240 of 241" in summary
        assert "unclaimed-number did not enter" in summary

    def test_a_ledger_with_no_claim_says_two_legs_read_nothing(self, tmp_path: Path) -> None:
        root = _built(OURS, tmp_path, log_entries=3)
        report = check_issue_numbers(root)
        assert report.floor is None
        assert report.not_verified is True
        assert "NOT CHECKED" in _step_issue_numbers(root).summary


class TestTheFocusDocumentMediumsPopulation:
    """Which rows the ``focus-document`` medium reads, and which document they are in.

    ``FocusDocument.row_cells`` is "the FIRST cell of every markdown table row in
    the file", justified as "the column an ACTIVE table names its bead in". Both
    halves are claims about an arrangement: the column is a convention, and every
    table row in the file is a wider population than the bead table.
    """

    def test_a_document_stored_outside_the_default_folder_is_still_read(
        self, tmp_path: Path
    ) -> None:
        """The arrangement axis ``.75`` got right: the glob is configured, not spelled."""
        flow = build_flow(tmp_path / "proj", DOCS_ELSEWHERE)
        documents = _plan_focus(flow.root, flow.active, flow.work_item)
        assert documents is not None
        assert [document.path for document in documents] == ["docs/planning/ADOPT-1/ACTIVE.md"]
        check = _check_focus_document(
            WaveEnvironment(focus_documents=documents), _records(*flow.beads)
        )
        assert check.status == "passed"

    def test_our_own_arrangement_passes(self, tmp_path: Path) -> None:
        flow = build_flow(tmp_path / "proj", OURS)
        documents = _plan_focus(flow.root, flow.active, flow.work_item)
        check = _check_focus_document(
            WaveEnvironment(focus_documents=documents), _records(*flow.beads)
        )
        assert check.status == "passed"

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-5 (BDL-UX #272): the medium reads only the first cell of a row, "
            "so a bead table that carries the id in its second column reports every "
            "bead of the wave as having no row — a red against a document that gives "
            "each of them one"
        ),
    )
    def test_a_bead_table_that_numbers_its_waves_first_still_names_its_beads(
        self, tmp_path: Path
    ) -> None:
        flow = build_flow(tmp_path / "proj", BEAD_IN_THE_SECOND_COLUMN)
        documents = _plan_focus(flow.root, flow.active, flow.work_item)
        check = _check_focus_document(
            WaveEnvironment(focus_documents=documents), _records(*flow.beads)
        )
        assert check.status == "passed", check.detail

    def test_the_false_red_is_the_one_recorded(self, tmp_path: Path) -> None:
        flow = build_flow(tmp_path / "proj", BEAD_IN_THE_SECOND_COLUMN)
        documents = _plan_focus(flow.root, flow.active, flow.work_item)
        assert documents is not None
        assert documents[0].row_cells[:4] == ("Wave", "------", "1", "2")
        check = _check_focus_document(
            WaveEnvironment(focus_documents=documents), _records(*flow.beads)
        )
        assert check.status == "failed"
        assert "2 of 2 bead(s)" in check.detail

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-5 (BDL-UX #272): the population is every table row in the "
            "document, so a bead named only by a table about something else passes "
            "— the medium reports a line of its own where the bead has none"
        ),
    )
    def test_a_bead_named_only_by_a_second_table_is_reported(self, tmp_path: Path) -> None:
        flow = build_flow(tmp_path / "proj", OURS, beads=("adopter-aaaa.1",), deferred=(".9",))
        documents = _plan_focus(flow.root, flow.active, flow.work_item)
        check = _check_focus_document(
            WaveEnvironment(focus_documents=documents),
            _records("adopter-aaaa.1", "adopter-aaaa.9"),
        )
        assert check.status == "failed", check.detail

    def test_the_false_green_is_the_one_recorded(self, tmp_path: Path) -> None:
        """The row that satisfies the check is in the deferral table, not the bead table."""
        flow = build_flow(tmp_path / "proj", OURS, beads=("adopter-aaaa.1",), deferred=(".9",))
        documents = _plan_focus(flow.root, flow.active, flow.work_item)
        assert documents is not None
        assert ".9" in documents[0].row_cells
        check = _check_focus_document(
            WaveEnvironment(focus_documents=documents),
            _records("adopter-aaaa.1", "adopter-aaaa.9"),
        )
        assert check.status == "passed"

    def test_an_alignment_row_spelling_does_not_move_the_verdict(self, tmp_path: Path) -> None:
        """The one table axis this medium is indifferent to, held so it stays that way."""
        flow = build_flow(tmp_path / "proj", SHORT_ALIGNMENT_ROWS)
        documents = _plan_focus(flow.root, flow.active, flow.work_item)
        check = _check_focus_document(
            WaveEnvironment(focus_documents=documents), _records(*flow.beads)
        )
        assert check.status == "passed"


class TestTheGraphFilesMediumUnderBothLayouts:
    """The medium ``beadloom-kqsv`` shipped, asked about a layout that is not ours.

    ``.80`` moved this repository to one node per file, so the branch that names a
    shared file is no longer reachable from our own graph. It is the branch every
    adopter of ``beadloom init`` starts on, which is what makes it worth a room of
    its own.
    """

    @pytest.mark.parametrize(
        ("arrangement", "expected"),
        [(SINGLE_FILE_GRAPH, ONE_FILE), (OURS, ONE_PER_NODE)],
        ids=[ONE_FILE, ONE_PER_NODE],
    )
    def test_the_layout_is_read_off_the_directory(
        self, tmp_path: Path, arrangement: FlowArrangement, expected: str
    ) -> None:
        flow = build_flow(tmp_path / "proj", arrangement, nodes=("orders", "billing"))
        layout = layout_of(flow.graph_dir)
        assert layout.declared == 2
        assert layout.holds is (expected == ONE_PER_NODE)
        assert layout.shared_nodes == (2 if expected == ONE_FILE else 0)

    def test_a_single_file_graph_names_the_file_a_node_adding_bead_writes(
        self, tmp_path: Path
    ) -> None:
        flow = build_flow(tmp_path / "proj", SINGLE_FILE_GRAPH)
        check = _check_graph_files(WaveEnvironment(graph_input=_graph_input_of(flow.root)))
        assert check.status == "passed"
        assert "a bead that ADDS one writes .beadloom/_graph/graph.yml" in check.detail
        assert "which holds 2 of them" in check.detail

    def test_one_file_per_node_says_the_collision_cannot_be_attempted(
        self, tmp_path: Path
    ) -> None:
        flow = build_flow(tmp_path / "proj", OURS)
        check = _check_graph_files(WaveEnvironment(graph_input=_graph_input_of(flow.root)))
        assert check.status == "passed"
        assert "declared in a file of its own" in check.detail

    def test_both_layouts_state_the_half_no_plan_can_reach(self, tmp_path: Path) -> None:
        """The sentence that survives the layout change, in both branches."""
        details = []
        for arrangement in (SINGLE_FILE_GRAPH, OURS):
            flow = build_flow(tmp_path / arrangement.label, arrangement)
            details.append(
                _check_graph_files(WaveEnvironment(graph_input=_graph_input_of(flow.root))).detail
            )
        assert all("in no graph this plan could read" in detail for detail in details)


class TestTheRoleMapReadsTheMapEachDeclaredToolHolds:
    """Which artifact the role map reads, and whose document it names.

    Until BDL-068 `.84` this class characterised the defect the S6 review made
    Major 1: ``role_map_report`` composed ``("claude", "CLAUDE")`` unconditionally
    and never read ``config.tools``, so a project declaring ``cursor`` alone was
    judged against a composition its flow does not declare while the map its
    agent actually reads -- ``.cursor/rules/beadloom-flow.md``, whose body
    enumerates the roles -- was asked nothing.

    The control below is the one that moved. It used to assert that the verdict
    does NOT change with the tool set, which was the defect stated as a property;
    it now asserts that it does, because the corpus is the tool's own map.
    """

    def test_a_cursor_only_project_is_checked_against_the_cursor_map(
        self, tmp_path: Path
    ) -> None:
        flow = build_flow(tmp_path / "proj", CURSOR_ONLY)
        report = role_map_report(flow.root)
        assert [artifact.tool for artifact in report.artifacts] == ["cursor"]
        assert [artifact.name for artifact in report.artifacts] == [
            ".cursor/rules/beadloom-flow.md"
        ]
        assert report.inspected == (".cursor/rules/beadloom-flow.md",)

    def test_the_tool_set_moves_the_corpus(self, tmp_path: Path) -> None:
        """The control the defect used to pass: two tool sets, two maps."""
        ours = role_map_report(build_flow(tmp_path / "ours", OURS).root)
        cursor = role_map_report(build_flow(tmp_path / "cursor", CURSOR_ONLY).root)
        assert [artifact.tool for artifact in ours.artifacts] == ["claude"]
        assert ours.inspected == ("templates/agentic_flow/CLAUDE.md.txt",
                                  "templates/claude/stack/python/CLAUDE.md.txt")
        assert set(ours.inspected).isdisjoint(cursor.inspected)

    def test_neither_arrangement_reads_an_artifact_that_project_wrote(
        self, tmp_path: Path
    ) -> None:
        """Both corpora are the COMPOSITION, so no adopter's edit is judged.

        The cursor map's one fragment is labelled with the path the pointer is
        written TO, because that is what a reader opens; its BODY comes from
        ``role_adapters``. Asserted by building the project without ever running
        the adapter generator, so the file the label names does not exist.
        """
        for arrangement in (OURS, CURSOR_ONLY):
            flow = build_flow(tmp_path / arrangement.label, arrangement)
            report = role_map_report(flow.root)
            assert report.references, report
            for artifact in report.artifacts:
                assert not (flow.root / artifact.name).exists(), artifact.name

    def test_the_cursor_map_is_judged_by_the_same_derivation(
        self, tmp_path: Path
    ) -> None:
        """A role the Cursor pointer does not name is a finding against it.

        This is BDL-UX #252's own class on the axis the check could not reach: a
        composed role missing from the map that enumerates roles. The population
        is varied through the ``roles`` seam rather than by writing a sixth
        fragment into the shared templates directory.
        """
        flow = build_flow(tmp_path / "proj", CURSOR_ONLY)
        report = role_map_report(flow.root, roles=(*ROLE_NAMES, "scout"))
        unmapped = [f for f in report.findings if f.kind == "unmapped"]
        assert [f.role for f in unmapped] == ["scout"]
        assert unmapped[0].tool == "cursor"
        assert unmapped[0].artifact == ".cursor/rules/beadloom-flow.md"
        assert ".cursor/rules/beadloom-flow.md" in unmapped[0].why

    def test_the_shipped_cursor_map_names_every_composed_role(
        self, tmp_path: Path
    ) -> None:
        """The control for the test above: red on a sixth role, green on ours."""
        flow = build_flow(tmp_path / "proj", CURSOR_ONLY)
        assert role_map_report(flow.root).findings == ()

    def test_a_declared_tool_with_no_map_artifact_is_unreached_not_substituted(
        self, tmp_path: Path
    ) -> None:
        """The population is ``config.tools``; the artifact table is the lookup.

        Reached through the ``config`` seam because ``flow.yml`` validates
        ``tools:`` against ``SUPPORTED_TOOLS``, so this is the arrangement a
        release that adds a tool reaches first. It is the same control
        ``beadloom-ec1a`` used on the other tool-population constant in this
        domain (BDL-UX #277).
        """
        flow = build_flow(tmp_path / "proj", OURS)
        config = FlowConfig(tools=("windsurf",), architecture="ddd", stack=("python",))
        report = role_map_report(flow.root, config)
        assert report.artifacts == ()
        assert report.findings == ()
        assert [entry.tool for entry in report.unreached] == ["windsurf"]
        assert "was NOT checked" in report.unreached[0].why

    def test_every_declared_tool_is_either_a_map_read_or_a_reason_it_was_not(
        self, tmp_path: Path
    ) -> None:
        """The partition, over every tool set an adopter can declare."""
        flow = build_flow(tmp_path / "proj", OURS)
        for tools in (("claude",), ("cursor",), ("claude", "cursor"), ("windsurf",)):
            config = FlowConfig(tools=tools, architecture="ddd", stack=("python",))
            report = role_map_report(flow.root, config)
            assert report.tools == tools
            covered = [a.tool for a in report.artifacts] + [
                u.tool for u in report.unreached
            ]
            assert covered == list(tools), (tools, covered)

    def test_a_project_declaring_both_tools_is_checked_against_both_maps(
        self, tmp_path: Path
    ) -> None:
        """Each map owes the whole role population on its own."""
        flow = build_flow(tmp_path / "proj", OURS)
        config = FlowConfig(
            tools=("claude", "cursor"), architecture="ddd", stack=("python",)
        )
        report = role_map_report(flow.root, config, roles=(*ROLE_NAMES, "scout"))
        assert {f.tool for f in report.findings if f.kind == "unmapped"} == {
            "claude",
            "cursor",
        }
        assert {reference.tool for reference in report.references} == {
            "claude",
            "cursor",
        }


class TestEveryFindingHereIsStrictAndNamesItself:
    """The meta-check `.18` introduced and `.22` carried."""

    def test_every_xfail_in_this_module_is_strict_and_cites_a_finding(self) -> None:
        import sys

        module = sys.modules[__name__]
        for klass_name, klass in vars(module).items():
            if not (isinstance(klass, type) and klass_name.startswith("Test")):
                continue
            for name, function in vars(klass).items():
                for mark in getattr(function, "pytestmark", []):
                    if mark.name != "xfail":
                        continue
                    where = f"{klass_name}.{name}"
                    assert mark.kwargs.get("strict") is True, f"{where}: not strict"
                    assert "FINDING BDL-068.S6-" in mark.kwargs.get("reason", ""), where


def _built(arrangement: FlowArrangement, root: Path, *, log_entries: int = 0) -> Path:
    """A project arranged as *arrangement*, under a directory the caller owns."""
    return build_flow(root / "proj", arrangement, log_entries=log_entries).root


def _graph_input_of(project_root: Path) -> GraphInput:
    """The ``GraphInput`` a plan holds, read the way the command reads it.

    The graph half goes through :func:`each_graph_file`, which is the one policy
    every reader of that directory holds; the index half is supplied as the same
    population, so these rows measure the LAYOUT and not a database. The drift
    branch, where the two populations differ, is ``tests/test_wave_media_checks.py``'s.
    """
    graph_dir = project_root / ".beadloom" / "_graph"
    files = tuple(
        GraphFile(
            path=path.relative_to(project_root).as_posix(),
            nodes=tuple(
                sorted(
                    str(node["ref_id"])
                    for node in data.get("nodes") or []
                    if isinstance(node, dict) and node.get("ref_id")
                )
            ),
        )
        for path, data in each_graph_file(graph_dir)
    )
    return GraphInput(
        files=files,
        indexed=frozenset(ref for entry in files for ref in entry.nodes),
    )
