"""Verify one Beadloom artifact on a project that is not this repository.

Usage::

    python3 tests/release/verify_the_release.py <wheel path | beadloom==X.Y.Z>
        [--release 9.0.0] [--node-bin DIR] [--python 3.12] [--keep] [--record-json PATH]

The artifact is either a built wheel or an exact PyPI pin. It is installed with its
``languages`` extra, so TypeScript and Vue are parsed, into a FRESH virtual environment made
by ``uv`` in a new temporary directory, with ``UV_NO_CACHE=1`` and ``--refresh``, so the
verdict is about that artifact and not about whatever the machine already held. The checks
then run that environment's ``beadloom`` on two throwaway projects the script writes itself.
The first is a Python adopter: three modules with imports between them, a README, a ``docs/``
folder, a test, a node declared ``kind: site``, and a git history dated so that the three
modules fall into three different activity levels. The second is a Feature-Sliced Vue
frontend with three planted violations, the tree ``tests/support/fsd_tree.py`` holds; it is
copied here because this script imports nothing of the suite.

The checks, in the order they run and are reported:

* **version** -- ``beadloom --version``, ``beadloom.__version__`` and the installed
  distribution's metadata read ``--release``; the imported module is the one inside the
  fresh environment; a wheel's file name states the same version as its metadata.
* **languages** -- the fresh environment imports the TypeScript parser the extra installs.
* **init** and **reindex** exit 0; on a full history the reindex prints no shallow-history
  line.
* **site alias** -- the node declared ``kind: site`` is ``service`` in ``ctx --json``, and the
  reindex prints an ``[info]`` line naming it as read through the alias.
* **activity** -- ``ctx --json`` carries ``activity.level`` from the five levels (hot, warm,
  cool, quiet, dormant) and an integer ``lines_30d`` for every node that owns a source
  directory (the root, whose source is the whole project, carries none), and the dated history
  lands where it was written to land: the module changed five days ago is hot, warm or
  cool, the one changed 45 days ago is quiet, the one untouched for 300 days is dormant.
* **shallow history** -- on a ``--depth 1`` clone the reindex prints the ``Activity:`` line
  naming the shallow history.
* **portal scaffold** -- ``docs site --out`` writes ``package.json``, ``.vitepress/`` and
  ``e2e/``.
* **portal steiger** -- it writes ``steiger.config.js`` and a ``lint:fsd`` script.
* **portal brand** -- it writes ``public/brand/`` with Beadloom's icon, the SVG favicon and
  the two PNG favicons.
* **portal footer** -- it writes the ``widgets/powered-by/`` slice of the theme.
* **portal build** -- ``npm ci`` and ``npm run docs:build`` succeed under Node 22 or later.
* **portal assets** -- the built portal serves the brand files, links the SVG favicon and
  draws "Powered by Beadloom".
* **portal lint:fsd** -- ``npm run lint:fsd`` (Steiger) passes on the scaffold as shipped.
* **pages workflow** -- ``docs site --pages-workflow`` writes
  ``.github/workflows/beadloom-portal.yml`` with ``fetch-depth: 0``.
* **fsd init** -- on the Feature-Sliced project ``init --yes`` exits 1 and names the planted
  cross-import among the code's crossings of the rules it wrote.
* **fsd preset**, **fsd rules**, **fsd steiger** -- it writes ``preset: fsd``, the nine FSD
  rules into ``rules.yml`` and a ``lint:fsd`` script into the project's ``package.json``.
* **fsd lint** -- ``lint --strict`` exits 1 and reports the planted cross-import
  ``features-cart -> features-auth``, which only the Vite alias ``init`` read resolves.

The three npm checks need Node 22+ and npm. With ``--node-bin`` they are required, and a
directory that holds neither stops the run before it starts. Without it they run when ``PATH``
holds both, and are otherwise ``SKIPPED``: not counted in the verdict, and named under it with
the reason, so a run on a machine with no usable Node says what it did not run.

The report names every check, and the FIRST that did not pass. A check whose step it depends
on failed is listed as ``NOT RUN`` with the reason: the project's checks after a failed
``init``, and the portal build after a scaffold that was not written. A step that cannot run
once the checks have started is recorded as ``CANNOT RUN``, and the report is printed and
recorded all the same. The shallow clone failing stops only its own check. A ``git`` command
that fails while the project is written or committed stops every project check not yet
reached, and each is listed as ``NOT RUN``. A child that exits 0 and prints no JSON where JSON
was asked for fails its check, and the detail quotes what it printed.

Exit codes: 0 every check that ran holds, and the ones ``SKIPPED`` are named under the
verdict; 2 the run could not start (an unpinned or unknown artifact, no ``uv``/``git``, a
``--node-bin`` with no Node 22+ and npm, an install that failed) or a step could not run, so
the verdict is incomplete; 3 a version check failed, or the index serves no such pin; 4 a
behaviour check failed and every version check held. When a run has several, the order is
3, then 4, then 2: a check that ran and failed already settles that the artifact is not the
release, and the checks an incomplete run did not reach cannot overturn that.

It uses the standard library only, so any Python 3.10+ can run it, and it needs ``uv`` and
``git`` on ``PATH``, and ``node``/``npm`` for the portal build (``--node-bin`` puts a Node
directory first).
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
DEFAULT_RELEASE = "9.0.0"

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

#: The extra the artifact is installed with: the parsers of TypeScript, Vue and the rest.
LANGUAGES_EXTRA = "languages"

#: Steiger's configuration in the portal scaffold, and the script that runs it.
STEIGER_CONFIG = "steiger.config.js"
LINT_FSD = "lint:fsd"

#: The brand files ``docs site`` writes, relative to the portal; the built portal serves
#: them under ``brand/``.
BRAND_FILES = (
    "public/brand/beadloom-icon.svg",
    "public/brand/beadloom-favicon.svg",
    "public/brand/beadloom-favicon.png",
    "public/brand/beadloom-favicon-dark.png",
)

#: The theme's slice that draws the "Powered by Beadloom" footer, entered through its index.
FOOTER_WIDGET = ".vitepress/theme/widgets/powered-by"

#: What the built portal's index page carries when the brand and the footer were built.
FAVICON_LINK = "brand/beadloom-favicon.svg"
POWERED_BY = "Powered by Beadloom"

#: The node the adopter declares ``kind: site``, and the kind it must be read as.
PORTAL_NODE = "quayside-portal"
SITE_ALIAS_TARGET = "service"

#: The nine rules ``init`` writes for a Feature-Sliced frontend.
FSD_RULES = (
    "fsd-layers",
    "fsd-public-api",
    "fsd-slice-shape",
    "fsd-cohesion-app",
    "fsd-cohesion-pages",
    "fsd-cohesion-widgets",
    "fsd-cohesion-features",
    "fsd-cohesion-entities",
    "fsd-cohesion-shared",
)

#: The cross-import planted inside the features layer, through the Vite alias ``@features``.
PLANTED_CROSSING = ("features-cart", "features-auth")

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

#: The status of a check this run was not equipped to make, such as the portal build on a
#: machine with no Node 22+: not counted in the verdict, and named under it.
_SKIPPED = "SKIPPED"

#: How much of a child's output a check's detail quotes.
_EXCERPT = 300

#: The adopter project's checks in the order they run, by the stage each check's name begins
#: with; a check not reached is listed under its stage.
_PROJECT_STAGES = (
    "init",
    "reindex",
    "site alias",
    "activity",
    "shallow history",
    "portal scaffold",
    "portal steiger",
    "portal brand",
    "portal footer",
    "portal build",
    "portal assets",
    "portal lint:fsd",
    "pages workflow",
)

#: The Feature-Sliced project's checks in the order they run, by the stage each name begins
#: with.
_FSD_STAGES = ("fsd init", "fsd preset", "fsd rules", "fsd steiger", "fsd lint")


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
    """One assertion and its outcome: ``PASS``, ``FAIL``, ``NOT RUN``, ``CANNOT RUN`` or
    ``SKIPPED``.

    ``NOT RUN`` is a check skipped because a check or a step it depends on did not pass;
    ``CANNOT RUN`` is a check whose own step failed for a reason outside the artifact;
    ``SKIPPED`` is a check this run was not equipped to make, which the verdict does not
    count and names under it.
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

    def skipped(self, name: str, kind: str, why: str) -> None:
        self.checks.append(Check(name, kind, _SKIPPED, why))

    def ran(self) -> list[Check]:
        """The checks this run made: every check but the ones ``SKIPPED``."""
        return [check for check in self.checks if check.status != _SKIPPED]

    def not_asked(self) -> list[Check]:
        """The checks this run was not equipped to make."""
        return [check for check in self.checks if check.status == _SKIPPED]

    def first_failure(self) -> Check | None:
        return next((check for check in self.ran() if check.status != "PASS"), None)

    def exit_code(self) -> int:
        """3, then 4, then 2: a check that ran and failed outranks an incomplete run."""
        failed = [check for check in self.ran() if check.status != "PASS"]
        if any(check.kind == "version" for check in failed):
            return _EXIT_VERSION
        if any(check.status == "FAIL" for check in failed):
            return _EXIT_BEHAVIOUR
        if any(check.status == _CANNOT_RUN for check in failed):
            return _EXIT_CANNOT_RUN
        return _EXIT_BEHAVIOUR if failed else _EXIT_OK

    def not_reached(self, stages: tuple[str, ...], why: str) -> None:
        """List as ``NOT RUN`` each of *stages* no check of this report names yet."""
        for stage in stages:
            if not any(
                check.name == stage or check.name.startswith(f"{stage}:") for check in self.checks
            ):
                self.not_run(stage, "behaviour", why)


