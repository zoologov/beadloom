"""Verify one Beadloom artifact on a project that is not this repository.

Usage::

    python3 tests/release/verify_the_release.py <wheel path | beadloom==X.Y.Z>
        [--release 8.0.0] [--node-bin DIR] [--python 3.12] [--keep] [--record-json PATH]

The artifact is either a built wheel or an exact PyPI pin. It is installed into a FRESH
virtual environment made by ``uv`` in a new temporary directory, with ``UV_NO_CACHE=1``
and ``--refresh``, so the verdict is about that artifact and not about whatever the machine
already held. The checks then run that environment's ``beadloom`` on a throwaway adopter
project the script writes itself: three modules with imports between them, a README, a
``docs/`` folder, a test, and a git history dated so that the three modules fall into three
different activity levels.

The checks, in the order they run and are reported:

* **version** -- ``beadloom --version``, ``beadloom.__version__`` and the installed
  distribution's metadata read ``--release``; the imported module is the one inside the
  fresh environment; a wheel's file name states the same version as its metadata.
* **init** and **reindex** exit 0; on a full history the reindex prints no shallow-history
  line.
* **activity** -- ``ctx --json`` carries ``activity.level`` from the five levels (hot, warm,
  cool, quiet, dormant) and an integer ``lines_30d`` for every node that owns a source
  directory (the root, whose source is the whole project, carries none), and the dated history
  lands where it was written to land: the module changed five days ago is hot, warm or
  cool, the one changed 45 days ago is quiet, the one untouched for 300 days is dormant.
* **shallow history** -- on a ``--depth 1`` clone the reindex prints the ``Activity:`` line
  naming the shallow history.
* **portal scaffold** -- ``docs site --out`` writes ``package.json``, ``.vitepress/`` and
  ``e2e/``.
* **portal build** -- ``npm ci`` and ``npm run docs:build`` succeed under Node 22 or later.
* **pages workflow** -- ``docs site --pages-workflow`` writes
  ``.github/workflows/beadloom-portal.yml`` with ``fetch-depth: 0``.

Every check runs, and the report names the FIRST that failed. A step that cannot run once
the checks have started -- a ``git`` command that fails while the project is written, or the
shallow clone -- is recorded as ``CANNOT RUN`` beside the checks that ran, and the report is
printed and recorded all the same; the checks that do not depend on that step still run.

Exit codes: 0 every check holds; 2 the run could not start (an unpinned or unknown artifact,
no ``uv``/``git``, a Node older than 22, an install that failed) or a step could not run, so
the verdict is incomplete; 3 a version check failed, or the index serves no such pin; 4 a
behaviour check failed and every version check held. A failed version check outranks an
incomplete run, because it already settles that the artifact is not the release.

It uses the standard library only, so any Python 3.10+ can run it, and it needs ``uv``,
``git`` and ``node``/``npm`` on ``PATH`` (``--node-bin`` puts a Node directory first).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

#: The release this script verifies when ``--release`` is not given.
DEFAULT_RELEASE = "8.0.0"

#: The five activity levels a node can carry.
ACTIVITY_LEVELS = frozenset({"hot", "warm", "cool", "quiet", "dormant"})

#: The oldest Node major the portal scaffold's ``engines.node`` accepts.
NODE_MAJOR = 22

#: What a pages workflow must check out for activity to be measured on the full history.
FULL_FETCH = "fetch-depth: 0"

#: Where ``docs site --pages-workflow`` writes the workflow, relative to the project.
PAGES_WORKFLOW = Path(".github") / "workflows" / "beadloom-portal.yml"

#: What the portal scaffold holds at the top of the output directory.
SCAFFOLD_ENTRIES = (("package.json", "file"), (".vitepress", "dir"), ("e2e", "dir"))

#: An exact pin of the one distribution this script verifies.
_PIN = re.compile(r"^beadloom==(\d+\.\d+\.\d+(?:[a-z]+\d+)?)$")

#: A wheel's file name, whose second field is the version.
_WHEEL = re.compile(r"^beadloom-([^-]+)-.+\.whl$")

#: The committer of every commit of the throwaway project.
_IDENTITY = (
    "-c",
    "user.name=Release Check",
    "-c",
    "user.email=release-check@example.invalid",
    "-c",
    "init.defaultBranch=main",
)

#: Environment variables that would point the child processes at another environment.
_FOREIGN_ENVIRONMENT = ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "CONDA_PREFIX", "PYTHONSTARTUP")

_EXIT_OK = 0
_EXIT_CANNOT_RUN = 2
_EXIT_VERSION = 3
_EXIT_BEHAVIOUR = 4

#: The status of a check whose own step failed for a reason outside the artifact.
_CANNOT_RUN = "CANNOT RUN"


class CannotRunError(Exception):
    """The run could not start, so there is no verdict about the artifact."""

    def __init__(self, message: str, *, exit_code: int = _EXIT_CANNOT_RUN) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class Artifact:
    """What is installed: the argument to ``uv pip install`` and the version it claims."""

    install: str
    claimed_version: str
    is_wheel: bool


@dataclass
class Check:
    """One assertion and its outcome: ``PASS``, ``FAIL``, ``NOT RUN`` or ``CANNOT RUN``.

    ``NOT RUN`` is a check skipped because an earlier check of the artifact failed;
    ``CANNOT RUN`` is a check whose own step failed for a reason outside the artifact.
    """

    name: str
    kind: str
    status: str
    detail: str


@dataclass
class Report:
    """Everything a run found, in the order it was found."""

    artifact: str
    release: str
    room: dict[str, str] = field(default_factory=dict)
    checks: list[Check] = field(default_factory=list)

    def record(self, name: str, kind: str, *, passed: bool, detail: str) -> bool:
        self.checks.append(Check(name, kind, "PASS" if passed else "FAIL", detail))
        return passed

    def not_run(self, name: str, kind: str, why: str) -> None:
        self.checks.append(Check(name, kind, "NOT RUN", why))

    def cannot_run(self, name: str, kind: str, why: str) -> None:
        self.checks.append(Check(name, kind, _CANNOT_RUN, why))

    def first_failure(self) -> Check | None:
        return next((check for check in self.checks if check.status != "PASS"), None)

    def exit_code(self) -> int:
        failed = [check for check in self.checks if check.status != "PASS"]
        if any(check.kind == "version" for check in failed):
            return _EXIT_VERSION
        if any(check.status == _CANNOT_RUN for check in failed):
            return _EXIT_CANNOT_RUN
        return _EXIT_BEHAVIOUR if failed else _EXIT_OK


@dataclass(frozen=True)
class Done:
    """A finished child process."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


