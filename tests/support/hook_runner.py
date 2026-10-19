"""An installed git hook, run under a PATH that holds only the tools a test names.

BDL-083 S1a (``beadloom-7i09``). What the composed hooks print depends on which tools git's
PATH holds: ``beadloom``, ``uv``, ``ruff``, ``bd``. A test that inherits the machine's PATH
measures the machine, so every hook test here builds its own directory of tools: ``git``
always, the ``beadloom`` this suite runs under when asked for, and a shim for anything the
test wants to answer for itself.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from beadloom.services.cli import main

#: The interpreter's own scripts directory, where the ``beadloom`` under test is installed.
_SCRIPTS = Path(sys.executable).parent


def install_hooks(root: Path, *args: str) -> None:
    """Install the composed hooks into *root*'s repository; raise if the command fails."""
    result = CliRunner().invoke(main, ["install-hooks", "--project", str(root), *args])
    assert result.exit_code == 0, result.output


def tools(workdir: Path, *, beadloom: bool = False, shims: dict[str, str] | None = None) -> str:
    """A PATH value holding ``git``, optionally ``beadloom``, and the named shell shims.

    *shims* maps a tool name to the body of a POSIX ``sh`` script standing in for it.
    """
    bindir = workdir / "tools"
    bindir.mkdir(exist_ok=True)
    git = shutil.which("git")
    assert git is not None, "the hook tests need git"
    (bindir / "git").symlink_to(git)
    if beadloom:
        (bindir / "beadloom").symlink_to(_SCRIPTS / "beadloom")
    for name, body in (shims or {}).items():
        shim = bindir / name
        shim.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        shim.chmod(0o755)
    return f"{bindir}:/usr/bin:/bin"


def run_hook(
    root: Path, name: str, path: str, *, stdin: str = ""
) -> subprocess.CompletedProcess[str]:
    """Run *root*'s installed hook *name* as git would, from the root, under *path*.

    *stdin* is what git writes to the hook: for pre-push, one line per ref pushed
    (``<local ref> <local oid> <remote ref> <remote oid>``). It is always handed over,
    empty by default, so no hook reads the terminal the suite happens to run under.
    """
    return subprocess.run(  # noqa: S603 - the hook this test installed, run by sh
        ["/bin/sh", str(root / ".git" / "hooks" / name)],
        cwd=root,
        env={"PATH": path, "HOME": str(root)},
        input=stdin,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
