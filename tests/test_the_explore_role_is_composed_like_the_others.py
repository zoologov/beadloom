"""BDL-068 S1.5 — the Explore role, and the route a work item was decided into.

Two acceptance points, and one measured premise failure behind each.

**"A role file composed by role-composer like the other four"** presumed one role
population to add a fifth member to. Measured at ``2a5c0d1`` there were two hand-maintained
literals of the same fact — ``role_composer.ROLE_NAMES`` and
``agentic_flow_setup.AGENT_FILES``, whose own comment said it mirrored the other — with eight
readers between them, plus a third list spelled as prose inside the Cursor orchestrator
pointer. A fifth role added to one of them is exactly the fifth thing that can drift. So the
population is DERIVED from the shipped CORE fragments and the other two are that derivation.

**"/task-init cannot reach the type decision without it having run"** was false, and
measurably so: ``beadloom docs quality`` at ``2a5c0d1`` reported ``BRIEF documents do not
carry Axes (0/12)`` and ``RFC documents do not carry Axes (0/48)``. S1.4's ``missing-section``
is peer-relative, so a section no peer keeps produces one kind-level statement and no
document-level finding at all.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.planning_report import CHECK_NAMES, planning_report
from beadloom.application.work_item_routing import (
    AXES_ROLE,
    FULL,
    SIMPLIFIED,
    TASK_INIT_COMMAND,
    read_routing,
    task_init_routing,
)
from beadloom.doc_sync.axes_section import AXES_HEADING
from beadloom.doc_sync.doc_shape import EMPTY_SECTION, check_planning_sections
from beadloom.doc_sync.work_item_type import (
    NODES_THE_SIMPLIFIED_ROUTE_HOLDS,
    ROUTE_NOT_SUPPORTED_BY_THE_AXES,
    ROUTED_WITHOUT_AXES,
    check_work_item_types,
)
from beadloom.onboarding.agentic_flow_setup import (
    AGENT_FILES,
    _vendored_asset,
    composed_command,
    scaffold,
)
from beadloom.onboarding.composer import SHARED_ROLE_FRAGMENTS, compose
from beadloom.onboarding.config_sync import ConfigDrift, check_config_drift
from beadloom.onboarding.doc_templates import DEFAULT_DOC_CONFIG
from beadloom.onboarding.flow_config import (
    SUPPORTED_ARCHITECTURES,
    FlowConfig,
    load_flow_config,
)
from beadloom.onboarding.role_adapters import cursor_rules_body, generate_adapters
from beadloom.onboarding.role_composer import (
    ROLE_NAMES,
    compose_role,
    fragment_role_name,
    roles_in,
    roles_templates_root,
)

if TYPE_CHECKING:
    from pathlib import Path

_FLOW_YML = "tools: [claude]\narchitecture: ddd\nstack: [python]\n"

_REPO_ROOT_MARKER = "pyproject.toml"


def _repo_root() -> Path:
    from pathlib import Path as _Path

    here = _Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / _REPO_ROOT_MARKER).is_file():
            return candidate
    msg = "the repository root was not found above this test file"
    raise AssertionError(msg)


def _adopter(tmp_path: Path) -> Path:
    """A fully scaffolded adopter project — the two calls the CLI command makes."""
    project = tmp_path / "acme-service"
    (project / ".beadloom").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "acme-service"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    (project / ".beadloom" / "flow.yml").write_text(_FLOW_YML, encoding="utf-8")
    generate_adapters(load_flow_config(project), project)
    scaffold(project, include_agents=False)
    return project


def _drifts(project: Path) -> list[ConfigDrift]:
    return check_config_drift(project, sqlite3.connect(":memory:"))


class TestARoleExistsBecauseAFragmentShipsForIt:
    """The population is derived from the fragments, over a shape, not a spelling."""

    def test_the_derived_population_is_what_the_core_directory_holds(self) -> None:
        """Every shipped role, and nothing that is only a layer."""
        core = roles_templates_root() / "core"
        named = {
            path.name.removesuffix(".md.txt")
            for path in core.glob("*.md.txt")
            if fragment_role_name(path.read_text(encoding="utf-8")) is not None
        }
        assert set(ROLE_NAMES) == named
        assert AXES_ROLE in ROLE_NAMES

    def test_the_shared_layer_is_not_a_role(self) -> None:
        """``_writing`` composes into every role and is never written as one."""
        for shared in SHARED_ROLE_FRAGMENTS:
            assert shared not in ROLE_NAMES
        text = (roles_templates_root() / "core" / "_writing.md.txt").read_text(
            encoding="utf-8"
        )
        assert fragment_role_name(text) is None

    def test_a_localisation_is_not_a_second_role(self, tmp_path: Path) -> None:
        """``scout.ru.md.txt`` is the same role in another language, not another role."""
        # Arrange
        core = tmp_path / "core"
        core.mkdir()
        body = "---\nname: scout\ndescription: d.\n---\n\nbody\n"
        (core / "scout.md.txt").write_text(body, encoding="utf-8")
        (core / "scout.ru.md.txt").write_text(body, encoding="utf-8")

        # Act + Assert
        assert roles_in(core) == ("scout",)

    def test_a_fragment_naming_another_role_is_not_read_as_one(
        self, tmp_path: Path
    ) -> None:
        """The file name and the declared name are what every reader keys on."""
        # Arrange — a copy-pasted fragment whose front matter was not updated
        core = tmp_path / "core"
        core.mkdir()
        (core / "scout.md.txt").write_text(
            "---\nname: dev\ndescription: d.\n---\n\nbody\n", encoding="utf-8"
        )

        # Act + Assert
        assert roles_in(core) == ()

    def test_the_population_is_ordered_deterministically(self, tmp_path: Path) -> None:
        """A directory listing is not ordered, and generated bytes must be."""
        core = tmp_path / "core"
        core.mkdir()
        for name in ("zulu", "alpha", "mike"):
            (core / f"{name}.md.txt").write_text(
                f"---\nname: {name}\ndescription: d.\n---\n\nbody\n", encoding="utf-8"
            )
        assert roles_in(core) == ("alpha", "mike", "zulu")

    def test_the_scaffold_reads_the_same_population(self) -> None:
        """One fact, one home — ``AGENT_FILES`` IS ``ROLE_NAMES``."""
        assert AGENT_FILES is ROLE_NAMES

    def test_every_role_has_a_vendored_asset(self) -> None:
        """``_scaffold_vendored`` reads one per role; a missing one would raise."""
        for role in ROLE_NAMES:
            assert _vendored_asset("agents", role)

    def test_the_cursor_pointer_names_the_derived_population(self) -> None:
        """The prose list inside the pointer was a third home for the same fact."""
        body = cursor_rules_body()
        for role in ROLE_NAMES:
            assert role in body
        assert f"{len(ROLE_NAMES)} roles" in body


class TestTheExploreRoleStatesAFixedDeliverable:
    """A mode has no protocol file, which is why the one Explore run returned prose."""

    @pytest.mark.parametrize("architecture", sorted(SUPPORTED_ARCHITECTURES))
    def test_it_composes_for_every_architecture(self, architecture: str) -> None:
        """An overlay is additive; no architecture may be missing its boundary text."""
        text = compose_role(AXES_ROLE, architecture=architecture, stack=("python",))
        assert f"## {AXES_HEADING}" in text
        assert "beadloom impact" in text

    def test_the_ddd_and_fsd_overlays_say_different_things(self) -> None:
        """The Node column means a domain in one methodology and a slice in the other."""
        ddd = compose_role(AXES_ROLE, architecture="ddd", stack=("python",))
        fsd = compose_role(AXES_ROLE, architecture="fsd", stack=("python",))
        assert ddd != fsd
        assert "bounded context" in ddd
        assert "slice" in fsd

    def test_the_role_is_read_only(self) -> None:
        """Its deliverable is a section it returns; a role that edits is a different one."""
        front = compose_role(AXES_ROLE, architecture="ddd", stack=("python",))
        tools = next(
            line for line in front.splitlines() if line.startswith("tools:")
        )
        assert "Write" not in tools
        assert "Edit" not in tools

    def test_it_refuses_to_decide_the_scope_column(self) -> None:
        """The derivation's half is the role's; the scope decision is the person's."""
        text = compose_role(AXES_ROLE, architecture="ddd", stack=("python",))
        assert "the person's" in text
        assert "narrative" in text.lower()

    def test_the_writing_standard_composes_into_it(self) -> None:
        """Every role carries the shared layer, and a new one must not miss it."""
        text = compose_role(AXES_ROLE, architecture="ddd", stack=("python",))
        assert "Writing standard" in text


