"""Step implementations for BDL-068 S4 — the typed surface the gate checks.

Thin by design. Every step drives the real ``beadloom typed-surface`` over a
real ``pyproject.toml``, and the last scenario drives the real emitted hook text
through a real ``/bin/sh`` with stub ``uv``/``mypy`` on ``PATH``. The defect
being pinned is which files a check is handed and what reaches the committer
when it fails, and a double would report whatever the double was told to.

The module is named ``test_*`` so default pytest collection picks the scenarios
up -- the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/typed_surface.feature")

#: The prefix the porcelain verdict line carries, shared with `scope-check` so a
#: hook splits verdict from payload on one shape. A payload line is a
#: project-relative path and no path begins with it.
_MARKER = "# "

_STAGED = (
    "src/beadloom/alpha.py",
    "src/beadloom/beta.py",
    "tests/test_alpha.py",
    "tests/conftest.py",
    "src/scripts/tool.py",
)

#: The same five files on the FLAT layout -- the package at the repository root,
#: which is where a Python project sits unless someone chose otherwise. The
#: counts below are identical by construction, so a scenario that reads "2 of 5"
#: is making the same claim about both layouts and not two claims that happen to
#: agree.
_STAGED_FLAT = (
    "beadloom/alpha.py",
    "beadloom/beta.py",
    "tests/test_alpha.py",
    "tests/conftest.py",
    "scripts/tool.py",
)

_DECLARED = """\
[project]
name = "demo"

[tool.mypy]
strict = true
packages = ["beadloom"]
mypy_path = "src"
"""

_UNDECLARED = """\
[project]
name = "demo"

[tool.ruff]
src = ["src", "tests"]
"""

#: The flat layout's declaration: the same package, and no `mypy_path`, because
#: there is no source directory to point at.
_DECLARED_FLAT = """\
[project]
name = "demo"

[tool.mypy]
strict = true
packages = ["beadloom"]
"""


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _project(tmp_path: Path, pyproject: str, staged: tuple[str, ...] = _STAGED) -> Path:
    """A project holding `staged`, with its directories taken from those paths.

    The directories are derived from the staged paths rather than named here,
    so a second layout is a second tuple and not a second set of `mkdir` calls
    that could disagree with it.
    """
    project = tmp_path / "proj"
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    for rel in staged:
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n", encoding="utf-8")
    return project


def _filter(project: Path, staged: tuple[str, ...]) -> dict[str, Any]:
    """Run the real command the hook runs, and split its two kinds of line."""
    result = CliRunner().invoke(
        main,
        ["typed-surface", "--filter", "--project", str(project)],
        input="\n".join(staged) + "\n",
    )
    lines = result.output.splitlines()
    return {
        "exit_code": result.exit_code,
        "verdict": next(
            (line[len(_MARKER) :] for line in lines if line.startswith(_MARKER)), ""
        ),
        "paths": [line for line in lines if not line.startswith(_MARKER)],
    }


@given("a project whose mypy configuration declares one package typed")
def _declared(state: dict[str, Any], tmp_path: Path) -> None:
    state["project"] = _project(tmp_path, _DECLARED)


@given("a project whose configuration declares no typed surface")
def _undeclared(state: dict[str, Any], tmp_path: Path) -> None:
    state["project"] = _project(tmp_path, _UNDECLARED)


@when("the staged paths are filtered against the declared typed surface")
def _run_filter(state: dict[str, Any]) -> None:
    state["run"] = _filter(state["project"], _STAGED)


@when("a commit staging only paths outside the declared surface is filtered")
def _run_filter_outside(state: dict[str, Any]) -> None:
    state["run"] = _filter(state["project"], ("tests/test_alpha.py", "tests/conftest.py"))


@then("only the paths inside the declared package are handed to the type checker")
def _only_inside(state: dict[str, Any]) -> None:
    assert state["run"]["paths"] == ["src/beadloom/alpha.py", "src/beadloom/beta.py"]


@then("the verdict states how many staged files were checked out of how many staged")
def _states_counts(state: dict[str, Any]) -> None:
    verdict = state["run"]["verdict"]
    assert "2 of 5" in verdict
    assert "src/beadloom" in verdict


@then("no path is handed to the type checker")
def _no_paths(state: dict[str, Any]) -> None:
    assert state["run"]["paths"] == []


@then("the verdict says none of the staged files is inside the declared surface")
def _says_nothing_to_check(state: dict[str, Any]) -> None:
    verdict = state["run"]["verdict"]
    assert "NOTHING TO CHECK" in verdict
    assert "0 of 2" in verdict


@then("the verdict says the surface could not be derived, with the reason")
def _says_not_checked(state: dict[str, Any]) -> None:
    verdict = state["run"]["verdict"]
    assert verdict.startswith("Typed surface: NOT CHECKED")
    assert "[tool.mypy]" in verdict


# --- the hook, run for real -------------------------------------------------


_STUB_UV = """\
#!/bin/sh
# `uv run mypy <paths...>` -- reject the one file the scenario says is rejected.
# The path is read from `$REJECT` rather than written here, because the file the
# scenario points at is where the layout puts it and the layout is an argument.
shift 2
for f in "$@"; do
  if [ "$f" = "$REJECT" ]; then
    echo "$f:1: error: Incompatible return value type  [return-value]"
    echo "Found 1 error in 1 file (checked $# source files)"
    exit 1
  fi
