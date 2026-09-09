"""`beadloom waves` — the two output shapes, the three exit codes, the tracker seam.

The command is presentation and wiring; what it must not get wrong is that the
human shape and `--json` carry the SAME facts, that neither depends on whether
stdout is a terminal, and that an unanswerable request is exit 2 rather than a
confident shape built on nothing (BDL-UX #148).
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main
from beadloom.services.commands.docsync import _HOOK_TEMPLATE_WARN

if TYPE_CHECKING:
    from pathlib import Path

_EXIT_CLEAN = 0
_EXIT_FINDINGS = 1
_EXIT_UNDECIDABLE = 2


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    # The graph file as well as the index, because the plan derives its scopes
    # from the index and the `graph-files` medium asks whether that index still
    # agrees with the files it was built from (BDL-UX #261). A project holding
    # only one of the two homes is a project whose graph nobody could read.
    (project / ".beadloom" / "_graph" / "services.yml").write_text(
        "nodes:\n"
        + "".join(
            f"  - ref_id: {ref}\n    kind: feature\n    source: src/{ref}/\n"
            for ref in ("billing", "shipping")
        ),
        encoding="utf-8",
    )
    conn = open_db(project / ".beadloom" / "beadloom.db")
    create_schema(conn)
    for ref in ("billing", "shipping"):
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref, "feature", ref, f"src/{ref}/"),
        )
    conn.commit()
    conn.close()
    return project


#: The work item the measured project's branch names, so the declarations the
#: plan rests on are held against a recorded derivation rather than against
#: nothing. Before BDL-UX #232 there was nothing to hold them against, and a
#: concurrent wave whose declarations nobody compared reached exit 0.
_WORK_ITEM = "KEY-1"


def _work_item(project: Path) -> None:
    """A planning document declaring both this project's nodes in scope."""
    folder = project / ".claude" / "development" / "docs" / "features" / _WORK_ITEM
    folder.mkdir(parents=True)
    (folder / "RFC.md").write_text(
        "# RFC\n\n## Axes\n\n"
        "> **Derived by:** `beadloom impact` over `src/billing/core.py`\n"
        "> **Seed:** `none`\n"
        "> **Unresolved:** none\n\n"
        "| Axis | Node | Sites | In scope | Why |\n|---|---|---|---|---|\n"
        "| callers | `billing` | 1 | yes | the bead edits it |\n"
        "| callers | `shipping` | 1 | yes | the other bead edits it |\n",
        encoding="utf-8",
    )


def _measured_project(tmp_path: Path) -> Path:
    """A project in which every plan-time precondition can be measured clean.

    A branch naming a work item whose `## Axes` keeps both nodes in scope, so
    the fourth thing a clean plan rests on — that the declarations were held
    against the derivation they should have been generated from — is measured
    here too rather than defaulted past (BDL-UX #232).

    A real git repository with one commit, `.beadloom/` ignored so the index is
    not read as an uncommitted change, and a pre-commit hook carrying the scope
    marker. The command reads all three from the machine, so a double would prove
    the double — this is the same reason the commit-scope scenarios run against a
    real repository rather than a fake one.
    """
    project = _project(tmp_path)
    (project / ".gitignore").write_text(".beadloom/\n", encoding="utf-8")
    (project / ".git" / "hooks").mkdir(parents=True)
    (project / ".git" / "hooks" / "pre-commit").write_text(
        _HOOK_TEMPLATE_WARN, encoding="utf-8"
    )
    _work_item(project)
    for args in (
        ["init"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "t"],
        ["add", ".gitignore", ".claude"],
        ["commit", "-m", "base", "--no-verify"],
        ["switch", "-c", f"features/{_WORK_ITEM}"],
    ):
        subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=project,
            check=True,
            capture_output=True,
        )
    return project


class _FakeBd:
    """A stand-in for the `bd` binary: bead id -> the record it answers with.

    A double here proves the double's contract and nothing else (FAKES PROVE
    FAKES) — which is exactly the right scope for this test, because what it
    checks is the COMMAND's rendering and exit codes. The real seam is covered by
    `tests/test_bd_seam.py`, and the shape of a real `bd show --json` record is
    pinned by `test_the_record_shape_this_command_reads_is_the_one_bd_emits`.
    """

    def __init__(
        self,
        records: dict[str, dict[str, Any]],
        census: list[dict[str, Any]] | None = None,
        ready: list[str] | None = None,
        ready_stderr: str = "",
    ) -> None:
        self.records = records
        self.census = census
        self.ready = ready
        self.ready_stderr = ready_stderr

    def __call__(self, args: list[str], *, cwd: str | None = None) -> Any:
        from beadloom.services.bd_seam import BdResult

        if args[0] == "list":
            if self.census is None:
                return BdResult(returncode=1, stdout="", stderr="no tracker")
            return BdResult(returncode=0, stdout=json.dumps(self.census), stderr="")
        if args[0] == "ready":
            if self.ready is None:
                return BdResult(returncode=1, stdout="", stderr="no tracker")
            return BdResult(
                returncode=0,
                stdout=json.dumps([{"id": bead} for bead in self.ready]),
                stderr=self.ready_stderr,
            )
        bead = args[1]
        if bead not in self.records:
            return BdResult(returncode=1, stdout="", stderr=f"no such issue: {bead}")
        return BdResult(
            returncode=0, stdout=json.dumps([self.records[bead]]), stderr=""
        )