class TestConfigCheckSeesTheFifthAdapter:
    """#191's shape: a hand-edited adapter silently recomposed, or never looked at."""

    def test_a_freshly_composed_adapter_is_clean(self, tmp_path: Path) -> None:
        project = _adopter(tmp_path)
        assert (project / ".claude" / "agents" / f"{AXES_ROLE}.md").is_file()
        assert not [
            drift for drift in _drifts(project) if AXES_ROLE in drift.file
        ]

    def test_a_hand_edited_adapter_is_reported(self, tmp_path: Path) -> None:
        # Arrange
        project = _adopter(tmp_path)
        adapter = project / ".claude" / "agents" / f"{AXES_ROLE}.md"
        adapter.write_text(
            adapter.read_text(encoding="utf-8") + "\nJust write a summary.\n",
            encoding="utf-8",
        )

        # Act + Assert
        assert [drift.file for drift in _drifts(project) if AXES_ROLE in drift.file]

    def test_a_deleted_adapter_is_reported_as_missing(self, tmp_path: Path) -> None:
        """The scaffold's present/missing split is where the second literal mattered."""
        # Arrange
        project = _adopter(tmp_path)
        (project / ".claude" / "agents" / f"{AXES_ROLE}.md").unlink()

        # Act + Assert
        assert [drift.file for drift in _drifts(project) if AXES_ROLE in drift.file]

    def test_the_composer_writes_one_adapter_per_role(self, tmp_path: Path) -> None:
        project = tmp_path / "acme"
        project.mkdir()
        config = FlowConfig(
            tools=("claude", "cursor"), architecture="ddd", stack=("python",)
        )
        result = generate_adapters(config, project)
        for tool in ("claude", "cursor"):
            assert len(result.agents[tool]) == len(ROLE_NAMES)
            assert any(AXES_ROLE in path for path in result.agents[tool])


