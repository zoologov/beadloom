"""Thin, patchable wrappers around ``beadloom`` / ``git`` subprocess calls.

These are the only place the harness shells out to external tools. They are
kept deliberately thin so tests can patch :func:`run_command` (or the helpers)
without monkeypatching ``subprocess`` directly. No business logic lives here.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommandResult:
    """Result of a subprocess invocation (exit code + captured streams)."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        """True when the command exited 0."""
        return self.returncode == 0


def run_command(args: list[str], *, cwd: Path) -> CommandResult:
    """Run *args* in *cwd*, capturing stdout/stderr (never raises on non-zero).

    The single subprocess seam: every external call funnels through here so
    tests patch exactly one function. ``check`` is intentionally False — the
    harness inspects exit codes itself (a failing gate is data, not an
    exception).
    """
    logger.debug("run: %s (cwd=%s)", " ".join(args), cwd)
    completed = subprocess.run(  # noqa: S603 - args are constructed internally, never shell
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def beadloom_sync_check_json(project_root: Path) -> dict[str, object]:
    """Run ``beadloom sync-check --json`` and parse the report.

    Exit code 2 means stale docs were found — that is expected data, not an
    error, so it is parsed normally.
    """
    result = run_command(["beadloom", "sync-check", "--json"], cwd=project_root)
    if not result.stdout.strip():
        raise RuntimeError(
            f"sync-check produced no JSON (rc={result.returncode}): {result.stderr}"
        )
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, dict):
        raise RuntimeError("sync-check JSON is not an object")
    return parsed


def beadloom_docs_polish_json(project_root: Path) -> dict[str, object]:
    """Run ``beadloom docs polish --format json`` and parse the enrichment data."""
    result = run_command(
        ["beadloom", "docs", "polish", "--format", "json"], cwd=project_root
    )
    if not result.stdout.strip():
        raise RuntimeError(f"docs polish produced no JSON (rc={result.returncode})")
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, dict):
        raise RuntimeError("docs polish JSON is not an object")
    return parsed


def beadloom_ctx_json(project_root: Path, ref_id: str) -> dict[str, object]:
    """Run ``beadloom ctx <ref> --json`` and parse the context bundle."""
    result = run_command(["beadloom", "ctx", ref_id, "--json"], cwd=project_root)
    if not result.stdout.strip():
        return {}
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def beadloom_why(project_root: Path, ref_id: str) -> str:
    """Run ``beadloom why <ref>`` and return its (text) impact analysis."""
    result = run_command(["beadloom", "why", ref_id], cwd=project_root)
    return result.stdout


def beadloom_sync_update(project_root: Path, ref_id: str) -> CommandResult:
    """Re-baseline one ref non-interactively (W1: ``sync-update <ref> --yes``)."""
    return run_command(
        ["beadloom", "sync-update", ref_id, "--yes"], cwd=project_root
    )


def beadloom_ci(project_root: Path) -> CommandResult:
    """Run the unified gate (``beadloom ci``). rc 0 = green, 1 = failure."""
    return run_command(["beadloom", "ci"], cwd=project_root)
