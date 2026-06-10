"""Tests for the mockable `bd` CLI seam (BDL-048 BEAD-03).

The seam wraps every `bd` invocation behind a single subprocess call so the
MCP process-tools can be unit-tested WITHOUT a real `bd` binary and without
network. These tests assert:

- a successful invocation returns the captured stdout/stderr/returncode;
- a missing `bd` binary surfaces a clear structured error (not a crash);
- a non-zero exit is reported faithfully (returncode + stderr).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from beadloom.services.bd_seam import BdResult, BdUnavailableError, run_bd


def test_run_bd_success() -> None:
    completed = MagicMock(returncode=0, stdout="ok\n", stderr="")
    with patch("beadloom.services.bd_seam.subprocess.run", return_value=completed) as run:
        result = run_bd(["show", "bd-1"])
    assert isinstance(result, BdResult)
    assert result.ok is True
    assert result.returncode == 0
    assert result.stdout == "ok\n"
    # The seam always invokes the `bd` binary with the supplied args.
    call_args = run.call_args.args[0]
    assert call_args[0] == "bd"
    assert call_args[1:] == ["show", "bd-1"]


def test_run_bd_nonzero_exit() -> None:
    completed = MagicMock(returncode=1, stdout="", stderr="boom\n")
    with patch("beadloom.services.bd_seam.subprocess.run", return_value=completed):
        result = run_bd(["close", "bd-1"])
    assert result.ok is False
    assert result.returncode == 1
    assert result.stderr == "boom\n"


def test_run_bd_missing_binary_raises_clear_error() -> None:
    with patch(
        "beadloom.services.bd_seam.subprocess.run",
        side_effect=FileNotFoundError("bd"),
    ), pytest.raises(BdUnavailableError) as exc:
        run_bd(["ready"])
    assert "bd" in str(exc.value)


def test_run_bd_passes_cwd() -> None:
    completed = MagicMock(returncode=0, stdout="", stderr="")
    with patch("beadloom.services.bd_seam.subprocess.run", return_value=completed) as run:
        run_bd(["ready"], cwd="/work/x")
    assert run.call_args.kwargs["cwd"] == "/work/x"