def parse_artifact(argument: str) -> Artifact:
    """The artifact *argument* names: an existing wheel file, or an exact ``beadloom`` pin."""
    pinned = _PIN.match(argument.strip())
    if pinned:
        return Artifact(argument.strip(), pinned.group(1), is_wheel=False)
    path = Path(argument).expanduser()
    if path.suffix == ".whl":
        if not path.is_file():
            raise CannotRunError(f"no wheel at {path}")
        named = _WHEEL.match(path.name)
        if not named:
            raise CannotRunError(f"{path.name} is not named like a beadloom wheel")
        return Artifact(str(path.resolve()), named.group(1), is_wheel=True)
    raise CannotRunError(
        f"{argument!r} is neither a wheel path nor an exact pin "
        f"such as beadloom=={DEFAULT_RELEASE}"
    )


class Room:
    """The fresh environment and the scratch directory every command of a run works in."""

    def __init__(self, workdir: Path, node_bin: Path | None) -> None:
        self.workdir = workdir
        self.venv = workdir / "venv"
        self.bin = self.venv / "bin"
        path = [str(self.bin)]
        if node_bin is not None:
            path.append(str(node_bin))
        path.append(os.environ.get("PATH", ""))
        self.env = {
            key: value for key, value in os.environ.items() if key not in _FOREIGN_ENVIRONMENT
        }
        self.env.update(
            PATH=os.pathsep.join(path),
            UV_NO_CACHE="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            NO_COLOR="1",
        )

    def run(self, command: list[str], cwd: Path, env: dict[str, str] | None = None) -> Done:
        done = subprocess.run(  # noqa: S603 - fixed commands assembled by this script
            command,
            cwd=cwd,
            env=env if env is not None else self.env,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return Done(done.returncode, done.stdout, done.stderr)

    def beadloom(self, project: Path, *args: str) -> Done:
        """The fresh environment's ``beadloom``, run in and on *project*."""
        return self.run([str(self.bin / "beadloom"), *args], project)

    def git(self, project: Path, *args: str, when: int | None = None) -> Done:
        env = dict(self.env)
        if when is not None:
            stamp = f"@{when} +0000"
            env.update(GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
        done = self.run(["git", *_IDENTITY, *args], project, env)
        if done.returncode != 0:
            raise CannotRunError(f"git {' '.join(args)} exited {done.returncode}: {done.output}")
        return done


# ---------------------------------------------------------------------------
# The throwaway adopter project
# ---------------------------------------------------------------------------

_PROJECT_FILES = {
    "pyproject.toml": (
        '[project]\nname = "quayside"\nversion = "0.4.0"\n'
        'description = "Books berths for barges and bills the owners."\n'
        'requires-python = ">=3.10"\n'
    ),
    "README.md": (
        "# Quayside\n\nBooks berths for barges and bills the owners. See the "
        "[berthing guide](docs/berthing.md).\n\n## Layout\n\n"
        "- `dock` takes a berth request.\n- `ledger` prices it.\n"
        "- `manifest` keeps the cargo list.\n"
    ),
    "docs/berthing.md": (
        "# Berthing\n\nA barge asks the dock for a berth; the ledger prices the stay and "
        "the manifest records what the barge carries.\n"
    ),
    "src/quayside/__init__.py": '"""Quayside: berths for barges."""\n',
    "src/quayside/dock/__init__.py": '"""Takes a berth request."""\n',
    "src/quayside/dock/berths.py": (
        '"""Takes a berth request and answers with its booking."""\n\n'
        "from __future__ import annotations\n\n"
        "from quayside.ledger.tariff import price_stay\n"
        "from quayside.manifest.cargo import CargoList\n\n\n"
        "def book_berth(barge: str, hours: int, cargo: CargoList) -> dict[str, object]:\n"
        '    """Price a stay, record the cargo, and return what the caller sees."""\n'
        '    return {"barge": barge, "amount": price_stay(hours), "cargo": cargo.count()}\n'
    ),
    "src/quayside/ledger/__init__.py": '"""Prices a stay."""\n',
    "src/quayside/ledger/tariff.py": (
        '"""Prices a stay at the quay."""\n\n'
        "from __future__ import annotations\n\n"
        "HOURLY_RATE = 12\n\n\n"
        "def price_stay(hours: int) -> int:\n"
        '    """The price of *hours* at the quay."""\n'
        "    return hours * HOURLY_RATE\n"
    ),
    "src/quayside/manifest/__init__.py": '"""Keeps the cargo list."""\n',
    "src/quayside/manifest/cargo.py": (
        '"""The cargo a barge declares."""\n\n'
        "from __future__ import annotations\n\n\n"
        "class CargoList:\n"
        '    """The items a barge carries."""\n\n'
        "    def __init__(self) -> None:\n"
        "        self.items: list[str] = []\n\n"
        "    def count(self) -> int:\n"
        '        """How many items are declared."""\n'
        "        return len(self.items)\n"
    ),
    "tests/test_tariff.py": (
        "from quayside.ledger.tariff import price_stay\n\n\n"
        "def test_a_stay_is_priced_by_the_hour() -> None:\n"
        "    assert price_stay(2) == 24\n"
    ),
}

#: The source directory of each module, and the activity the dated history gives it.
_CHANGED_RECENTLY = "src/quayside/dock"
_CHANGED_IN_90_DAYS = "src/quayside/ledger"
_UNTOUCHED = "src/quayside/manifest"

_DAY = 86_400


def _append(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def write_project(room: Room, root: Path, now: int) -> None:
    """The adopter's project, committed in three dated commits on a full history.

    300 days ago everything is written; 45 days ago only the ledger changes; five days
    ago only the dock changes, by about forty lines. The manifest is never touched again.
    """
    for relative, text in _PROJECT_FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    room.git(root, "init", "-q")
    room.git(root, "remote", "add", "origin", "git@github.com:harbour-works/quayside.git")
    room.git(root, "add", "-A")
    room.git(root, "commit", "-q", "-m", "the project", when=now - 300 * _DAY)
    _append(
        root,
        f"{_CHANGED_IN_90_DAYS}/tariff.py",
        "\n\ndef price_night(nights: int) -> int:\n"
        '    """A night costs twelve hours."""\n'
        "    return price_stay(12 * nights)\n",
    )
    room.git(root, "add", "-A")
    room.git(root, "commit", "-q", "-m", "ledger: nights", when=now - 45 * _DAY)
    for number in range(1, 11):
        _append(
            root,
            f"{_CHANGED_RECENTLY}/berths.py",
            f"\n\ndef gate_{number}() -> str:\n"
            f'    """The quay gate {number}."""\n'
            f'    return "gate-{number}"\n',
        )
    room.git(root, "add", "-A")
    room.git(root, "commit", "-q", "-m", "dock: gates", when=now - 5 * _DAY)


def declare_portal(root: Path) -> None:
    """What the adopter writes after ``init``: the portal's identity under ``site:``."""
    _append(
        root,
        ".beadloom/config.yml",
        "site:\n  title: Quayside\n  base: /quayside/\n"
        "  repo_url: https://github.com/harbour-works/quayside\n",
    )


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------


def check_versions(room: Room, artifact: Artifact, report: Report) -> None:
    release = report.release
    done = room.run([str(room.bin / "beadloom"), "--version"], room.workdir)
    reported = done.stdout.strip().rsplit(" ", 1)[-1] if done.returncode == 0 else ""
    report.record(
        "version: beadloom --version",
        "version",
        passed=reported == release,
        detail=f"printed {done.output.strip()!r} (rc {done.returncode}), expected {release}",
    )
    probe = (
        "import importlib.metadata, json, beadloom; print(json.dumps({"
        "'version': beadloom.__version__, "
        "'metadata': importlib.metadata.version('beadloom'), "
        "'file': beadloom.__file__}))"
    )
    done = room.run([str(room.bin / "python"), "-I", "-c", probe], room.workdir)
    found: dict[str, str] = json.loads(done.stdout) if done.returncode == 0 else {}
    report.record(
        "version: beadloom.__version__",
        "version",
        passed=found.get("version") == release,
        detail=f"reads {found.get('version')!r}, expected {release}",
    )
    report.record(
        "version: importlib.metadata.version('beadloom')",
        "version",
        passed=found.get("metadata") == release,
        detail=f"reads {found.get('metadata')!r}, expected {release}",
    )
    module = Path(found.get("file", ""))
    report.record(
        "version: the imported module is the one in the fresh environment",
        "version",
        passed=bool(found) and room.venv.resolve() in module.resolve().parents,
        detail=f"beadloom imported from {module}",
    )
    if artifact.is_wheel:
        report.record(
            "version: the wheel's file name states its metadata's version",
            "version",
            passed=artifact.claimed_version == found.get("metadata"),
            detail=(
                f"file name says {artifact.claimed_version}, metadata says "
                f"{found.get('metadata')!r}"
            ),
        )


def _graph_sources(room: Room, project: Path) -> dict[str, str]:
    """Each node's source directory mapped to its ref_id, read from the graph files."""
    probe = (
        "import json, pathlib, sys, yaml\n"
        "found = {}\n"
        "for path in sorted(pathlib.Path(sys.argv[1]).glob('*.yml')):\n"
        "    for node in (yaml.safe_load(path.read_text(encoding='utf-8')) or {})"
        ".get('nodes') or []:\n"
        "        found[str(node.get('source') or '').rstrip('/')] = node['ref_id']\n"
        "print(json.dumps(found))\n"
    )
    graph = project / ".beadloom" / "_graph"
    done = room.run([str(room.bin / "python"), "-I", "-c", probe, str(graph)], project)
    if done.returncode != 0:
        return {}
    loaded: dict[str, str] = json.loads(done.stdout)
    return loaded


def _activity(room: Room, project: Path, ref_id: str) -> tuple[dict[str, object] | None, str]:
    done = room.beadloom(project, "ctx", ref_id, "--json", "--project", str(project))
    if done.returncode != 0:
        return None, f"ctx {ref_id} --json exited {done.returncode}: {done.stderr.strip()[-300:]}"
    focus = json.loads(done.stdout).get("focus") or {}
    activity = focus.get("activity")
    if not isinstance(activity, dict):
        return None, f"ctx {ref_id} --json carries no focus.activity"
    return activity, ""


def check_activity(room: Room, project: Path, report: Report) -> None:
    name = "activity: ctx --json carries the five-level activity and lines_30d"
    sources = _graph_sources(room, project)
    expected = {
        _CHANGED_RECENTLY: {"hot", "warm", "cool"},
        _CHANGED_IN_90_DAYS: {"quiet"},
        _UNTOUCHED: {"dormant"},
    }
    missing = [source for source in expected if source not in sources]
    if missing:
        report.record(name, "behaviour", passed=False, detail=f"init wrote no node for {missing}")
        return
    problems: list[str] = []
    seen: list[str] = []
    lines_of: dict[str, object] = {}
    # The root node's source is the whole project (``''``); activity is measured on the
    # nodes that own a source directory, so the root is not asked.
    for source, ref_id in sorted(item for item in sources.items() if item[0]):
        activity, why = _activity(room, project, ref_id)
        if activity is None:
            problems.append(why)
            continue
        lines_of[source] = activity.get("lines_30d")
        level, lines = activity.get("level"), activity.get("lines_30d")
        seen.append(f"{ref_id}={level}/{lines}")
        if level not in ACTIVITY_LEVELS:
            problems.append(f"{ref_id}: level {level!r} is not one of the five")
        if not isinstance(lines, int) or isinstance(lines, bool):
            problems.append(f"{ref_id}: lines_30d is {lines!r}, not an integer")
        if source in expected and level not in expected[source]:
            problems.append(f"{ref_id} ({source}): level {level!r}, expected {expected[source]}")
    recent_lines = lines_of.get(_CHANGED_RECENTLY)
    if _CHANGED_RECENTLY in lines_of and not (isinstance(recent_lines, int) and recent_lines > 0):
        problems.append(
            f"{sources[_CHANGED_RECENTLY]}: lines_30d {recent_lines!r} "
            "after a change five days ago"
        )
    report.record(
        name,
        "behaviour",
        passed=not problems,
        detail="; ".join(problems) if problems else ", ".join(seen),
    )


def check_shallow_history(room: Room, project: Path, report: Report) -> None:
    name = "shallow history: reindex on a --depth 1 clone prints the Activity line"
    clone = room.workdir / "shallow"
    try:
        room.git(room.workdir, "clone", "-q", "--depth", "1", project.as_uri(), str(clone))
    except CannotRunError as exc:
        report.cannot_run(name, "behaviour", str(exc))
        return
    done = room.beadloom(clone, "reindex", "--project", str(clone))
    lines = [line for line in done.stdout.splitlines() if line.startswith("Activity:")]
    passed = done.returncode == 0 and any("history: shallow (1 commit)" in line for line in lines)
    report.record(
        name,
        "behaviour",
        passed=passed,
        detail=(lines[0] if lines else "no 'Activity:' line") + f" (rc {done.returncode})",
    )


def _first_line(text: str) -> str:
    """The first non-empty line of *text*, for a one-line detail."""
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def _last_line(text: str) -> str:
    """The last non-empty line of *text*: where a CLI states the error after its usage."""
    return next((line.strip() for line in reversed(text.splitlines()) if line.strip()), "")


def check_portal(room: Room, project: Path, report: Report) -> None:
    site = project / "site"
    scaffold = "portal scaffold: docs site --out writes package.json, .vitepress/, e2e/"
    build = f"portal build: npm ci and npm run docs:build under Node {NODE_MAJOR}+"
    done = room.beadloom(project, "docs", "site", "--out", str(site), "--project", str(project))
    absent = [
        f"{entry}/" if kind == "dir" else entry
        for entry, kind in SCAFFOLD_ENTRIES
        if not ((site / entry).is_dir() if kind == "dir" else (site / entry).is_file())
    ]
    written = report.record(
        scaffold,
        "behaviour",
        passed=done.returncode == 0 and not absent,
        detail=f"rc {done.returncode}; absent: {absent or 'none'}; {_first_line(done.output)}",
    )
    if not written:
        report.not_run(build, "behaviour", "the scaffold was not written")
        return
    for step in (["npm", "ci", "--no-audit", "--no-fund"], ["npm", "run", "docs:build"]):
        done = room.run(step, site)
        if done.returncode != 0:
            report.record(
                build,
                "behaviour",
                passed=False,
                detail=f"{' '.join(step)} exited {done.returncode}: {done.output.strip()[-600:]}",
            )
            return
    report.record(
        build,
        "behaviour",
        passed=(site / ".vitepress" / "dist" / "index.html").is_file(),
        detail="built .vitepress/dist/index.html",
    )


def check_pages_workflow(room: Room, project: Path, report: Report) -> None:
    name = f"pages workflow: docs site --pages-workflow writes it with '{FULL_FETCH}'"
    site = project / "site"
    done = room.beadloom(
        project, "docs", "site", "--out", str(site), "--pages-workflow", "--project", str(project)
    )
    workflow = project / PAGES_WORKFLOW
    text = workflow.read_text(encoding="utf-8") if workflow.is_file() else ""
    report.record(
        name,
        "behaviour",
        passed=done.returncode == 0 and FULL_FETCH in text,
        detail=(
            f"rc {done.returncode}; {PAGES_WORKFLOW} "
            f"{'written' if text else 'absent'}; "
            f"{FULL_FETCH!r} {'present' if FULL_FETCH in text else 'absent'}; "
            f"{_first_line(done.stdout) if done.returncode == 0 else _last_line(done.stderr)}"
        ),
    )


def check_project(room: Room, report: Report) -> None:
    project = room.workdir / "quayside"
    project.mkdir()
    write_project(room, project, int(time.time()))
    done = room.beadloom(project, "init", "--yes", "--project", str(project))
    if not report.record(
        "init: beadloom init --yes exits 0",
        "behaviour",
        passed=done.returncode == 0,
        detail=f"rc {done.returncode}: {done.output.strip()[-300:]}",
    ):
        for remaining in ("reindex", "activity", "shallow history", "portal", "pages workflow"):
            report.not_run(remaining, "behaviour", "init failed")
        return
    declare_portal(project)
    room.git(project, "add", "-A")
    room.git(project, "commit", "-q", "-m", "beadloom: the graph and the portal's identity")
    done = room.beadloom(project, "reindex", "--project", str(project))
    activity_lines = [line for line in done.stdout.splitlines() if line.startswith("Activity:")]
    report.record(
        "reindex: exits 0 and names no shallow history on a full history",
        "behaviour",
        passed=done.returncode == 0 and not activity_lines,
        detail=f"rc {done.returncode}; Activity lines: {activity_lines or 'none'}",
    )
    check_activity(room, project, report)
    check_shallow_history(room, project, report)
    check_portal(room, project, report)
    check_pages_workflow(room, project, report)


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


def _node_major(room: Room) -> tuple[int, str]:
    node = shutil.which("node", path=room.env["PATH"])
    if node is None:
        raise CannotRunError("no node on PATH; pass --node-bin with a Node 22+ bin directory")
    done = room.run([node, "--version"], room.workdir)
    version = done.stdout.strip()
    try:
        return int(version.lstrip("v").split(".")[0]), f"{version} ({node})"
    except ValueError as exc:
        raise CannotRunError(f"{node} --version printed {version!r}") from exc


def prepare(room: Room, artifact: Artifact, python: str, report: Report) -> None:
    """Check the tools, then create the fresh environment and install the artifact into it."""
    for tool in ("uv", "git"):
        if shutil.which(tool, path=room.env["PATH"]) is None:
            raise CannotRunError(f"no {tool} on PATH")
    major, node = _node_major(room)
    if major < NODE_MAJOR:
        raise CannotRunError(f"node {node} is older than {NODE_MAJOR}; pass --node-bin")
    done = room.run(["uv", "venv", "-q", "--python", python, str(room.venv)], room.workdir)
    if done.returncode != 0:
        raise CannotRunError(f"uv venv exited {done.returncode}: {done.output.strip()}")
    done = room.run(
        [
            "uv",
            "pip",
            "install",
            "--refresh",
            "--python",
            str(room.bin / "python"),
            artifact.install,
        ],
        room.workdir,
    )
    if done.returncode != 0:
        unserved = not artifact.is_wheel and "no version of beadloom" in done.output.lower()
        raise CannotRunError(
            f"the index holds no {artifact.install}: {done.output.strip()[-400:]}"
            if unserved
            else f"uv pip install exited {done.returncode}: {done.output.strip()[-400:]}",
            exit_code=_EXIT_VERSION if unserved else _EXIT_CANNOT_RUN,
        )
    interpreter = room.run(
        [str(room.bin / "python"), "-I", "-c", "import sys; print(sys.version)"], room.workdir
    )
    report.room = {
        "platform": f"{platform.system()} {platform.machine()}",
        "python": interpreter.stdout.strip().split()[0] if interpreter.stdout else python,
        "node": node,
        "workdir": str(room.workdir),
    }


#: What a failure while the adopter project is written and committed is reported as.
_PROJECT_STEP = "project: the adopter project is written and committed"


def verify(
    artifact: Artifact, *, release: str, python: str, node_bin: Path | None, workdir: Path
) -> Report:
    room = Room(workdir, node_bin)
    report = Report(artifact=artifact.install, release=release)
    prepare(room, artifact, python, report)
    check_versions(room, artifact, report)
    try:
        check_project(room, report)
    except CannotRunError as exc:
        report.cannot_run(_PROJECT_STEP, "behaviour", str(exc))
    return report


def render(report: Report) -> str:
    lines = [
        f"artifact: {report.artifact}",
        f"release expected: {report.release}",
        "room: " + ", ".join(f"{key} {value}" for key, value in report.room.items()),
        "",
    ]
    lines += [
        f"{check.status:<8} {check.name}\n         {check.detail}" for check in report.checks
    ]
    failed = [check for check in report.checks if check.status != "PASS"]
    first = report.first_failure()
    lines.append("")
    if first is None:
        lines.append(f"VERDICT: {len(report.checks)} of {len(report.checks)} checks hold (exit 0)")
    else:
        incomplete = any(check.status == _CANNOT_RUN for check in failed)
        lines.append(
            f"VERDICT: {len(failed)} of {len(report.checks)} checks fail "
            f"(exit {report.exit_code()}); the first: {first.name}"
            + ("; a step could not run, so the verdict is incomplete" if incomplete else "")
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Beadloom wheel or PyPI pin on a throwaway adopter project.",
        epilog=(
            "usage example: python3 tests/release/verify_the_release.py beadloom==8.0.0 "
            "--node-bin $HOME/.nvm/versions/node/v22.9.0/bin"
        ),
    )
    parser.add_argument("artifact", help="a beadloom-*.whl path, or an exact pin beadloom==X.Y.Z")
    parser.add_argument("--release", default=DEFAULT_RELEASE, help="the version expected")
    parser.add_argument("--python", default="3.12", help="the fresh environment's interpreter")
    parser.add_argument("--node-bin", type=Path, default=None, help="a Node 22+ bin directory")
    parser.add_argument("--keep", action="store_true", help="keep the scratch directory")
    parser.add_argument("--record-json", type=Path, default=None, help="write the report here")
    options = parser.parse_args(argv)
    workdir = Path(tempfile.mkdtemp(prefix="beadloom-release-"))
    try:
        artifact = parse_artifact(options.artifact)
        report = verify(
            artifact,
            release=options.release,
            python=options.python,
            node_bin=options.node_bin,
            workdir=workdir,
        )
    except CannotRunError as exc:
        sys.stderr.write(f"CANNOT RUN (exit {exc.exit_code}): {exc}\n")
        return exc.exit_code
    finally:
        if options.keep:
            sys.stderr.write(f"kept {workdir}\n")
        else:
            shutil.rmtree(workdir, ignore_errors=True)
    sys.stdout.write(render(report))
    if options.record_json is not None:
        payload = {**asdict(report), "exit": report.exit_code()}
        options.record_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