class TestTheRoutingIsDerivedFromTaskInit:
    """The command cannot state a route the check does not police."""

    def test_the_shipped_command_declares_both_flows(self) -> None:
        routing = task_init_routing()
        assert routing.flow_of("bug") == SIMPLIFIED
        assert routing.flow_of("epic") == FULL
        assert routing.flow_of("nonesuch") is None
        assert routing.notes == ()

    def test_only_the_kinds_unique_to_a_route_identify_it(self) -> None:
        """``ACTIVE`` is written by both routes and identifies neither."""
        routing = task_init_routing()
        assert routing.simplified_kinds == frozenset({"BRIEF"})
        assert "ACTIVE" not in routing.simplified_kinds
        assert "ACTIVE" not in routing.full_kinds
        assert "RFC" in routing.full_kinds

    def test_the_explore_step_precedes_the_type_decision(self) -> None:
        """The second acceptance point, on the artifact rather than about it."""
        routing = task_init_routing()
        assert routing.explore_line is not None
        assert routing.decision_line is not None
        assert routing.explore_line < routing.decision_line
        assert routing.explore_precedes_the_decision
        assert AXES_ROLE in routing.explore_step.lower()

    def test_the_step_is_found_by_the_launch_and_not_by_its_title(self) -> None:
        """A step is the step that launches the role, whatever its heading says."""
        text = (
            "## Groundwork\n\nRun `Agent(subagent_type=\"explore\")` first.\n\n"
            "## Type detection\n\n"
            "| Type | Flow | Docs created |\n|---|---|---|\n"
            "| `bug` | Simplified: BRIEF | BRIEF, ACTIVE |\n"
        )
        routing = read_routing(text)
        assert routing.explore_step == "Groundwork"
        assert routing.explore_precedes_the_decision

    def test_a_command_with_no_routing_table_says_so(self) -> None:
        """An empty routing must not read as "no types are declared"."""
        routing = read_routing("## Type detection\n\nDecide by feel.\n")
        assert routing.routes == ()
        assert any("no routing table" in note for note in routing.notes)

    def test_a_command_that_launches_nothing_says_so(self) -> None:
        text = (
            "## Type detection\n\n"
            "| Type | Flow | Docs created |\n|---|---|---|\n"
            "| `bug` | Simplified: BRIEF | BRIEF, ACTIVE |\n"
        )
        routing = read_routing(text)
        assert routing.explore_line is None
        assert not routing.explore_precedes_the_decision
        assert any(AXES_ROLE in note for note in routing.notes)

    def test_a_step_stated_after_the_decision_does_not_precede_it(self) -> None:
        """The order is the point, so reversing it must change the answer."""
        text = (
            "## Type detection\n\n"
            "| Type | Flow | Docs created |\n|---|---|---|\n"
            "| `bug` | Simplified: BRIEF | BRIEF, ACTIVE |\n\n"
            "## Afterwards\n\nRun `Agent(subagent_type=\"explore\")`.\n"
        )
        routing = read_routing(text)
        assert routing.explore_line is not None
        assert not routing.explore_precedes_the_decision

    def test_a_project_layer_that_adds_a_type_is_policed_by_the_same_act(
        self, tmp_path: Path
    ) -> None:
        """The whole reason the table is read rather than restated."""
        # Arrange — a project fragment appending one more row
        project = tmp_path / "acme"
        fragment = project / ".beadloom" / "flow" / "commands"
        fragment.mkdir(parents=True)
        (fragment / "task-init.md").write_text(
            "\n## Local routes\n\n"
            "| Type | Flow | Docs created |\n|---|---|---|\n"
            "| `spike` | Simplified: NOTE → ACTIVE | NOTE, ACTIVE |\n",
            encoding="utf-8",
        )

        # Act
        routing = task_init_routing(
            config=DEFAULT_DOC_CONFIG, project_root=project
        )

        # Assert
        assert routing.flow_of("spike") == SIMPLIFIED
        assert "NOTE" in routing.simplified_kinds

    def test_the_command_it_reads_is_the_composed_one(self) -> None:
        """Not the vendored bytes: a project layer must be part of what is read."""
        composed = compose(*TASK_INIT_COMMAND, config=DEFAULT_DOC_CONFIG).text
        assert read_routing(composed).routes == task_init_routing().routes