@dataclass(frozen=True)
class Done:
    """A finished child process."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


def install_spec(artifact: Artifact) -> str:
    """What ``uv pip install`` is given: the artifact with its ``languages`` extra."""
    if artifact.is_wheel:
        return f"{artifact.install}[{LANGUAGES_EXTRA}]"
    name, version = artifact.install.split("==", 1)
    return f"{name}[{LANGUAGES_EXTRA}]=={version}"


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
        #: Why the npm checks are skipped, or empty when they run; :func:`prepare` decides.
        self.npm_skip = ""
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
    """What the adopter writes after ``init``: the portal's identity under ``site:``, and the
    portal as a node of the graph, declared ``kind: site`` as graphs before 9.0.0 declared it.
    """
    _append(
        root,
        ".beadloom/config.yml",
        "site:\n  title: Quayside\n  base: /quayside/\n"
        "  repo_url: https://github.com/harbour-works/quayside\n",
    )
    (root / ".beadloom" / "_graph" / "portal.yml").write_text(
        f"nodes:\n  - ref_id: {PORTAL_NODE}\n    kind: site\n"
        '    summary: "The project portal beadloom docs site writes"\n',
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# The throwaway Feature-Sliced project
# ---------------------------------------------------------------------------

#: A synthetic Feature-Sliced Vue frontend: six layers under ``src/``, a tsconfig ``@/*``
#: path, a Vite alias ``@features`` no tsconfig carries, two legacy folders, and three planted
#: violations -- a deep import past ``features/auth``'s index, the cross-import
#: ``features/cart -> features/auth`` through the Vite alias, and a ``helpers/`` folder that
#: is no segment. A copy of ``tests/support/fsd_tree.py``'s tree, which a self-check holds
#: equal to it: this script imports nothing of the suite.
FSD_PROJECT_FILES: dict[str, str] = {
    "package.json": (
        "{\n"
        '  "name": "orchard-web",\n'
        '  "private": true,\n'
        '  "scripts": {"dev": "vite"},\n'
        '  "dependencies": {"vue": "3.5.0"},\n'
        '  "devDependencies": {"vite": "6.0.0", "typescript": "5.6.0"}\n'
        "}\n"
    ),
    "tsconfig.json": (
        "{\n"
        "  // the app's paths\n"
        '  "compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}},\n'
        "}\n"
    ),
    "vite.config.ts": (
        "import { defineConfig } from 'vite'\n"
        "export default defineConfig({\n"
        "  resolve: { alias: { '@features': './src/features' } },\n"
        "})\n"
    ),
    "src/main.ts": (
        "import { createApp } from 'vue'\nimport { mountApp } from './app'\nmountApp(createApp)\n"
    ),
    "src/app/index.ts": (
        "export { router } from './providers/router'\n"
        "export function mountApp(f: unknown) { return f }\n"
    ),
    "src/app/providers/router.ts": (
        "import { HomePage } from '@/pages/home'\n"
        "import { ProfilePage } from '@/pages/profile'\n"
        "export const router = [HomePage, ProfilePage]\n"
    ),
    "src/app/styles/theme.ts": ("export const theme = { dark: false }\n"),
    "src/pages/home/index.ts": ("export { default as HomePage } from './ui/HomePage.vue'\n"),
    "src/pages/home/ui/HomePage.vue": (
        '<script setup lang="ts">\n'
        "import { Header } from '@/widgets/header'\n"
        "import { LoginForm } from '@/features/auth'\n"
        "</script>\n"
        "<template><Header /><LoginForm /></template>\n"
    ),
    "src/pages/profile/index.ts": ("export { ProfilePage } from './ui/ProfilePage'\n"),
    "src/pages/profile/ui/ProfilePage.ts": (
        "import { userName } from '@/entities/user'\n"
        "export function ProfilePage() { return userName() }\n"
    ),
    "src/widgets/header/index.ts": ("export { Header } from './ui/Header'\n"),
    # PLANTED: a deep import past features/auth's index (public API sidestep).
    "src/widgets/header/ui/Header.ts": (
        "import { currentSession } from '@/features/auth/model/session'\n"
        "import { userName } from '@/entities/user'\n"
        "export function Header() { return [currentSession(), userName()] }\n"
    ),
    "src/features/auth/index.ts": (
        "export { LoginForm } from './ui/LoginForm'\n"
        "export { currentSession } from './model/session'\n"
    ),
    "src/features/auth/ui/LoginForm.ts": (
        "import { currentSession } from '../model/session'\n"
        "import { Button } from '@/shared/ui'\n"
        "export function LoginForm() { return [Button(), currentSession()] }\n"
    ),
    "src/features/auth/model/session.ts": (
        "import { userName } from '@/entities/user'\n"
        "import { client } from '@/shared/api'\n"
        "export function currentSession() { return [userName(), client] }\n"
    ),
    "src/features/cart/index.ts": ("export { addToCart } from './model/cart'\n"),
    # PLANTED: a cross-import inside the features layer, through the Vite alias.
    "src/features/cart/model/cart.ts": (
        "import { currentSession } from '@features/auth'\n"
        "import { formatPrice } from '../helpers/format'\n"
        "import { productTitle } from '@/entities/product'\n"
        "export function addToCart() {\n"
        "  return [currentSession(), formatPrice(1), productTitle()]\n"
        "}\n"
    ),
    # PLANTED: `helpers/` is not one of FSD's standard segments.
    "src/features/cart/helpers/format.ts": (
        "export function formatPrice(n: number) { return `${n}` }\n"
    ),
    "src/entities/user/index.ts": ("export { userName } from './model/user'\n"),
    "src/entities/user/model/user.ts": (
        "import { capitalise } from '@/shared/lib'\n"
        "export function userName() { return capitalise('ann') }\n"
    ),
    "src/entities/product/index.ts": ("export { productTitle } from './model/product'\n"),
    "src/entities/product/model/product.ts": (
        "import { capitalise } from '@/shared/lib'\n"
        "export function productTitle() { return capitalise('pear') }\n"
    ),
    "src/shared/api/index.ts": ("export const client = { get: (u: string) => u }\n"),
    "src/shared/lib/index.ts": (
        "export function capitalise(s: string) { return s.toUpperCase() }\n"
    ),
    "src/shared/ui/index.ts": ("export { Button } from './button'\n"),
    "src/shared/ui/button.ts": (
        "import { capitalise } from '../lib'\n"
        "export function Button() { return capitalise('ok') }\n"
    ),
    # Legacy folders beside the layers, from before the project moved to FSD.
    "src/components/LegacyButton.ts": (
        "import { Button } from '@/shared/ui'\n"
        "export function LegacyButton() { return Button() }\n"
    ),
    "src/hooks/useCart.ts": (
        "import { addToCart } from '@/features/cart'\n"
        "export function useCart() { return addToCart() }\n"
    ),
}


def write_fsd_project(room: Room, root: Path) -> None:
    """The Feature-Sliced project, committed in one commit."""
    for relative, text in FSD_PROJECT_FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    room.git(root, "init", "-q")
    room.git(root, "add", "-A")
    room.git(root, "commit", "-q", "-m", "the frontend")


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------


def _json_object(text: str, what: str) -> tuple[dict[str, object] | None, str]:
    """*text* read as a JSON object, or ``None`` and why not, quoting what *what* printed."""
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"{what} printed no JSON ({exc}): {text.strip()[-_EXCERPT:]!r}"
    if not isinstance(loaded, dict):
        return None, f"{what} printed JSON that is not an object: {text.strip()[-_EXCERPT:]!r}"
    return loaded, ""


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
    parsed, why = (
        _json_object(done.stdout, "the version probe")
        if done.returncode == 0
        else (None, f"the version probe exited {done.returncode}: {done.stderr[-_EXCERPT:]}")
    )
    found: dict[str, object] = parsed or {}
    unread = f"; {why}" if why else ""
    report.record(
        "version: beadloom.__version__",
        "version",
        passed=found.get("version") == release,
        detail=f"reads {found.get('version')!r}, expected {release}{unread}",
    )
    report.record(
        "version: importlib.metadata.version('beadloom')",
        "version",
        passed=found.get("metadata") == release,
        detail=f"reads {found.get('metadata')!r}, expected {release}{unread}",
    )
    module = Path(str(found.get("file", "")))
    report.record(
        "version: the imported module is the one in the fresh environment",
        "version",
        passed=bool(found) and room.venv.resolve() in module.resolve().parents,
        detail=f"beadloom imported from {module}{unread}",
    )
    if artifact.is_wheel:
        report.record(
            "version: the wheel's file name states its metadata's version",
            "version",
            passed=artifact.claimed_version == found.get("metadata"),
            detail=(
                f"file name says {artifact.claimed_version}, metadata says "
                f"{found.get('metadata')!r}{unread}"
            ),
        )


def check_languages(room: Room, report: Report) -> None:
    probe = "import tree_sitter_typescript; print(tree_sitter_typescript.__name__)"
    done = room.run([str(room.bin / "python"), "-I", "-c", probe], room.workdir)
    report.record(
        f"languages: the {LANGUAGES_EXTRA} extra installed the TypeScript parser",
        "behaviour",
        passed=done.returncode == 0,
        detail=(
            "tree_sitter_typescript imports"
            if done.returncode == 0
            else f"rc {done.returncode}: {_last_line(done.stderr)}"
        ),
    )


def _yaml_documents(room: Room, project: Path, *paths: Path) -> tuple[list[object] | None, str]:
    """Each of *paths* read as YAML by the fresh environment's PyYAML (``None`` when absent)."""
    probe = (
        "import json, pathlib, sys, yaml\n"
        "print(json.dumps([yaml.safe_load(pathlib.Path(p).read_text(encoding='utf-8'))"
        " if pathlib.Path(p).is_file() else None for p in sys.argv[1:]]))\n"
    )
    command = [str(room.bin / "python"), "-I", "-c", probe, *map(str, paths)]
    done = room.run(command, project)
    if done.returncode != 0:
        return None, f"the YAML probe exited {done.returncode}: {done.stderr[-_EXCERPT:]}"
    try:
        loaded = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        return None, f"the YAML probe printed no JSON ({exc}): {done.stdout[-_EXCERPT:]!r}"
    if not isinstance(loaded, list) or len(loaded) != len(paths):
        return None, f"the YAML probe printed {done.stdout[-_EXCERPT:]!r}"
    return loaded, ""


