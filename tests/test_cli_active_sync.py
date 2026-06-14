"""Tests for the `beadloom active-sync` command (BDL-053 BEAD-02).

The command reconciles each epic's ACTIVE.md bead-status table from ``bd``
(the source of truth), syncs the tracked ``.beads/issues.jsonl`` via ``bd
export`` in fix mode, and is a strict no-op when ``bd`` is unavailable or there
are no ACTIVE files with a bead table. ``bd`` is reached through
``beadloom.services.bd_seam.run_bd`` — patched here so no real ``bd`` /network is
needed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from click.testing import CliRunner

from beadloom.services.bd_seam import BdResult, BdUnavailableError
from beadloom.services.cli import _bd_statuses_from_list, main

if TYPE_CHECKING:
    from pathlib import Path


_ACTIVE_TABLE = """\
# ACTIVE: DEMO

## Beads

| Bead | Role | Status |
|------|------|--------|
| demo-a.1 | dev | ready |
| demo-a.2 | dev | in progress |
| demo-a.3 | review | ready |

## Progress Log
- something human-authored
"""


def _write_active(project: Path, epic: str, body: str = _ACTIVE_TABLE) -> Path:
    epic_dir = project / ".claude" / "development" / "docs" / "features" / epic
    epic_dir.mkdir(parents=True)
    path = epic_dir / "ACTIVE.md"
    path.write_text(body, encoding="utf-8")
    return path


def _bd_list_json(beads: list[dict[str, object]]) -> str:
    return json.dumps(beads)


def _result_ok(stdout: str) -> BdResult:
    return BdResult(returncode=0, stdout=stdout, stderr="")


# ---------------------------------------------------------------------------
# _bd_statuses_from_list — status derivation (blocked detection)
# ---------------------------------------------------------------------------


def test_bd_statuses_open_with_no_blocker_stays_open() -> None:
    beads = [{"id": "x.1", "status": "open", "dependency_count": 0, "dependencies": []}]
    assert _bd_statuses_from_list(beads) == {"x.1": "open"}


def test_bd_statuses_open_with_open_blocker_is_blocked() -> None:
    beads = [
        {"id": "x.1", "status": "open", "dependency_count": 0, "dependencies": []},
        {
            "id": "x.2",
            "status": "open",
            "dependency_count": 1,
            "dependencies": [{"type": "blocks", "depends_on_id": "x.1"}],
        },
    ]
    assert _bd_statuses_from_list(beads) == {"x.1": "open", "x.2": "blocked"}


def test_bd_statuses_open_with_closed_blocker_stays_open() -> None:
    beads = [
        {"id": "x.1", "status": "closed", "dependency_count": 0, "dependencies": []},
        {
            "id": "x.2",
            "status": "open",
            "dependency_count": 1,
            "dependencies": [{"type": "blocks", "depends_on_id": "x.1"}],
        },
    ]
    assert _bd_statuses_from_list(beads) == {"x.1": "closed", "x.2": "open"}


def test_bd_statuses_parent_child_dep_does_not_block() -> None:
    beads = [
        {"id": "x", "status": "open", "dependency_count": 0, "dependencies": []},
        {
            "id": "x.1",
            "status": "open",
            "dependency_count": 0,
            "dependencies": [{"type": "parent-child", "depends_on_id": "x"}],
        },
    ]
    assert _bd_statuses_from_list(beads) == {"x": "open", "x.1": "open"}


# ---------------------------------------------------------------------------
# fix mode — rewrites drifted Status cells from the mocked bd statuses
# ---------------------------------------------------------------------------


def test_fix_mode_rewrites_drifted_cells(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    beads = [
        {"id": "demo-a.1", "status": "closed", "dependencies": []},
        {"id": "demo-a.2", "status": "in_progress", "dependencies": []},
        {"id": "demo-a.3", "status": "open", "dependencies": []},
    ]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ):
        result = CliRunner().invoke(
            main, ["active-sync", "--project", str(tmp_path), "--no-export"]
        )
    assert result.exit_code == 0, result.output
    text = active.read_text(encoding="utf-8")
    assert "| demo-a.1 | dev | ✓ done |" in text
    # demo-a.2 already 'in progress' — unchanged; demo-a.3 stays 'ready'.
    assert "Progress Log" in text


def test_check_mode_exits_1_on_drift(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    before = active.read_text(encoding="utf-8")
    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ):
        result = CliRunner().invoke(main, ["active-sync", "--check", "--project", str(tmp_path)])
    assert result.exit_code == 1, result.output
    # --check must not write.
    assert active.read_text(encoding="utf-8") == before


def test_check_mode_exits_0_when_clean(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    beads = [
        {"id": "demo-a.1", "status": "open", "dependencies": []},
        {"id": "demo-a.2", "status": "in_progress", "dependencies": []},
        {"id": "demo-a.3", "status": "open", "dependencies": []},
    ]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ):
        result = CliRunner().invoke(main, ["active-sync", "--check", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output


def test_json_output_shape(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ):
        result = CliRunner().invoke(
            main, ["active-sync", "--json", "--project", str(tmp_path), "--no-export"]
        )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "changed_files" in payload
    assert "drifted_rows" in payload
    assert any(row["bead_id"] == "demo-a.1" for row in payload["drifted_rows"])


def test_epic_option_limits_to_one(tmp_path: Path) -> None:
    a = _write_active(tmp_path, "EPIC-A")
    b = _write_active(tmp_path, "EPIC-B")
    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ):
        result = CliRunner().invoke(
            main,
            ["active-sync", "--epic", "EPIC-A", "--project", str(tmp_path), "--no-export"],
        )
    assert result.exit_code == 0, result.output
    assert "✓ done" in a.read_text(encoding="utf-8")
    # EPIC-B untouched.
    assert "✓ done" not in b.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# no-op contract
# ---------------------------------------------------------------------------


def test_noop_when_bd_unavailable(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    before = active.read_text(encoding="utf-8")
    with patch(
        "beadloom.services.bd_seam.run_bd",
        side_effect=BdUnavailableError("no bd"),
    ):
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert active.read_text(encoding="utf-8") == before


def test_noop_when_bd_unavailable_check_mode(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    with patch(
        "beadloom.services.bd_seam.run_bd",
        side_effect=BdUnavailableError("no bd"),
    ):
        result = CliRunner().invoke(main, ["active-sync", "--check", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output


def test_noop_when_no_active_files(tmp_path: Path) -> None:
    # No .claude/development/docs/features/*/ACTIVE.md at all.
    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ) as mocked:
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # bd must not even be queried when there is no table to reconcile.
    mocked.assert_not_called()


# ---------------------------------------------------------------------------
# jsonl export — only when tracked + bd available
# ---------------------------------------------------------------------------


def _git(cwd: Path, *args: str) -> None:
    import subprocess

    subprocess.run(["git", *args], cwd=cwd, check=True)  # noqa: S603, S607


def _make_tracked_jsonl(tmp_path: Path) -> None:
    beads_dir = tmp_path / ".beads"
    beads_dir.mkdir()
    (beads_dir / "issues.jsonl").write_text("{}\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".beads/issues.jsonl")


def test_jsonl_export_called_when_tracked(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    _make_tracked_jsonl(tmp_path)
    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    calls: list[list[str]] = []

    def fake_run_bd(args: list[str], *, cwd: str | None = None) -> BdResult:
        calls.append(args)
        if args[0] == "list":
            return _result_ok(_bd_list_json(beads))
        return _result_ok("")

    with patch("beadloom.services.bd_seam.run_bd", side_effect=fake_run_bd):
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert any(c[:1] == ["export"] for c in calls), calls


def test_jsonl_export_skipped_when_not_tracked(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    calls: list[list[str]] = []

    def fake_run_bd(args: list[str], *, cwd: str | None = None) -> BdResult:
        calls.append(args)
        return _result_ok(_bd_list_json(beads))

    with patch("beadloom.services.bd_seam.run_bd", side_effect=fake_run_bd):
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert not any(c[:1] == ["export"] for c in calls), calls


def test_no_export_flag_skips_export(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    _make_tracked_jsonl(tmp_path)
    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    calls: list[list[str]] = []

    def fake_run_bd(args: list[str], *, cwd: str | None = None) -> BdResult:
        calls.append(args)
        return _result_ok(_bd_list_json(beads))

    with patch("beadloom.services.bd_seam.run_bd", side_effect=fake_run_bd):
        result = CliRunner().invoke(
            main, ["active-sync", "--project", str(tmp_path), "--no-export"]
        )
    assert result.exit_code == 0, result.output
    assert not any(c[:1] == ["export"] for c in calls), calls


def test_check_mode_does_not_export(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    _make_tracked_jsonl(tmp_path)
    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    calls: list[list[str]] = []

    def fake_run_bd(args: list[str], *, cwd: str | None = None) -> BdResult:
        calls.append(args)
        return _result_ok(_bd_list_json(beads))

    with patch("beadloom.services.bd_seam.run_bd", side_effect=fake_run_bd):
        CliRunner().invoke(main, ["active-sync", "--check", "--project", str(tmp_path)])
    assert not any(c[:1] == ["export"] for c in calls), calls


# ---------------------------------------------------------------------------
# --stage — git add EXACTLY the reconciled ACTIVE.md(s) + the jsonl, nothing else
# ---------------------------------------------------------------------------


def _git_out(cwd: Path, *args: str) -> str:
    import subprocess

    out = subprocess.run(  # noqa: S603
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True  # noqa: S607
    )
    return out.stdout


def _staged_paths(cwd: Path) -> set[str]:
    """Paths currently in the git index (staged)."""
    out = _git_out(cwd, "diff", "--cached", "--name-only")
    return {line for line in out.splitlines() if line}


def _init_repo(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")


def test_stage_stages_only_reconciled_active_not_unrelated_doc(tmp_path: Path) -> None:
    """The over-staging bug pinned: a concurrently-edited sibling doc in the same
    features subtree must NOT be staged — only the reconciled ACTIVE.md is."""
    active = _write_active(tmp_path, "DEMO")
    # An unrelated, concurrently-modified doc in the SAME features subtree.
    unrelated = active.parent / "CONTEXT.md"
    unrelated.write_text("original\n", encoding="utf-8")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline")
    # Now dirty the unrelated doc in the working tree (NOT staged).
    unrelated.write_text("concurrent edit\n", encoding="utf-8")

    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ):
        result = CliRunner().invoke(
            main, ["active-sync", "--stage", "--project", str(tmp_path), "--no-export"]
        )
    assert result.exit_code == 0, result.output
    rel_active = "/".join(active.relative_to(tmp_path).parts)
    rel_unrelated = "/".join(unrelated.relative_to(tmp_path).parts)
    staged = _staged_paths(tmp_path)
    assert rel_active in staged, staged
    assert rel_unrelated not in staged, staged


def test_stage_stages_exported_jsonl(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    beads_dir = tmp_path / ".beads"
    beads_dir.mkdir()
    (beads_dir / "issues.jsonl").write_text("{}\n", encoding="utf-8")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline")

    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]

    def fake_run_bd(args: list[str], *, cwd: str | None = None) -> BdResult:
        if args[0] == "list":
            return _result_ok(_bd_list_json(beads))
        if args[0] == "export":
            # Simulate bd writing a fresh jsonl.
            (beads_dir / "issues.jsonl").write_text('{"id":"demo-a.1"}\n', encoding="utf-8")
            return _result_ok("")
        return _result_ok("")

    with patch("beadloom.services.bd_seam.run_bd", side_effect=fake_run_bd):
        result = CliRunner().invoke(
            main, ["active-sync", "--stage", "--project", str(tmp_path)]
        )
    assert result.exit_code == 0, result.output
    staged = _staged_paths(tmp_path)
    rel_active = "/".join(active.relative_to(tmp_path).parts)
    assert ".beads/issues.jsonl" in staged, staged
    assert rel_active in staged, staged


def test_stage_noop_when_nothing_reconciled(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    unrelated = active.parent / "CONTEXT.md"
    unrelated.write_text("original\n", encoding="utf-8")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline")
    unrelated.write_text("concurrent edit\n", encoding="utf-8")

    # bd agrees with every cell -> no drift, nothing reconciled.
    beads = [
        {"id": "demo-a.1", "status": "open", "dependencies": []},
        {"id": "demo-a.2", "status": "in_progress", "dependencies": []},
        {"id": "demo-a.3", "status": "open", "dependencies": []},
    ]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ):
        result = CliRunner().invoke(
            main, ["active-sync", "--stage", "--project", str(tmp_path), "--no-export"]
        )
    assert result.exit_code == 0, result.output
    # Nothing reconciled -> nothing staged at all.
    assert _staged_paths(tmp_path) == set()


def test_stage_best_effort_when_not_a_git_repo(tmp_path: Path) -> None:
    """No git repo -> --stage skips staging silently and still exits 0."""
    _write_active(tmp_path, "DEMO")
    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ):
        result = CliRunner().invoke(
            main, ["active-sync", "--stage", "--project", str(tmp_path), "--no-export"]
        )
    assert result.exit_code == 0, result.output


def test_stage_is_a_noop_in_check_mode(tmp_path: Path) -> None:
    """--check never writes, so --stage stages nothing even if combined."""
    active = _write_active(tmp_path, "DEMO")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline")
    active.write_text(_ACTIVE_TABLE, encoding="utf-8")  # keep clean working tree

    beads = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_result_ok(_bd_list_json(beads)),
    ):
        result = CliRunner().invoke(
            main, ["active-sync", "--check", "--stage", "--project", str(tmp_path)]
        )
    # --check exits 1 on drift; nothing is staged.
    assert result.exit_code == 1, result.output
    assert _staged_paths(tmp_path) == set()