def _record(bead: str, refs: str = "", deps: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {
        "id": bead,
        "title": f"[{bead}] work",
        "description": f"do the work.\nrefs: {refs}" if refs else "do the work.",
        "dependencies": deps or [],
    }


@pytest.fixture()
def bd(monkeypatch: pytest.MonkeyPatch) -> Any:
    def _install(
        records: dict[str, dict[str, Any]],
        census: list[dict[str, Any]] | None = None,
        ready: list[str] | None = None,
        ready_stderr: str = "",
    ) -> None:
        monkeypatch.setattr(
            "beadloom.services.bd_seam.run_bd",
            _FakeBd(records, census, ready, ready_stderr),
            raising=True,
        )

    return _install


def _census_row(
    bead: str, parent: str = "", depends_on: tuple[str, ...] = ()
) -> dict[str, Any]:
    """One row in `bd list --all --json`'s own spelling of a dependency.

    `bd list` writes `type` and `depends_on_id`; `bd show` writes
    `dependency_type` and `id` for the same edge. Pinned in the double because
    reading the wrong pair would silently make every population empty.
    """
    return {
        "id": bead,
        "parent": parent or None,
        "dependencies": [
            {"issue_id": bead, "depends_on_id": other, "type": "blocks"}
            for other in depends_on
        ],
    }


class TestShape:
    def test_independent_beads_land_in_one_wave_at_exit_zero(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The shape is decided AND every shared medium was measured clean."""
        project = _measured_project(tmp_path)
        bd({"a": _record("a", "billing"), "b": _record("b", "shipping")})
        result = CliRunner().invoke(
            main, ["waves", "a", "b", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_CLEAN
        assert "1 wave(s) for 2 bead(s)" in result.output
        assert "Wave 1: a, b" in result.output

    def test_a_concurrent_wave_nobody_measured_does_not_reach_exit_zero(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The same two beads outside a git repository: same shape, exit 1.

        Nothing about the wave changed — what changed is that neither the tree nor
        the hook could be observed. Before `.80` this ran at exit 0 with the four
        media printed as a constant tuple beside it. The doc baseline is measured
        even here, because it is read from the index rather than from git, and it
        is reported as measured rather than folded in with the two that were not.
        """
        project = _project(tmp_path)
        bd({"a": _record("a", "billing"), "b": _record("b", "shipping")})
        result = CliRunner().invoke(
            main, ["waves", "a", "b", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_FINDINGS
        assert "Wave 1: a, b" in result.output
        for medium in ("working-tree", "commit-gate"):
            assert f"medium_unmeasured: {medium}" in result.output
        assert "doc-baseline: passed" in result.output

    def test_a_shared_node_serialises_and_the_reason_is_printed(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """A measured project, because a serial plan is checked too (#228).

        It ran against `_project` until the media stopped being conditional on
        wave size: a plan whose three machine-observed media nobody could measure
        is `unmeasured` at exit 1 whether or not any wave holds two beads.
        """
        project = _measured_project(tmp_path)
        bd({"a": _record("a", "billing"), "b": _record("b", "billing")})
        result = CliRunner().invoke(
            main, ["waves", "a", "b", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_CLEAN
        assert "2 wave(s)" in result.output
        assert "shared_node: billing" in result.output

    def test_an_undeclared_scope_is_exit_one_with_a_finding(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _project(tmp_path)
        bd({"a": _record("a", "billing"), "b": _record("b")})
        result = CliRunner().invoke(
            main, ["waves", "a", "b", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_FINDINGS
        assert "FINDING: unresolved_scope: b" in result.output


class TestOneContractForEveryCaller:
    def test_json_and_the_human_shape_agree_on_every_count(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _project(tmp_path)
        bd({"a": _record("a", "billing"), "b": _record("b", "billing")})
        runner = CliRunner()
        human = runner.invoke(main, ["waves", "a", "b", "--project", str(project)])
        machine = runner.invoke(
            main, ["waves", "a", "b", "--json", "--project", str(project)]
        )
        payload = json.loads(machine.stdout)
        assert machine.exit_code == human.exit_code == payload["exit_code"]
        assert f"{len(payload['waves'])} wave(s)" in human.output
        assert f"{len(payload['conflicts'])} serialisation(s)" in human.output
        assert f"{len(payload['findings'])} finding(s)" in human.output

    def test_the_summary_line_survives_a_pipe(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The shape must not depend on whether a human is watching (#148)."""
        project = _project(tmp_path)
        bd({"a": _record("a", "billing"), "b": _record("b", "shipping")})
        runner = CliRunner()
        piped = runner.invoke(
            main, ["waves", "a", "b", "--project", str(project)], color=False
        )
        assert "wave(s) for 2 bead(s)" in piped.output

    def test_a_concurrent_wave_prints_its_shared_media_and_gate_owner(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _project(tmp_path)
        bd({"a": _record("a", "billing"), "b": _record("b", "shipping")})
        result = CliRunner().invoke(
            main, ["waves", "a", "b", "--json", "--project", str(project)]
        )
        payload = json.loads(result.stdout)
        assert {m["name"] for m in payload["shared_media"]} == {
            "graph-files",
            "working-tree",
            "commit-gate",
            "landing-order",
            "focus-document",
            "doc-baseline",
            "tracker-ids",
        }
        assert payload["waves"][0]["gate_owner"] in payload["waves"][0]["beads"]


class TestUndecidable:
    def test_no_index_is_exit_two(self, tmp_path: Path, bd: Any) -> None:
        project = tmp_path / "bare"
        (project / ".beadloom").mkdir(parents=True)
        bd({})
        result = CliRunner().invoke(
            main, ["waves", "a", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_UNDECIDABLE
        assert "database not found" in result.output

    def test_a_bead_the_tracker_does_not_have_is_exit_two(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _project(tmp_path)
        bd({"a": _record("a", "billing")})
        result = CliRunner().invoke(
            main, ["waves", "a", "ghost", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_UNDECIDABLE
        assert "no bead 'ghost'" in result.output

    def test_a_waves_block_that_cannot_be_used_is_exit_two(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _project(tmp_path)
        (project / ".beadloom" / "flow.yml").write_text(
            "waves:\n  overrides:\n  - beads: [a, b]\n    decision: parallel\n",
            encoding="utf-8",
        )
        bd({"a": _record("a", "billing"), "b": _record("b", "shipping")})
        result = CliRunner().invoke(
            main, ["waves", "a", "b", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_UNDECIDABLE
        assert "no wave shape could be decided" in result.output


class TestTrackerSeam:
    def test_the_record_shape_this_command_reads_is_the_one_bd_emits(self) -> None:
        """The fields the command reads out of a real `bd show --json` record.

        Pinned here because the double above cannot fail when the tracker's
        vocabulary moves. The names come from bd 1.0.4's own output.
        """
        from beadloom.application.waves import compose_declaration
        from beadloom.services.commands.waves import _blocked_by

        record = {
            "id": "x.1",
            "title": "t",
            "description": "d.\nrefs: billing",
            "notes": "n",
            "dependencies": [
                {"id": "x", "dependency_type": "parent-child", "status": "open"},
                {"id": "x.0", "dependency_type": "blocks", "status": "closed"},
                {"id": "x.2", "dependency_type": "blocks", "status": "open"},
            ],
        }
        assert _blocked_by(record) == frozenset({"x.2"})
        assert "refs: billing" in compose_declaration(record)

    def test_an_open_parent_link_never_blocks_its_child(self) -> None:
        from beadloom.services.commands.waves import _blocked_by

        record = {
            "dependencies": [
                {"id": "epic", "dependency_type": "parent-child", "status": "open"}
            ]
        }
        assert _blocked_by(record) == frozenset()


class TestThePopulationItWasNotAskedAbout:
    """BDL-UX #274 — the plan derives which beads may run at once, and used to
    take WHICH BEADS from whatever the caller typed.

    The measured instance is this project's own coordinator: three beads of
    BDL-068's S6 sat in `bd ready --limit 0` through fifteen launches and were
    never named. Every plan was internally correct about the smaller world it
    was asked about, and none of them could say the world was smaller.
    """

    def test_a_plan_over_part_of_the_ready_population_says_how_many_it_left_out(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _measured_project(tmp_path)
        bd(
            {"a": _record("a", "billing"), "b": _record("b", "shipping")},
            census=[
                _census_row("epic", depends_on=("a", "b", "c")),
                _census_row("a", parent="epic"),
                _census_row("b", parent="epic"),
                _census_row("c", parent="epic"),
            ],
            ready=["a", "b", "c"],
        )
        result = CliRunner().invoke(
            main, ["waves", "a", "b", "--project", str(project)]
        )
        assert "1 ready bead(s) this plan was not asked about: c" in result.output
        assert "epic" in result.output

    def test_the_narrowing_is_reported_and_is_not_a_finding(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """15 of 15 of this epic's own S6 launches were subsets, so a finding
        here would go red on every real run and teach its reader to discount it."""
        project = _measured_project(tmp_path)
        bd(
            {"a": _record("a", "billing")},
            census=[
                _census_row("epic", depends_on=("a", "c")),
                _census_row("a", parent="epic"),
                _census_row("c", parent="epic"),
            ],
            ready=["a", "c"],
        )
        result = CliRunner().invoke(main, ["waves", "a", "--project", str(project)])
        assert result.exit_code == _EXIT_CLEAN
        assert "not asked about: c" in result.output

    def test_a_bead_reaching_the_work_item_only_through_a_blocking_edge_is_counted(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The shape that was actually lost: two of the three beads had no
        parent link at all and belonged to the slice by blocking it."""
        project = _measured_project(tmp_path)
        bd(
            {"a": _record("a", "billing")},
            census=[
                _census_row("epic", depends_on=("a", "orphan")),
                _census_row("a", parent="epic"),
                _census_row("orphan"),
            ],
            ready=["a", "orphan"],
        )
        result = CliRunner().invoke(main, ["waves", "a", "--project", str(project)])
        assert "not asked about: orphan" in result.output

    def test_parent_derives_the_bead_list_instead_of_taking_it_from_the_caller(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _measured_project(tmp_path)
        bd(
            {"a": _record("a", "billing"), "b": _record("b", "shipping")},
            census=[
                _census_row("epic", depends_on=("a", "b")),
                _census_row("a", parent="epic"),
                _census_row("b", parent="epic"),
            ],
            ready=["a", "b"],
        )
        result = CliRunner().invoke(
            main, ["waves", "--parent", "epic", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_CLEAN
        assert "Wave 1: a, b" in result.output
        assert "every ready bead under epic is in this plan" in result.output

    def test_a_parent_the_tracker_cannot_answer_for_is_exit_two(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """A derived list nobody could derive is not a plan of no beads."""
        project = _measured_project(tmp_path)
        bd({"a": _record("a", "billing")})
        result = CliRunner().invoke(
            main, ["waves", "--parent", "epic", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_UNDECIDABLE
        assert "could not be derived" in result.output

    def test_naming_neither_a_bead_nor_a_parent_is_exit_two(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _measured_project(tmp_path)
        bd({})
        result = CliRunner().invoke(main, ["waves", "--project", str(project)])
        assert result.exit_code == _EXIT_UNDECIDABLE
        assert "--parent" in result.output

    def test_a_tracker_that_cannot_answer_leaves_the_population_unstated(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """Not a comfortable zero: the plan says it held its list against nothing."""
        project = _measured_project(tmp_path)
        bd({"a": _record("a", "billing")})
        result = CliRunner().invoke(main, ["waves", "a", "--project", str(project)])
        assert result.exit_code == _EXIT_CLEAN
        assert "gathered no tracker census" in result.output

    def test_a_capped_ready_answer_makes_the_count_a_claim_about_part(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The one thing here that can fail is this report's own population."""
        project = _measured_project(tmp_path)
        bd(
            {"a": _record("a", "billing")},
            census=[
                _census_row("epic", depends_on=("a", "c")),
                _census_row("a", parent="epic"),
                _census_row("c", parent="epic"),
            ],
            ready=["a", "c"],
            ready_stderr="Showing 100 of 120 ready issues.",
        )
        result = CliRunner().invoke(main, ["waves", "a", "--project", str(project)])
        assert result.exit_code == _EXIT_FINDINGS
        assert "FINDING: population_not_whole" in result.output

    def test_json_and_the_human_shape_agree_about_the_population(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _measured_project(tmp_path)
        records = {"a": _record("a", "billing")}
        census = [
            _census_row("epic", depends_on=("a", "c")),
            _census_row("a", parent="epic"),
            _census_row("c", parent="epic"),
        ]
        runner = CliRunner()
        bd(records, census=census, ready=["a", "c"])
        human = runner.invoke(main, ["waves", "a", "--project", str(project)])
        bd(records, census=census, ready=["a", "c"])
        machine = runner.invoke(
            main, ["waves", "a", "--json", "--project", str(project)]
        )
        payload = json.loads(machine.stdout)["population"]
        assert payload["work_item"] == "epic"
        assert payload["unasked"] == ["c"]
        assert payload["work_item"] in human.output
        assert f"{len(payload['unasked'])} ready bead(s)" in human.output