def _package_scripts(package: Path) -> tuple[dict[str, object], str]:
    """The ``scripts`` of the ``package.json`` at *package*, or why there are none."""
    if not package.is_file():
        return {}, f"{package.name} absent"
    try:
        loaded = json.loads(package.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, f"{package.name} is no JSON ({exc})"
    scripts = loaded.get("scripts") if isinstance(loaded, dict) else None
    return (scripts, "") if isinstance(scripts, dict) else ({}, f"{package.name} has no scripts")


def _graph_sources(room: Room, project: Path) -> tuple[dict[str, str], str]:
    """Each node's source directory mapped to its ref_id, or why the graph could not be read."""
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
        return {}, f"the graph probe exited {done.returncode}: {done.stderr[-_EXCERPT:]}"
    loaded, why = _json_object(done.stdout, "the graph probe")
    if loaded is None:
        return {}, why
    return {str(source): str(ref_id) for source, ref_id in loaded.items()}, ""


def _activity(room: Room, project: Path, ref_id: str) -> tuple[dict[str, object] | None, str]:
    done = room.beadloom(project, "ctx", ref_id, "--json", "--project", str(project))
    if done.returncode != 0:
        return None, f"ctx {ref_id} --json exited {done.returncode}: {done.stderr.strip()[-300:]}"
    loaded, why = _json_object(done.stdout, f"ctx {ref_id} --json")
    if loaded is None:
        return None, why
    focus = loaded.get("focus")
    activity = focus.get("activity") if isinstance(focus, dict) else None
    if not isinstance(activity, dict):
        return None, f"ctx {ref_id} --json carries no focus.activity"
    return activity, ""


def check_site_alias(room: Room, project: Path, reindexed: str, report: Report) -> None:
    """The node declared ``kind: site`` is read as a service, and the reindex said so."""
    done = room.beadloom(project, "ctx", PORTAL_NODE, "--json", "--project", str(project))
    loaded, why = (
        _json_object(done.stdout, f"ctx {PORTAL_NODE} --json")
        if done.returncode == 0
        else (
            None,
            f"ctx {PORTAL_NODE} --json exited {done.returncode}: {_last_line(done.output)}",
        )
    )
    focus = (loaded or {}).get("focus")
    kind = focus.get("kind") if isinstance(focus, dict) else None
    report.record(
        f"site alias: ctx --json reads the kind: site node as a {SITE_ALIAS_TARGET}",
        "behaviour",
        passed=kind == SITE_ALIAS_TARGET,
        detail=why or f"{PORTAL_NODE}: focus.kind {kind!r}, expected {SITE_ALIAS_TARGET!r}",
    )
    info = [
        line.strip()
        for line in reindexed.splitlines()
        if "[info]" in line and f"'{PORTAL_NODE}'" in line
    ]
    report.record(
        "site alias: reindex prints an [info] line for the node read through the alias",
        "behaviour",
        passed=any(f"read as '{SITE_ALIAS_TARGET}'" in line for line in info),
        detail=info[0] if info else f"no [info] line names {PORTAL_NODE}",
    )


def check_activity(room: Room, project: Path, report: Report) -> None:
    name = "activity: ctx --json carries the five-level activity and lines_30d"
    sources, unread = _graph_sources(room, project)
    if unread:
        report.record(name, "behaviour", passed=False, detail=unread)
        return
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


def check_scaffold_surfaces(site: Path, report: Report) -> None:
    """What 9.0.0 added to the scaffold: Steiger, the brand files and the footer's slice."""
    scripts, unread = _package_scripts(site / "package.json")
    steiger = (site / STEIGER_CONFIG).is_file()
    lint_fsd = scripts.get(LINT_FSD)
    report.record(
        f"portal steiger: docs site writes {STEIGER_CONFIG} and a {LINT_FSD} script",
        "behaviour",
        passed=steiger and isinstance(lint_fsd, str),
        detail=(
            f"{STEIGER_CONFIG} {'present' if steiger else 'absent'}; "
            f"{LINT_FSD}: {lint_fsd!r}{f' ({unread})' if unread else ''}"
        ),
    )
    absent = [relative for relative in BRAND_FILES if not (site / relative).is_file()]
    report.record(
        "portal brand: docs site writes Beadloom's icon, the SVG favicon and two PNG favicons",
        "behaviour",
        passed=not absent,
        detail=f"absent: {absent}" if absent else ", ".join(BRAND_FILES),
    )
    index = f"{FOOTER_WIDGET}/index.js"
    footer = (site / index).is_file()
    report.record(
        "portal footer: docs site writes the powered-by widget of the theme",
        "behaviour",
        passed=footer,
        detail=f"{index} {'present' if footer else 'absent'}",
    )


def check_built_portal(site: Path, report: Report) -> None:
    """The built portal serves the brand files, links the SVG favicon and draws the footer."""
    dist = site / ".vitepress" / "dist"
    page = dist / "index.html"
    html = page.read_text(encoding="utf-8", errors="replace") if page.is_file() else ""
    absent = [
        f"brand/{name}"
        for name in (relative.rsplit("/", 1)[-1] for relative in BRAND_FILES)
        if not (dist / "brand" / name).is_file()
    ]
    if FAVICON_LINK not in html:
        absent.append(f"the favicon link to {FAVICON_LINK} in index.html")
    if POWERED_BY not in html:
        absent.append(f"{POWERED_BY!r} in index.html")
    report.record(
        "portal assets: the built portal serves the brand files and the footer",
        "behaviour",
        passed=not absent,
        detail=f"absent: {absent}" if absent else f"dist/brand/ served; {POWERED_BY!r} drawn",
    )


def check_portal(room: Room, project: Path, report: Report) -> None:
    site = project / "site"
    scaffold = "portal scaffold: docs site --out writes package.json, .vitepress/, e2e/"
    build = f"portal build: npm ci and npm run docs:build under Node {NODE_MAJOR}+"
    assets = "portal assets: the built portal serves the brand files and the footer"
    lint = f"portal {LINT_FSD}: npm run {LINT_FSD} (Steiger) passes on the scaffold"
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
        report.not_reached(
            ("portal steiger", "portal brand", "portal footer"), "the scaffold was not written"
        )
        for name in (build, assets, lint):
            report.not_run(name, "behaviour", "the scaffold was not written")
        return
    check_scaffold_surfaces(site, report)
    if room.npm_skip:
        for name in (build, assets, lint):
            report.skipped(name, "behaviour", room.npm_skip)
        return
    done = room.run(["npm", "ci", "--no-audit", "--no-fund"], site)
    if done.returncode != 0:
        report.record(
            build,
            "behaviour",
            passed=False,
            detail=f"npm ci exited {done.returncode}: {done.output.strip()[-600:]}",
        )
        report.not_run(assets, "behaviour", "npm ci failed")
        report.not_run(lint, "behaviour", "npm ci failed")
        return
    done = room.run(["npm", "run", "docs:build"], site)
    if report.record(
        build,
        "behaviour",
        passed=done.returncode == 0 and (site / ".vitepress" / "dist" / "index.html").is_file(),
        detail=(
            "built .vitepress/dist/index.html"
            if done.returncode == 0
            else f"npm run docs:build exited {done.returncode}: {done.output.strip()[-600:]}"
        ),
    ):
        check_built_portal(site, report)
    else:
        report.not_run(assets, "behaviour", "the portal was not built")
    done = room.run(["npm", "run", LINT_FSD], site)
    said = _last_line(done.output) if done.returncode == 0 else _first_line(done.stderr)
    report.record(
        lint,
        "behaviour",
        passed=done.returncode == 0,
        detail=f"rc {done.returncode}: {said or _last_line(done.output)}",
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
        report.not_reached(_PROJECT_STAGES, "init failed")
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
    check_site_alias(room, project, done.output, report)
    check_activity(room, project, report)
    check_shallow_history(room, project, report)
    check_portal(room, project, report)
    check_pages_workflow(room, project, report)


def check_fsd_init(room: Room, project: Path, report: Report) -> None:
    """``init --yes`` exits 1, naming the planted cross-import among the code's crossings."""
    done = room.beadloom(project, "init", "--yes", "--project", str(project))
    named = f"fsd-layers: {PLANTED_CROSSING[0]}"
    report.record(
        "fsd init: init --yes exits 1 and names the code's crossing of the rules it wrote",
        "behaviour",
        passed=done.returncode == 1 and named in done.output,
        detail=(
            f"rc {done.returncode}; {named!r} {'named' if named in done.output else 'not named'}"
            f"; {_first_line(done.output[done.output.find('Graph:') :])}"
        ),
    )


def check_fsd_scaffold(room: Room, project: Path, report: Report) -> None:
    """What ``init`` wrote: ``preset: fsd``, the nine rules, and the ``lint:fsd`` script."""
    beadloom = project / ".beadloom"
    documents, unread = _yaml_documents(
        room, project, beadloom / "config.yml", beadloom / "_graph" / "rules.yml"
    )
    config, rules = documents if documents is not None else (None, None)
    preset = config.get("preset") if isinstance(config, dict) else None
    report.record(
        "fsd preset: init --yes writes preset: fsd",
        "behaviour",
        passed=preset == "fsd",
        detail=unread or f"preset {preset!r} in .beadloom/config.yml",
    )
    listed = rules.get("rules") if isinstance(rules, dict) else None
    names = [str(rule.get("name")) for rule in listed or [] if isinstance(rule, dict)]
    missing = [name for name in FSD_RULES if name not in names]
    report.record(
        f"fsd rules: init writes the {len(FSD_RULES)} FSD rules into rules.yml",
        "behaviour",
        passed=not unread and not missing,
        detail=unread
        or (f"missing: {missing}; written: {names}" if missing else ", ".join(names)),
    )
    scripts, absent = _package_scripts(project / "package.json")
    lint_fsd = scripts.get(LINT_FSD)
    report.record(
        f"fsd steiger: init writes a {LINT_FSD} script into the project's package.json",
        "behaviour",
        passed=isinstance(lint_fsd, str),
        detail=absent or f"{LINT_FSD}: {lint_fsd!r}",
    )


def check_fsd_lint(room: Room, project: Path, report: Report) -> None:
    """``lint --strict`` exits 1 and reports the cross-import planted through the alias."""
    name = "fsd lint: lint --strict reports the planted cross-import {} -> {}".format(
        *PLANTED_CROSSING
    )
    done = room.beadloom(
        project, "lint", "--strict", "--format", "json", "--project", str(project)
    )
    loaded, why = _json_object(done.stdout, "lint --strict --format json")
    if loaded is None:
        report.record(name, "behaviour", passed=False, detail=f"rc {done.returncode}; {why}")
        return
    listed = loaded.get("violations")
    violations = (
        [found for found in listed if isinstance(found, dict)] if isinstance(listed, list) else []
    )
    crossing = [
        found
        for found in violations
        if found.get("rule_name") == "fsd-layers"
        and found.get("severity") == "error"
        and (found.get("from_ref_id"), found.get("to_ref_id")) == PLANTED_CROSSING
    ]
    seen = [
        f"{found.get('rule_name')}:{found.get('from_ref_id')}->{found.get('to_ref_id')}"
        for found in violations
    ]
    report.record(
        name,
        "behaviour",
        passed=done.returncode == 1 and bool(crossing),
        detail=f"rc {done.returncode}; {len(violations)} violation(s): {seen}",
    )


#: What a failure while the Feature-Sliced project is written and committed is reported as.
_FSD_STEP = "fsd project: the Feature-Sliced project is written and committed"


def check_fsd_project(room: Room, report: Report) -> None:
    project = room.workdir / "orchard"
    project.mkdir()
    write_fsd_project(room, project)
    check_fsd_init(room, project, report)
    check_fsd_scaffold(room, project, report)
    check_fsd_lint(room, project, report)


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


def find_npm(room: Room, *, asked: bool) -> tuple[str, str]:
    """The Node the npm checks run under, and why they are skipped (empty when they run).

    When *asked* (``--node-bin`` was given), a directory without a Node 22+ and npm stops the
    run: the operator asked for the build. Otherwise what ``PATH`` holds decides, and a missing
    or old Node, or a missing npm, skips the npm checks with the reason.
    """
    hint = f"pass --node-bin with a Node {NODE_MAJOR}+ bin directory"
    node = shutil.which("node", path=room.env["PATH"])
    if node is None:
        if asked:
            raise CannotRunError(f"no node on PATH; {hint}")
        return "absent", f"no node on PATH; {hint}"
    done = room.run([node, "--version"], room.workdir)
    version = done.stdout.strip()
    try:
        major = int(version.lstrip("v").split(".")[0])
    except ValueError as exc:
        raise CannotRunError(f"{node} --version printed {version!r}") from exc
    described = f"{version} ({node})"
    if major < NODE_MAJOR:
        if asked:
            raise CannotRunError(f"node {described} is older than {NODE_MAJOR}; {hint}")
        return described, f"node {described} is older than {NODE_MAJOR}; {hint}"
    if shutil.which("npm", path=room.env["PATH"]) is None:
        if asked:
            raise CannotRunError(f"no npm beside node {described}")
        return described, f"no npm beside node {described}; {hint}"
    return described, ""


def prepare(room: Room, artifact: Artifact, python: str, report: Report, asked: bool) -> None:
    """Check the tools, then create the fresh environment and install the artifact into it."""
    for tool in ("uv", "git"):
        if shutil.which(tool, path=room.env["PATH"]) is None:
            raise CannotRunError(f"no {tool} on PATH")
    node, room.npm_skip = find_npm(room, asked=asked)
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
            install_spec(artifact),
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
        "npm checks": f"skipped ({room.npm_skip})" if room.npm_skip else "run",
        "workdir": str(room.workdir),
    }


#: What a failure while the adopter project is written and committed is reported as.
_PROJECT_STEP = "project: the adopter project is written and committed"


def verify(
    artifact: Artifact, *, release: str, python: str, node_bin: Path | None, workdir: Path
) -> Report:
    room = Room(workdir, node_bin)
    report = Report(artifact=artifact.install, release=release)
    prepare(room, artifact, python, report, node_bin is not None)
    check_versions(room, artifact, report)
    check_languages(room, report)
    try:
        check_project(room, report)
    except CannotRunError as exc:
        report.cannot_run(_PROJECT_STEP, "behaviour", str(exc))
        report.not_reached(_PROJECT_STAGES, "the project step could not run")
    try:
        check_fsd_project(room, report)
    except CannotRunError as exc:
        report.cannot_run(_FSD_STEP, "behaviour", str(exc))
        report.not_reached(_FSD_STAGES, "the Feature-Sliced project step could not run")
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
    ran = report.ran()
    failed = [check for check in ran if check.status != "PASS"]
    first = report.first_failure()
    counted = "checks that ran" if report.not_asked() else "checks"
    lines.append("")
    if first is None:
        lines.append(f"VERDICT: {len(ran)} of {len(ran)} {counted} hold (exit 0)")
    else:
        incomplete = any(check.status == _CANNOT_RUN for check in failed)
        lines.append(
            f"VERDICT: {len(failed)} of {len(ran)} {counted} fail "
            f"(exit {report.exit_code()}); the first: {first.name}"
            + ("; a step could not run, so the verdict is incomplete" if incomplete else "")
        )
    reasons: dict[str, list[str]] = {}
    for check in report.not_asked():
        reasons.setdefault(check.detail, []).append(check.name.split(": ", 1)[0])
    lines += [f"Not run by this run: {', '.join(names)} ({why})" for why, names in reasons.items()]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Beadloom wheel or PyPI pin on a throwaway adopter project.",
        epilog=(
            "usage example: python3 tests/release/verify_the_release.py "
            f"beadloom=={DEFAULT_RELEASE} --node-bin $HOME/.nvm/versions/node/v22.9.0/bin"
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
        payload = {
            **asdict(report),
            "skipped": [check.name for check in report.not_asked()],
            "exit": report.exit_code(),
        }
        options.record_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