class TestTheTypeIsCheckedAgainstTheAxes:
    """BDL-067: routed `bug`, one BRIEF, 28 beads, four nodes when finally derived."""

    @staticmethod
    def _axes(rows: list[tuple[str, str]]) -> str:
        lines = [
            f"## {AXES_HEADING}",
            "",
            "> **Derived by:** `beadloom impact src/pkg/thing.py` over `src/pkg`",
            "> **Seed:** `write_it` (effect `serialises-yaml`), under rule `r`",
            "> **Unresolved:** none",
            "",
            "| Axis | Node | Sites | In scope | Why |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| co-writers | {node} | 1 — `src/pkg/thing.py:1` | {scope} | measured |"
            for node, scope in rows
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _doc(key: str, kind: str, body: str = "") -> tuple[str, str]:
        return (
            f".claude/development/docs/features/{key}/{kind}.md",
            f"# {kind}\n\n## Problem\n\nBroken.\n\n{body}",
        )

    def test_a_simplified_item_with_no_axes_is_reported(self) -> None:
        report = check_work_item_types(
            [self._doc("A-1", "BRIEF"), self._doc("A-1", "ACTIVE")],
            simplified_kinds=frozenset({"BRIEF"}),
        )
        assert [f.check for f in report.findings] == [ROUTED_WITHOUT_AXES]
        assert report.work_items == 1

    def test_the_finding_names_the_document_that_identified_the_route(self) -> None:
        report = check_work_item_types(
            [self._doc("A-1", "ACTIVE"), self._doc("A-1", "BRIEF")],
            simplified_kinds=frozenset({"BRIEF"}),
        )
        assert report.findings[0].path.endswith("BRIEF.md")

    def test_axes_in_a_sibling_document_of_the_same_work_item_count(self) -> None:
        """The unit is the folder: a work item states its axes once, somewhere."""
        report = check_work_item_types(
            [
                self._doc("A-1", "BRIEF"),
                self._doc("A-1", "ACTIVE", self._axes([("graph-loader", "yes")])),
            ],
            simplified_kinds=frozenset({"BRIEF"}),
        )
        assert report.findings == ()

    def test_two_kept_nodes_do_not_support_the_simplified_route(self) -> None:
        report = check_work_item_types(
            [
                self._doc(
                    "A-2",
                    "BRIEF",
                    self._axes([("graph-loader", "yes"), ("cli-commands", "yes")]),
                )
            ],
            simplified_kinds=frozenset({"BRIEF"}),
        )
        assert [f.check for f in report.findings] == [ROUTE_NOT_SUPPORTED_BY_THE_AXES]
        assert "graph-loader" in report.findings[0].excerpt
        assert "cli-commands" in report.findings[0].excerpt

    def test_a_node_ruled_out_of_scope_is_not_counted(self) -> None:
        """The scope decision is the person's half, and the check reads it."""
        report = check_work_item_types(
            [
                self._doc(
                    "A-3",
                    "BRIEF",
                    self._axes([("graph-loader", "yes"), ("cli-commands", "no")]),
                )
            ],
            simplified_kinds=frozenset({"BRIEF"}),
        )
        assert report.findings == ()

    def test_one_node_named_by_two_kept_rows_is_one_node(self) -> None:
        report = check_work_item_types(
            [
                self._doc(
                    "A-4",
                    "BRIEF",
                    self._axes([("graph-loader", "yes"), ("graph-loader", "yes")]),
                )
            ],
            simplified_kinds=frozenset({"BRIEF"}),
        )
        assert report.findings == ()

    def test_the_full_route_is_judged_by_its_approvals(self) -> None:
        report = check_work_item_types(
            [self._doc("A-5", "RFC"), self._doc("A-5", "PRD")],
            simplified_kinds=frozenset({"BRIEF"}),
        )
        assert report.findings == ()
        assert report.work_items == 0

    def test_an_underivable_routing_judges_nothing_and_says_so(self) -> None:
        """Zero is the population, not the finding count over a population."""
        report = check_work_item_types(
            [self._doc("A-6", "BRIEF")], simplified_kinds=frozenset()
        )
        assert report.findings == ()
        assert report.work_items == 0

    def test_the_route_holds_one_node_and_the_number_is_stated(self) -> None:
        assert NODES_THE_SIMPLIFIED_ROUTE_HOLDS == 1


class TestOneFaultOneReporter:
    """`## Axes` is withdrawn from the peer-relative half and from nothing else."""

    _REQUIRED = ("Problem", AXES_HEADING)

    @staticmethod
    def _brief(key: str, body: str) -> tuple[str, str]:
        return (f".claude/development/docs/features/{key}/BRIEF.md", body)

    def test_the_peer_relative_half_no_longer_reports_the_axes(self) -> None:
        """Otherwise one absence would be reported by two checks with two units."""
        carries = f"# BRIEF\n\n## Problem\n\nx\n\n## {AXES_HEADING}\n\ny\n"
        documents = [
            self._brief("A-1", carries),
            self._brief("A-2", carries),
            self._brief("A-3", "# BRIEF\n\n## Problem\n\nx\n"),
        ]
        requirements = {"BRIEF": self._REQUIRED}
        with_axes = check_planning_sections(documents, requirements)
        without = check_planning_sections(
            documents,
            requirements,
            absence_reported_elsewhere={"BRIEF": frozenset({AXES_HEADING})},
        )
        assert any(AXES_HEADING in f.excerpt for f in with_axes.findings)
        assert not any(AXES_HEADING in f.excerpt for f in without.findings)

    def test_an_empty_axes_section_is_still_reported(self) -> None:
        """Withdrawing the requirement would have removed this with it."""
        report = check_planning_sections(
            [self._brief("A-1", f"# BRIEF\n\n## Problem\n\nx\n\n## {AXES_HEADING}\n")],
            {"BRIEF": self._REQUIRED},
            absence_reported_elsewhere={"BRIEF": frozenset({AXES_HEADING})},
        )
        assert [f.check for f in report.findings] == [EMPTY_SECTION]


class TestTheReportCarriesTheTwoChecksAndTheirPopulation:
    """A check reported as "0 findings" over a population of zero has verified nothing."""

    def test_both_checks_are_in_the_one_composition(self) -> None:
        assert ROUTED_WITHOUT_AXES in CHECK_NAMES
        assert ROUTE_NOT_SUPPORTED_BY_THE_AXES in CHECK_NAMES

    def test_the_population_counted_is_folders_and_not_documents(
        self, tmp_path: Path
    ) -> None:
        # Arrange — one work item, three documents
        features = tmp_path / ".claude" / "development" / "docs" / "features" / "A-1"
        features.mkdir(parents=True)
        for kind in ("BRIEF", "ACTIVE", "SUMMARY"):
            (features / f"{kind}.md").write_text(
                f"# {kind}\n\n## Problem\n\nx\n", encoding="utf-8"
            )

        # Act
        report = planning_report(
            sorted(features.glob("*.md")), project_root=tmp_path
        )

        # Assert
        assert report.applicable[ROUTED_WITHOUT_AXES] == 1
        assert report.documents == 3
        assert ROUTED_WITHOUT_AXES in {f.check for f in report.findings}

    def test_this_repository_enters_the_population(self) -> None:
        """A check that reads nothing here would be verified nowhere."""
        # Arrange
        from beadloom.application.doc_shape import planning_documents

        root = _repo_root()

        # Act
        report = planning_report(planning_documents(root), project_root=root)

        # Assert
        assert report.applicable[ROUTED_WITHOUT_AXES] > 0
        for finding in report.findings:
            if finding.check in {ROUTED_WITHOUT_AXES, ROUTE_NOT_SUPPORTED_BY_THE_AXES}:
                assert (root / finding.path).is_file(), finding.path


class TestTheLiveFlowCarriesTheRole:
    """This repository is the reference implementation; its own flow must hold."""

    def test_the_live_adapter_equals_its_composition(self) -> None:
        root = _repo_root()
        live = (root / ".claude" / "agents" / f"{AXES_ROLE}.md").read_text(
            encoding="utf-8"
        )
        assert live == compose_role(
            AXES_ROLE, architecture="ddd", stack=("python",), project_root=root
        )

    def test_the_live_command_equals_its_composition(self) -> None:
        root = _repo_root()
        live = (root / ".claude" / "commands" / "task-init.md").read_text(
            encoding="utf-8"
        )
        assert live == composed_command(
            "task-init", load_flow_config(root), root
        )