done
exit 0
"""


@given("a pre-commit hook installed over a project with a declared typed surface")
def _hook_installed(state: dict[str, Any], tmp_path: Path) -> None:
    _install_hook(state, tmp_path, _DECLARED, _STAGED, "src/beadloom/alpha.py")


@given("a pre-commit hook installed over a project whose package sits at the repository root")
def _hook_installed_flat(state: dict[str, Any], tmp_path: Path) -> None:
    """The flat layout, which no path in this repository has (BDL-UX #240)."""
    _install_hook(state, tmp_path, _DECLARED_FLAT, _STAGED_FLAT, "beadloom/alpha.py")


def _install_hook(
    state: dict[str, Any],
    tmp_path: Path,
    pyproject: str,
    staged: tuple[str, ...],
    rejected: str,
) -> None:
    from beadloom.services.commands.docsync import _HOOK_TEMPLATE_WARN

    project = _project(tmp_path, pyproject, staged)
    state["project"] = project
    state["rejected"] = rejected
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "uv").write_text(_STUB_UV, encoding="utf-8")
    (bindir / "uv").chmod(0o755)
    (bindir / "beadloom").write_text(
        "#!/bin/sh\nexec "
        + sys.executable
        + ' -c "from beadloom.services.cli import main; main()" "$@"\n',
        encoding="utf-8",
    )
    (bindir / "beadloom").chmod(0o755)
    hook = tmp_path / "pre-commit"
    hook.write_text(_HOOK_TEMPLATE_WARN, encoding="utf-8")
    hook.chmod(0o755)
    state["hook"] = hook
    state["bindir"] = bindir


@when("the hook runs on a commit whose typed file the checker rejects")
def _run_hook(state: dict[str, Any]) -> None:
    project: Path = state["project"]
    subprocess.run(
        ["git", "init", "-q"],  # noqa: S607
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "-A"],  # noqa: S607
        cwd=project,
        check=True,
        capture_output=True,
    )
    env = dict(os.environ)
    env["PATH"] = f"{state['bindir']}{os.pathsep}{env['PATH']}"
    env["REJECT"] = state["rejected"]
    # The hook is written as UTF-8 above and carries an em dash in its blocking
    # verdicts, so the codec is stated here rather than taken from the image:
    # under `LC_ALL=C` `text=True` raises before any step can assert anything
    # (BDL-068 `.49`; measured on PR #61's `tests-locale (C)` leg).
    state["hook_run"] = subprocess.run(  # noqa: S603
        ["/bin/sh", str(state["hook"])],
        cwd=project,
        capture_output=True,
        encoding="utf-8",
        errors="strict",
        env=env,
        check=False,
    )


@then("the checker's own diagnostic reaches the committer")
def _diagnostic_reaches(state: dict[str, Any]) -> None:
    out = state["hook_run"].stdout
    assert "Incompatible return value type" in out, out
    assert f"{state['rejected']}:1" in out, out


@then("the gate names how many files it type-checked")
def _names_count(state: dict[str, Any]) -> None:
    out = state["hook_run"].stdout
    assert "2 of 5" in out, out
