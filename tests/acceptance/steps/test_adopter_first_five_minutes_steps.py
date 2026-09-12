"""Step implementations for `features/adopter_first_five_minutes.feature`.

BDL-069 acceptance (`beadloom-956f`). Every other init scenario in this suite
invokes `beadloom.services.cli:main` in-process, which measures the WORKING TREE.
The two criteria here are stated about the artifact an adopter installs, so these
steps build a wheel from this tree, install it into an interpreter of its own and
run the console script as a subprocess. Nothing in this module imports
`beadloom`, deliberately: an import would put the tree's code in the same process
as the assertion and make "the wheel does this" unprovable from inside it.

**The build happens once per session.** Building and installing measured 11 s on
a warm `uv` cache (Darwin arm64, CPython 3.13.7); doing it per scenario would add
that to every run for no extra coverage, since both scenarios ask the same
artifact different questions.

**A build that cannot happen SKIPS with its reason.** No `uv`, no manifest — the
state the docstring of `test_bootstrap_self_consistency_steps` records, where the
acceptance suite is copied out and run standalone — or an index that cannot be
reached. A suite that could not reach the artifact has measured nothing about it,
and the one thing it must not do is read as having measured it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("../features/adopter_first_five_minutes.feature")

#: The two-package layout BDL-UX #282 was measured on. `ledger` carries a second
#: module so a skeleton naming only the first module it met would still leave one
#: out, and none of `core`, `journal`, `invoice` appears in a line the templates
#: write — a fixture holding `source.py` would be satisfied by the skeleton's own
#: `## Source` heading and pass without the skeleton naming anything.
TWO_PACKAGES: dict[str, dict[str, str]] = {
    "ledger": {
        "__init__.py": '"""The ledger."""\n',
        "core.py": (
            "class Ledger:\n    def post(self, amount: int) -> int:\n        return amount\n"
        ),
        "journal.py": "def record(entry: str) -> str:\n    return entry\n",
    },
    "billing": {
        "__init__.py": '"""Billing."""\n',
        "core.py": (
            "from ledger.core import Ledger\n\n\n"
            "def charge(amount: int) -> int:\n    return Ledger().post(amount)\n"
        ),
        "invoice.py": "def issue(number: int) -> int:\n    return number\n",
    },
}

#: The project name for the multi-package layout: something none of its packages
#: is called, which is what makes the root node's ref_id unambiguous there.
TWO_PACKAGE_PROJECT = "myapp"

#: The single-package layout of BDL-UX #214, spelled as that report spells it:
#: `myapp` whose only package is `src/myapp/`. The collision is between the
#: service root and the package domain, and it needs the two names to be equal.
SINGLE_PACKAGE_PROJECT = "myapp"
SINGLE_PACKAGE: dict[str, dict[str, str]] = {
    SINGLE_PACKAGE_PROJECT: {
        "__init__.py": '"""My app."""\n',
        "core.py": "def count(items: list[str]) -> int:\n    return len(items)\n",
        "journal.py": "def record(entry: str) -> str:\n    return entry\n",
    },
}

#: What `init` prints about the graph it wrote, e.g. `Graph: 2 nodes, 1 edges`.
_INIT_NODES = re.compile(r"Graph:\s*(\d+)\s+nodes?")

#: What the freshness leg's summary says when every pair is fresh. A pair is a
#: document AND a code file, so the noun is what distinguishes the population
#: from the number of documents (CONTEXT, "A pair is a document AND a code file").
_FRESH_PAIRS = re.compile(r"(\d+)\s+pair\(s\)\s+fresh")


def _clean_env(*, venv: Path | None = None, first_on_path: Path | None = None) -> dict[str, str]:
    """The environment a subprocess about the WHEEL may see.

    ``PYTHONPATH`` is removed, and that removal is the whole point rather than
    hygiene: `beadloom clean-room` runs the suite with ``PYTHONPATH=<room>/src``,
    so a child that inherits it imports the room's source in preference to
    whatever is installed in its own interpreter. Measured — the first run of
    this file in a clean room reported the wheel's `beadloom.__file__` under
    `<room>/src`, and the scenario caught it because that is what it asserts.
    """
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("VIRTUAL_ENV", None)
    if venv is not None:
        env["VIRTUAL_ENV"] = str(venv)
    if first_on_path is not None:
        env["PATH"] = f"{first_on_path}{os.pathsep}{env.get('PATH', '')}"
    return env


def _ran(
    *args: str, cwd: Path | None = None, venv: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run *args* with a clean environment and hand back the whole result."""
    return subprocess.run(  # noqa: S603
        list(args),
        cwd=cwd,
        env=_clean_env(venv=venv),
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


class _Wheel:
    """A wheel built from this tree, installed into an interpreter of its own."""

    def __init__(self, console_script: Path, python: Path, site_packages_root: Path) -> None:
        self.console_script = console_script
        self.python = python
        self.site_packages_root = site_packages_root

    def run(self, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        """Run the installed console script in *project*, with a clean environment."""
        return subprocess.run(  # noqa: S603
            [str(self.console_script), *args],
            cwd=project,
            env=_clean_env(first_on_path=self.console_script.parent),
            capture_output=True,
            encoding="utf-8",
            check=False,
        )

    def imports_beadloom_from(self) -> Path:
        """Where the installed interpreter's own `beadloom` is read from."""
        where = _ran(str(self.python), "-c", "import beadloom; print(beadloom.__file__)")
        assert where.returncode == 0, f"{where.stdout}\n{where.stderr}"
        return Path(where.stdout.strip())


def _tree_above(start: Path) -> Path | None:
    """The first directory at or above *start* whose manifest names this project."""
    for candidate in start.resolve().parents:
        manifest = candidate / "pyproject.toml"
        if manifest.is_file() and 'name = "beadloom"' in manifest.read_text(encoding="utf-8"):
            return candidate
    return None


def _repository_root() -> Path:
    """The tree to build the wheel from.

    Asked of the INSTALLED package first and of this file second, because the
    acceptance suite is copied out of the repository and run standalone
    (`tests/test_bead14_s4_binding.py` does exactly that to sabotage a step
    binding), and in that copy there is nothing above this file but a temporary
    directory. The installed `beadloom` is an editable install of the tree under
    every arrangement this project runs, so it still points at one.

    The import is for a PATH and never for an answer: every assertion in this
    module is made against the wheel's own output, and none of them reads
    anything this import brings into the process.
    """
    import beadloom

    for start in (Path(beadloom.__file__), Path(__file__)):
        found = _tree_above(start)
        if found is not None:
            return found
    raise AssertionError(
        "no beadloom manifest above the installed package or above this file, so the "
        "artifact an adopter installs cannot be built and this criterion is unmeasurable"
    )


@pytest.fixture(scope="session")
def installed_wheel(tmp_path_factory: pytest.TempPathFactory) -> _Wheel:
    """Build this tree into a wheel and install it into a fresh interpreter.

    Every failure here is RED and never a skip. A step that steps aside is a
    scenario that stops running in the room where the guard fires, and
    `tests/test_bead14_s4_binding.py` fails on the presence of one anywhere in
    this directory. `uv` is this project's declared environment tool — every
    installing leg of `ci.yml` sets it up before it runs anything — so a run
    without it is a broken room and not a room this criterion is silent about.
    """
    uv = shutil.which("uv")
    assert uv is not None, "no `uv` on PATH, and `uv` is how this project builds its artifact"
    root = _repository_root()

    area = tmp_path_factory.mktemp("installed-wheel")
    dist, venv = area / "dist", area / "venv"
    build = _ran(uv, "build", "--wheel", "--out-dir", str(dist), cwd=root)
    assert build.returncode == 0, f"`uv build` failed:\n{build.stdout}\n{build.stderr}"
    wheels = sorted(dist.glob("beadloom-*.whl"))
    assert wheels, f"`uv build` exited 0 and produced no wheel: {build.stdout}"

    made = _ran(uv, "venv", str(venv))
    assert made.returncode == 0, f"`uv venv` failed:\n{made.stdout}\n{made.stderr}"
    installed = _ran(uv, "pip", "install", str(wheels[-1]), venv=venv)
    assert installed.returncode == 0, (
        f"installing the wheel failed:\n{installed.stdout}\n{installed.stderr}"
    )

    bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
    script = bin_dir / ("beadloom.exe" if os.name == "nt" else "beadloom")
    python = bin_dir / ("python.exe" if os.name == "nt" else "python")
    assert script.is_file(), f"the wheel installed without its console script: {sorted(bin_dir)}"
    return _Wheel(script, python, venv)


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _repository(root: Path, name: str, packages: dict[str, dict[str, str]]) -> Path:
    """A committed repository holding *packages* under `src/`, and nothing else."""
    project = root / f"{name}-project"
    for package, modules in packages.items():
        (project / "src" / package).mkdir(parents=True)
        for module, text in modules.items():
            (project / "src" / package / module).write_text(text, encoding="utf-8")
    (project / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "0.1.0"\nrequires-python = ">=3.10"\n',
        encoding="utf-8",
    )
    (project / "README.md").write_text(f"# {name}\n\nA project.\n", encoding="utf-8")
    _git(project, "init", "-q", "-b", "main")
    _git(project, "config", "user.email", "test@example.invalid")
    _git(project, "config", "user.name", "Test")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "the code before beadloom")
    return project


def _digest(project: Path) -> dict[str, str]:
    """Every file in *project* outside `.git`, by content. The no-hand-editing check."""
    return {
        str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(project.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(project).parts
    }


def _nodes_in_index(project: Path) -> dict[str, str]:
    """``ref_id -> source`` as the index holds it, read without importing beadloom.

    Read through stdlib ``sqlite3`` rather than through this tree's own database
    helper, because the subject is what the INSTALLED wheel wrote: a reader
    imported from the tree would make the assertion depend on the code under test
    being the code that is not under test.
    """
    db = project / ".beadloom" / "beadloom.db"
    assert db.is_file(), f"the wheel's init wrote no index at {db}"
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT ref_id, source FROM nodes").fetchall()
        return {str(ref): str(source) for ref, source in rows}
    finally:
        conn.close()


@given("a wheel built from this tree, installed into an interpreter of its own")
def _given_the_wheel(world: dict[str, Any], installed_wheel: _Wheel) -> None:
    world["wheel"] = installed_wheel


@given("a git repository holding two Python packages under src, which is not this repository")
def _given_two_packages(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _repository(tmp_path, TWO_PACKAGE_PROJECT, TWO_PACKAGES)


@given(
    "a git repository whose only Python package is named after it, "
    "which is not this repository"
)
def _given_one_package(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _repository(tmp_path, SINGLE_PACKAGE_PROJECT, SINGLE_PACKAGE)


@when("the installed beadloom initialises it in bootstrap mode without prompts")
def _when_init(world: dict[str, Any]) -> None:
    wheel, project = world["wheel"], world["project"]
    result = wheel.run(project, "init", "--yes", "--mode", "bootstrap")
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    world["init"] = result
    world["after_init"] = _digest(project)


@when("the installed beadloom runs its gate on the repository")
def _when_gate(world: dict[str, Any]) -> None:
    wheel, project = world["wheel"], world["project"]
    world["before_gate"] = _digest(project)
    world["gate"] = wheel.run(project, "ci", "--format", "json")


@when("the installed beadloom reports the project's status")
def _when_status(world: dict[str, Any]) -> None:
    wheel, project = world["wheel"], world["project"]
    result = wheel.run(project, "status", "--json")
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    world["status"] = json.loads(result.stdout)


@then("the gate exits 0")
def _then_green(world: dict[str, Any]) -> None:
    gate = world["gate"]
    assert gate.returncode == 0, f"{gate.stdout}\n{gate.stderr}"


@then("nothing in the repository was edited between the two commands")
def _then_untouched(world: dict[str, Any]) -> None:
    """The PRD's condition is `with no hand editing`, so it is checked, not promised.

    A green produced by a step quietly naming a module in a document would be a
    green about that step. Comparing the tree as `init` left it against the tree
    the gate was handed is what makes the two commands adjacent in fact.
    """
    after_init, before_gate = world["after_init"], world["before_gate"]
    assert after_init, "the initialisation wrote no file, so this comparison is vacuous"
    changed = sorted(
        name
        for name in set(after_init) | set(before_gate)
        if after_init.get(name) != before_gate.get(name)
    )
    assert not changed, f"edited between init and the gate: {changed}"


@then("the gate's freshness leg names the pairs it found fresh")
def _then_pairs_named(world: dict[str, Any]) -> None:
    """Anti-vacuity: a gate green over ZERO pairs is green about nothing.

    The count is compared against the code files the packages hold, because a
    pair is a document AND a code file — six files under two packages are six
    pairs over two documents, and `6 doc(s)` would be a different claim.
    """
    verdict = json.loads(world["gate"].stdout)
    leg = next(step for step in verdict["steps"] if step["name"] == "sync-check")
    assert leg["status"] == "PASS", leg
    match = _FRESH_PAIRS.search(leg["summary"])
    assert match is not None, f"the freshness leg does not name its population: {leg['summary']}"
    project = world["project"]
    code_files = sorted((project / "src").rglob("*.py"))
    assert int(match.group(1)) == len(code_files), (leg["summary"], code_files)


@then("the beadloom that ran is the installed wheel and not this working tree")
def _then_the_artifact_ran(world: dict[str, Any]) -> None:
    """Anti-vacuity for the whole file: a green taken against the tree proves nothing here."""
    wheel: _Wheel = world["wheel"]
    where = wheel.imports_beadloom_from()
    assert where.is_relative_to(wheel.site_packages_root), where
    assert not where.is_relative_to(_repository_root()), where


@then("the status counts every node the initialisation reported writing")
def _then_status_counts_them_all(world: dict[str, Any]) -> None:
    """BDL-UX #214: `init` reported 2 and `status` reported 1, and nothing said so."""
    reported = _INIT_NODES.search(world["init"].stdout)
    assert reported is not None, world["init"].stdout
    written = int(reported.group(1))
    assert written > 1, f"a project with one node cannot lose one: {world['init'].stdout}"
    assert world["status"]["nodes_count"] == written, (world["init"].stdout, world["status"])
    assert len(_nodes_in_index(world["project"])) == written, _nodes_in_index(world["project"])


@then("the node carrying the package's source is one of them")
def _then_the_source_node_survived(world: dict[str, Any]) -> None:
    """The node #214 dropped was the one holding the adopter's code, not the root."""
    sources = set(_nodes_in_index(world["project"]).values())
    assert f"src/{SINGLE_PACKAGE_PROJECT}/" in sources, sources


@then("the gate over that project exits 0")
def _then_that_gate_is_green(world: dict[str, Any]) -> None:
    wheel, project = world["wheel"], world["project"]
    result = wheel.run(project, "ci", "--format", "json")
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
