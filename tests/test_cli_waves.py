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
    (project / ".beadloom").mkdir(parents=True)
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


def _measured_project(tmp_path: Path) -> Path:
    """A project in which all three machine-observed media can be measured clean.

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
    for args in (
        ["init"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "t"],
        ["add", ".gitignore"],
        ["commit", "-m", "base", "--no-verify"],
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

    def __init__(self, records: dict[str, dict[str, Any]]) -> None:
        self.records = records

    def __call__(self, args: list[str], *, cwd: str | None = None) -> Any:
        from beadloom.services.bd_seam import BdResult

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
    def _install(records: dict[str, dict[str, Any]]) -> None:
        monkeypatch.setattr(
            "beadloom.services.bd_seam.run_bd", _FakeBd(records), raising=True
        )

    return _install


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
            "working-tree",
            "commit-gate",
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
