"""Mockable seam over the ``bd`` (beads) CLI.

# beadloom:service=mcp-server

The MCP process-tools (``task_init`` / ``complete_bead`` / ``checkpoint``)
drive the beads issue tracker. Rather than scatter ``subprocess`` calls across
the handlers, every ``bd`` invocation funnels through :func:`run_bd` — a single,
thin, **mockable** seam (mirrors the F4.1 harness's ``run_command``). Tests patch
:func:`run_bd` (or the module-level ``subprocess.run``) so the tools run WITHOUT
a real ``bd`` binary and without network.

If ``bd`` is not installed, :func:`run_bd` raises :class:`BdUnavailableError`
with a clear message; the calling tool converts that into a structured error
payload (the agentic flow already requires ``bd``).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

# Default per-call timeout (seconds) so a wedged `bd` never hangs a tool call.
_BD_TIMEOUT_S = 60


class BdUnavailableError(RuntimeError):
    """Raised when the ``bd`` binary is not installed / not on PATH."""


@dataclass(frozen=True)
class BdResult:
    """Outcome of a single ``bd`` invocation."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        """True when ``bd`` exited 0."""
        return self.returncode == 0


def run_bd(args: list[str], *, cwd: str | None = None) -> BdResult:
    """Invoke ``bd`` with *args* and capture its output.

    Parameters
    ----------
    args:
        Arguments passed to ``bd`` (without the leading ``bd``), e.g.
        ``["show", "bd-1", "--json"]``.
    cwd:
        Optional working directory for the invocation.

    Returns
    -------
    BdResult
        Captured ``returncode`` / ``stdout`` / ``stderr``.

    Raises
    ------
    BdUnavailableError
        If the ``bd`` binary cannot be found / executed.
    """
    try:
        # `bd` is resolved from PATH by design; argv is fixed (no shell, no user-built path).
        completed = subprocess.run(  # noqa: S603
            ["bd", *args],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=_BD_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError as exc:
        msg = "`bd` CLI not found on PATH — the agentic flow requires beads (bd) to be installed"
        raise BdUnavailableError(msg) from exc
    return BdResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
