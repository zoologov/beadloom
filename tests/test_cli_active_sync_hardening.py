"""Hardening tests for `beadloom active-sync` + the coherence hook (BEAD-03).

Focus: the NO-OP CONTRACT (adopter safety — "works for every new user") and the
fix/check/json/export branches not already covered by ``test_cli_active_sync.py``.
Everything is deterministic: ``bd`` is reached only through
``beadloom.services.bd_seam.run_bd`` (patched), git repos are local ``git init``
sandboxes, and no network is used.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from beadloom.services.bd_seam import BdResult, BdUnavailableError
from beadloom.services.cli import (
    _bd_statuses_from_list,
    _has_active_table,
    _jsonl_is_tracked,
    _query_bd_statuses,
    main,
)

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


def _ok(stdout: str) -> BdResult:
    return BdResult(returncode=0, stdout=stdout, stderr="")


def _bd_json(beads: list[dict[str, object]]) -> str:
    return json.dumps(beads)


# ===========================================================================
# NO-OP CONTRACT — adopter safety
# ===========================================================================


def test_noop_bd_unavailable_writes_nothing_and_exits_zero(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    before = active.read_text(encoding="utf-8")
    with patch(
        "beadloom.services.bd_seam.run_bd", side_effect=BdUnavailableError("no bd")
    ):
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert active.read_text(encoding="utf-8") == before
    assert "skipped" in result.output.lower()


def test_noop_bd_unavailable_check_mode_exits_zero_no_write(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    before = active.read_text(encoding="utf-8")
    with patch(
        "beadloom.services.bd_seam.run_bd", side_effect=BdUnavailableError("no bd")
    ):
        result = CliRunner().invoke(
            main, ["active-sync", "--check", "--project", str(tmp_path)]
        )
    # Even in check mode, bd-less must be a clean exit 0 (never the drift code 1).
    assert result.exit_code == 0, result.output
    assert active.read_text(encoding="utf-8") == before


def test_noop_flowless_repo_does_not_even_query_bd(tmp_path: Path) -> None:
    # A temp project with NO features/*/ACTIVE.md: bd must not be invoked at all.
    with patch("beadloom.services.bd_seam.run_bd") as mocked:
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    mocked.assert_not_called()


def test_noop_active_present_but_no_bead_table(tmp_path: Path) -> None:
    # ACTIVE.md exists but has no bead-status table -> skip, never query bd.
    epic_dir = tmp_path / ".claude" / "development" / "docs" / "features" / "DEMO"
    epic_dir.mkdir(parents=True)
    (epic_dir / "ACTIVE.md").write_text("# ACTIVE\n\nJust prose, no table.\n", "utf-8")
    with patch("beadloom.services.bd_seam.run_bd") as mocked:
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    mocked.assert_not_called()


def test_noop_untracked_jsonl_no_export_attempted(tmp_path: Path) -> None:
    # .beads/issues.jsonl absent -> fix mode must NOT call `bd export`.
    _write_active(tmp_path, "DEMO")
    beads: list[dict[str, object]] = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    calls: list[list[str]] = []

    def fake(args: list[str], *, cwd: str | None = None) -> BdResult:
        calls.append(args)
        return _ok(_bd_json(beads))

    with patch("beadloom.services.bd_seam.run_bd", side_effect=fake):
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert not any(c[:1] == ["export"] for c in calls), calls


# ===========================================================================
# _query_bd_statuses fail-safe branches (drive the no-op decision)
# ===========================================================================


def test_query_bd_statuses_returns_none_when_unavailable(tmp_path: Path) -> None:
    with patch(
        "beadloom.services.bd_seam.run_bd", side_effect=BdUnavailableError("x")
    ):
        assert _query_bd_statuses(tmp_path) is None


def test_query_bd_statuses_returns_none_on_nonzero_rc(tmp_path: Path) -> None:
    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=BdResult(returncode=2, stdout="", stderr="boom"),
    ):
        assert _query_bd_statuses(tmp_path) is None


def test_query_bd_statuses_returns_none_on_bad_json(tmp_path: Path) -> None:
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok("not json{")):
        assert _query_bd_statuses(tmp_path) is None


def test_query_bd_statuses_returns_none_on_non_list_json(tmp_path: Path) -> None:
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok('{"id": "x"}')):
        assert _query_bd_statuses(tmp_path) is None


def test_query_bd_statuses_skips_non_dict_entries(tmp_path: Path) -> None:
    payload = json.dumps([{"id": "x.1", "status": "open", "dependencies": []}, "junk", 7])
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok(payload)):
        assert _query_bd_statuses(tmp_path) == {"x.1": "open"}


# ===========================================================================
# _bd_statuses_from_list — defensive parsing of malformed payloads
# ===========================================================================


def test_bd_statuses_skips_entries_missing_id_or_status() -> None:
    beads: list[dict[str, object]] = [
        {"status": "open"},  # no id
        {"id": "x.1"},  # no status
        {"id": "x.2", "status": "closed", "dependencies": []},
    ]
    assert _bd_statuses_from_list(beads) == {"x.2": "closed"}


def test_bd_statuses_ignores_malformed_dependency_entries() -> None:
    beads: list[dict[str, object]] = [
        {"id": "x.1", "status": "open", "dependencies": []},
        {
            "id": "x.2",
            "status": "open",
            "dependencies": [
                "notadict",
                {"type": "blocks"},
                {"type": "blocks", "depends_on_id": 5},
            ],
        },
    ]
    # No well-formed open blocker -> x.2 stays open (malformed deps ignored).
    assert _bd_statuses_from_list(beads) == {"x.1": "open", "x.2": "open"}


def test_bd_statuses_non_list_dependencies_treated_as_none() -> None:
    beads: list[dict[str, object]] = [{"id": "x.1", "status": "open", "dependencies": "oops"}]
    assert _bd_statuses_from_list(beads) == {"x.1": "open"}


# ===========================================================================
# _jsonl_is_tracked / _has_active_table fail-safe branches
# ===========================================================================


def test_jsonl_is_tracked_false_when_absent(tmp_path: Path) -> None:
    # No .beads/issues.jsonl -> not tracked (git never queried).
    assert _jsonl_is_tracked(tmp_path) is False


def test_jsonl_is_tracked_false_on_subprocess_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    beads_dir = tmp_path / ".beads"
    beads_dir.mkdir()
    (beads_dir / "issues.jsonl").write_text("{}\n", encoding="utf-8")

    def boom(*a: object, **k: object) -> object:
        raise OSError("git missing")

    monkeypatch.setattr("subprocess.run", boom)
    assert _jsonl_is_tracked(tmp_path) is False


def test_jsonl_is_tracked_false_when_not_in_index(tmp_path: Path) -> None:
    # File exists, git repo exists, but the file is NOT added -> untracked.
    beads_dir = tmp_path / ".beads"
    beads_dir.mkdir()
    (beads_dir / "issues.jsonl").write_text("{}\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    assert _jsonl_is_tracked(tmp_path) is False


def test_has_active_table_skips_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_active(tmp_path, "DEMO")

    def boom(self: Path, *a: object, **k: object) -> str:
        raise OSError("unreadable")

    monkeypatch.setattr("pathlib.Path.read_text", boom)
    # Read failure on the only candidate -> treated as 'no table'.
    assert _has_active_table(tmp_path, None) is False


def test_check_mode_no_features_dir_is_clean(tmp_path: Path) -> None:
    # Active table present under an epic, but --check for a DIFFERENT epic whose
    # features dir does not exist -> no drift, exit 0 (sandbox copytree skipped).
    _write_active(tmp_path, "DEMO")
    beads: list[dict[str, object]] = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok(_bd_json(beads))):
        result = CliRunner().invoke(
            main, ["active-sync", "--check", "--epic", "GHOST", "--project", str(tmp_path)]
        )
    # --epic GHOST has no ACTIVE table -> skipped before bd query, exit 0.
    assert result.exit_code == 0, result.output


# ===========================================================================
# reconcile correctness through the command (rich-note preservation etc.)
# ===========================================================================


def test_fix_preserves_rich_note_when_state_agrees(tmp_path: Path) -> None:
    body = (
        "## Beads\n\n"
        "| Bead | Role | Status |\n|---|---|---|\n"
        "| demo-a.1 | review | ✓ done (PASS-WITH-FIXES) |\n"
    )
    active = _write_active(tmp_path, "DEMO", body)
    before = active.read_text(encoding="utf-8")
    beads: list[dict[str, object]] = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok(_bd_json(beads))):
        result = CliRunner().invoke(
            main, ["active-sync", "--project", str(tmp_path), "--no-export"]
        )
    assert result.exit_code == 0, result.output
    # bd=closed agrees with the rich '✓ done (...)' cell -> byte-unchanged.
    assert active.read_text(encoding="utf-8") == before


def test_fix_open_with_open_blocker_renders_blocked(tmp_path: Path) -> None:
    body = (
        "## Beads\n\n"
        "| Bead | Role | Status |\n|---|---|---|\n"
        "| demo-a.1 | dev | ready |\n"
        "| demo-a.2 | dev | ready |\n"
    )
    active = _write_active(tmp_path, "DEMO", body)
    beads: list[dict[str, object]] = [
        {"id": "demo-a.1", "status": "open", "dependencies": []},
        {
            "id": "demo-a.2",
            "status": "open",
            "dependencies": [{"type": "blocks", "depends_on_id": "demo-a.1"}],
        },
    ]
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok(_bd_json(beads))):
        CliRunner().invoke(
            main, ["active-sync", "--project", str(tmp_path), "--no-export"]
        )
    text = active.read_text(encoding="utf-8")
    assert "| demo-a.2 | dev | blocked |" in text


def test_fix_bead_absent_from_bd_row_untouched(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    # bd knows only demo-a.1; demo-a.2 / demo-a.3 absent -> untouched.
    beads: list[dict[str, object]] = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok(_bd_json(beads))):
        CliRunner().invoke(
            main, ["active-sync", "--project", str(tmp_path), "--no-export"]
        )
    text = active.read_text(encoding="utf-8")
    assert "| demo-a.1 | dev | ✓ done |" in text
    assert "| demo-a.2 | dev | in progress |" in text
    assert "| demo-a.3 | review | ready |" in text


# ===========================================================================
# --check semantics: byte-unchanged on drift, accurate JSON
# ===========================================================================


def test_check_mode_drift_leaves_file_bytes_unchanged(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    before = active.read_text(encoding="utf-8")
    beads: list[dict[str, object]] = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok(_bd_json(beads))):
        result = CliRunner().invoke(
            main, ["active-sync", "--check", "--project", str(tmp_path)]
        )
    assert result.exit_code == 1
    assert active.read_text(encoding="utf-8") == before


def test_check_json_reports_drift_without_writing(tmp_path: Path) -> None:
    active = _write_active(tmp_path, "DEMO")
    before = active.read_text(encoding="utf-8")
    beads: list[dict[str, object]] = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok(_bd_json(beads))):
        result = CliRunner().invoke(
            main, ["active-sync", "--check", "--json", "--project", str(tmp_path)]
        )
    # Drift present -> exit 1; JSON still emitted; file untouched.
    assert result.exit_code == 1
    assert active.read_text(encoding="utf-8") == before


def test_json_drifted_row_fields_are_accurate(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    beads: list[dict[str, object]] = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok(_bd_json(beads))):
        result = CliRunner().invoke(
            main,
            ["active-sync", "--json", "--project", str(tmp_path), "--no-export"],
        )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    row = next(r for r in payload["drifted_rows"] if r["bead_id"] == "demo-a.1")
    assert row["old"] == "ready"
    assert row["new"] == "✓ done"
    assert any("DEMO" in cf for cf in payload["changed_files"])


def test_json_clean_has_empty_drift(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    beads: list[dict[str, object]] = [
        {"id": "demo-a.1", "status": "open", "dependencies": []},
        {"id": "demo-a.2", "status": "in_progress", "dependencies": []},
        {"id": "demo-a.3", "status": "open", "dependencies": []},
    ]
    with patch("beadloom.services.bd_seam.run_bd", return_value=_ok(_bd_json(beads))):
        result = CliRunner().invoke(
            main, ["active-sync", "--json", "--project", str(tmp_path), "--no-export"]
        )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["changed_files"] == []
    assert payload["drifted_rows"] == []


# ===========================================================================
# jsonl export argv (mock run_bd, assert exact args)
# ===========================================================================


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True)  # noqa: S603, S607


def _tracked_jsonl(tmp_path: Path) -> None:
    beads_dir = tmp_path / ".beads"
    beads_dir.mkdir()
    (beads_dir / "issues.jsonl").write_text("{}\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".beads/issues.jsonl")


def test_export_invoked_with_exact_argv_when_tracked(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    _tracked_jsonl(tmp_path)
    beads: list[dict[str, object]] = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]
    export_calls: list[list[str]] = []

    def fake(args: list[str], *, cwd: str | None = None) -> BdResult:
        if args[:1] == ["export"]:
            export_calls.append(args)
            return _ok("")
        return _ok(_bd_json(beads))

    with patch("beadloom.services.bd_seam.run_bd", side_effect=fake):
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert export_calls == [["export", "-o", ".beads/issues.jsonl"]]


def test_export_bd_unavailable_is_swallowed(tmp_path: Path) -> None:
    _write_active(tmp_path, "DEMO")
    _tracked_jsonl(tmp_path)
    beads: list[dict[str, object]] = [{"id": "demo-a.1", "status": "closed", "dependencies": []}]

    def fake(args: list[str], *, cwd: str | None = None) -> BdResult:
        if args[:1] == ["export"]:
            raise BdUnavailableError("bd vanished mid-run")
        return _ok(_bd_json(beads))

    with patch("beadloom.services.bd_seam.run_bd", side_effect=fake):
        result = CliRunner().invoke(main, ["active-sync", "--project", str(tmp_path)])
    # Export failure never bubbles up.
    assert result.exit_code == 0, result.output


# ===========================================================================
# hook templates — guarded coherence block in BOTH modes, after sync-check
# ===========================================================================


def _install_hook(tmp_path: Path, mode: str = "warn") -> str:
    project = tmp_path / "proj"
    (project / ".git" / "hooks").mkdir(parents=True)
    (project / ".beadloom").mkdir()
    CliRunner().invoke(
        main, ["install-hooks", "--mode", mode, "--project", str(project)]
    )
    return (project / ".git" / "hooks" / "pre-commit").read_text()


@pytest.mark.parametrize("mode", ["warn", "block"])
def test_coherence_block_guarded_and_runs_active_sync(tmp_path: Path, mode: str) -> None:
    content = _install_hook(tmp_path, mode)
    assert "ACTIVE / tracker coherence" in content
    assert "command -v bd >/dev/null 2>&1" in content
    assert "beadloom active-sync" in content
    # Restages both the ACTIVE docs and the tracked jsonl.
    assert "git add -u .claude/development/docs/features" in content
    assert ".beads/issues.jsonl" in content


@pytest.mark.parametrize("mode", ["warn", "block"])
def test_coherence_block_ordered_after_sync_check(tmp_path: Path, mode: str) -> None:
    content = _install_hook(tmp_path, mode)
    assert content.index("sync-check") < content.index("ACTIVE / tracker coherence")


def test_block_template_guards_active_sync_behind_bd_check(tmp_path: Path) -> None:
    # The active-sync call must be INSIDE the `command -v bd` guard, so a bd-less
    # adopter never runs it.
    content = _install_hook(tmp_path, "block")
    guard = "if command -v bd >/dev/null 2>&1 && command -v beadloom >/dev/null 2>&1; then"
    assert guard in content
    after_guard = content.split(guard, 1)[1]
    assert "beadloom active-sync" in after_guard


# ===========================================================================
# HOOK END-TO-END in a bd-less temp git repo — the adopter scenario
# ===========================================================================


def _make_path_without_bd(tmp_path: Path) -> str:
    """A PATH dir holding only git/sh (NOT bd / beadloom): `command -v bd` fails."""
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    for tool in ("git", "sh", "env", "cat", "rm", "dirname", "uname"):
        src = shutil.which(tool)
        if src:
            (fakebin / tool).symlink_to(src)
    return str(fakebin)


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
def test_hook_is_strict_noop_in_bdless_repo(tmp_path: Path) -> None:
    project = tmp_path / "adopter"
    (project / ".git" / "hooks").mkdir(parents=True)
    # Install the hook via the real command.
    res = CliRunner().invoke(main, ["install-hooks", "--project", str(project)])
    assert res.exit_code == 0, res.output

    # Make it a real repo with one tracked file + a (deliberately wrong) ACTIVE
    # table that the hook would 'fix' ONLY if bd were available.
    _git(project, "init", "-q")
    _git(project, "config", "user.email", "t@example.com")
    _git(project, "config", "user.name", "Tester")
    feat = project / ".claude" / "development" / "docs" / "features" / "X"
    feat.mkdir(parents=True)
    active = feat / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n|---|---|---|\n| x.1 | dev | ready |\n", "utf-8"
    )
    active_before = active.read_text(encoding="utf-8")
    (project / "file.txt").write_text("hello\n", encoding="utf-8")
    _git(project, "add", "-A")

    # Commit with a PATH that contains NO bd / beadloom -> the coherence block's
    # `command -v bd` guard fails, the whole block is a no-op.
    env = dict(os.environ)
    env["PATH"] = _make_path_without_bd(tmp_path)
    completed = subprocess.run(
        ["git", "commit", "-m", "initial"],  # noqa: S607
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    # The ACTIVE table was NOT touched by the hook (adopter has no bd).
    assert active.read_text(encoding="utf-8") == active_before
    # Working tree is clean: the hook staged/changed nothing of its own.
    status = subprocess.run(
        ["git", "status", "--porcelain"],  # noqa: S607
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
    )
    assert status.stdout.strip() == "", status.stdout


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
def test_hook_noop_when_beadloom_present_but_bd_absent(tmp_path: Path) -> None:
    # The true adopter: they installed `beadloom` but NOT `bd`. The bd guard
    # alone must stop the block. A tripwire `beadloom` is on PATH that corrupts
    # the table if ever invoked — proving the hook never calls it.
    project = tmp_path / "adopter2"
    (project / ".git" / "hooks").mkdir(parents=True)
    res = CliRunner().invoke(main, ["install-hooks", "--project", str(project)])
    assert res.exit_code == 0, res.output

    _git(project, "init", "-q")
    _git(project, "config", "user.email", "t@example.com")
    _git(project, "config", "user.name", "Tester")
    feat = project / ".claude" / "development" / "docs" / "features" / "X"
    feat.mkdir(parents=True)
    active = feat / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n|---|---|---|\n| x.1 | dev | ready |\n", "utf-8"
    )
    active_before = active.read_text(encoding="utf-8")
    (project / "file.txt").write_text("hello\n", encoding="utf-8")
    _git(project, "add", "-A")

    # PATH = git/sh + a tripwire `beadloom` (but NO `bd`).
    fakebin = tmp_path / "fakebin2"
    fakebin.mkdir()
    for tool in ("git", "sh", "env", "cat", "rm", "dirname", "uname"):
        src = shutil.which(tool)
        if src:
            (fakebin / tool).symlink_to(src)
    # Tripwire `beadloom`: harmless for every subcommand EXCEPT `active-sync`,
    # which corrupts the table. The hook calls `beadloom sync-check` before the
    # coherence block, so only an `active-sync` invocation must trip it.
    tripwire = fakebin / "beadloom"
    tripwire.write_text(
        '#!/bin/sh\nif [ "$1" = "active-sync" ]; then echo CORRUPTED > "'
        + str(active)
        + '"; fi\nexit 0\n',
        encoding="utf-8",
    )
    tripwire.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = str(fakebin)
    completed = subprocess.run(
        ["git", "commit", "-m", "initial"],  # noqa: S607
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    # The tripwire beadloom was NEVER invoked (bd guard short-circuited first).
    assert active.read_text(encoding="utf-8") == active_before
