"""BDL-068 S4, `beadloom-gsal` (BDL-UX #231) — the typed surface a gate checks.

Three defects stacked in one hook leg, and the tests below hold each one down.
The leg ran ``mypy`` over every staged ``.py`` under ``src/`` or ``tests/``,
which is wider than anything this project declares typed. It kept
``2>/dev/null``, which does not hide mypy's findings -- those go to stdout --
but does hide the diagnostics of a mypy that could not START, so "found errors"
and "could not run" printed one sentence. And in the warn template it could not
stop anything, while in the blocking template it stopped almost everything.

The runtime cases drive the REAL emitted template through a real ``/bin/sh``
with stub ``uv``/``mypy`` on ``PATH``. A hook is shell text until something runs
it, and every property being pinned here is a property of what a committer sees.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.application.typed_surface import TypedSurface, declared_typed_surface
from beadloom.services.commands.docsync import (
    _HOOK_ENCODING,
    _HOOK_TEMPLATE_BLOCK,
    _HOOK_TEMPLATE_WARN,
    _hook_type_check,
)
from tests.ambient_codec import AMBIENT_CODECS, under_ambient_codec

if TYPE_CHECKING:
    from types import ModuleType

    from click.testing import Result

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write(project: Path, pyproject: str, *, tree: tuple[str, ...] = ()) -> Path:
    project.mkdir(parents=True, exist_ok=True)
    (project / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    for rel in tree:
        target = project / rel
        if rel.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x = 1\n", encoding="utf-8")
    return project


class TestTheSurfaceIsDerivedFromTheDeclaration:
    """`packages`, `modules` and `files` each name a surface; each is resolved."""

    def test_a_package_resolves_through_mypy_path(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\nmypy_path = "src"\n',
            tree=("src/demo/__init__.py",),
        )
        surface = declared_typed_surface(project)
        assert [r.path for r in surface.roots] == ["src/demo"]
        assert surface.roots[0].source == "[tool.mypy] packages = 'demo'"

    def test_a_package_resolves_at_the_root_when_mypy_path_is_absent(
        self, tmp_path: Path
    ) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\n',
            tree=("demo/__init__.py",),
        )
        assert [r.path for r in declared_typed_surface(project).roots] == ["demo"]

    def test_a_dotted_subpackage_resolves_to_its_directory(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo.inner"]\nmypy_path = "src"\n',
            tree=("src/demo/inner/__init__.py",),
        )
        assert [r.path for r in declared_typed_surface(project).roots] == [
            "src/demo/inner"
        ]

    def test_a_module_resolves_to_one_file(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\nmodules = ["solo"]\nmypy_path = "src"\n',
            tree=("src/solo.py",),
        )
        surface = declared_typed_surface(project)
        assert [r.path for r in surface.roots] == ["src/solo.py"]
        assert surface.contains("src/solo.py")
        assert not surface.contains("src/solo_helper.py")

    def test_files_entries_resolve_as_paths(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\nfiles = [\n  "src",   # a comment\n  "scripts",\n]\n',
            tree=("src/a.py", "scripts/b.py"),
        )
        assert sorted(r.path for r in declared_typed_surface(project).roots) == [
            "scripts",
            "src",
        ]

    def test_mypy_path_is_split_on_both_separators(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\nmypy_path = "lib:src"\n',
            tree=("src/demo/__init__.py",),
        )
        assert [r.path for r in declared_typed_surface(project).roots] == ["src/demo"]

    def test_an_overrides_table_is_not_a_surface(self, tmp_path: Path) -> None:
        """An override changes which findings are reported, never which files."""
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\nmypy_path = "src"\n\n'
            '[[tool.mypy.overrides]]\nmodule = ["vendor", "vendor.*"]\n'
            "ignore_missing_imports = true\n",
            tree=("src/demo/__init__.py", "vendor/__init__.py"),
        )
        assert [r.path for r in declared_typed_surface(project).roots] == ["src/demo"]

    def test_a_trailing_mypy_table_is_read(self, tmp_path: Path) -> None:
        """The last table in a file has no next `[` to stop the match at."""
        project = _write(
            tmp_path / "p",
            '[project]\nname = "demo"\n\n[tool.mypy]\npackages = ["demo"]\n',
            tree=("demo/__init__.py",),
        )
        assert [r.path for r in declared_typed_surface(project).roots] == ["demo"]


class TestContainmentIsOverSegments:
    """A prefix match would put a sibling directory inside the surface."""

    @pytest.fixture
    def surface(self, tmp_path: Path) -> TypedSurface:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\nmypy_path = "src"\n',
            tree=("src/demo/__init__.py",),
        )
        return declared_typed_surface(project)

    def test_a_file_under_the_root_is_inside(self, surface: TypedSurface) -> None:
        assert surface.contains("src/demo/deep/mod.py")

    def test_a_sibling_sharing_a_prefix_is_outside(self, surface: TypedSurface) -> None:
        assert not surface.contains("src/demo_extra/mod.py")

    def test_a_windows_separator_is_read_as_the_same_path(
        self, surface: TypedSurface
    ) -> None:
        assert surface.contains("src\\demo\\mod.py")


class TestWhatCouldNotBeResolvedIsPartOfTheAnswer:
    """A derivation that drops what it could not read hands back a clean list."""

    def test_a_package_that_resolves_to_nothing_is_named(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p", '[tool.mypy]\npackages = ["ghost"]\nmypy_path = "src"\n'
        )
        surface = declared_typed_surface(project)
        assert not surface.declared
        assert surface.unresolved[0].source == "[tool.mypy] packages = 'ghost'"
        assert "no directory or .py module for `ghost`" in surface.unresolved[0].why
        assert "none of its entries resolves" in (surface.why_undeclared or "")

    def test_an_exclude_pattern_is_declared_unapplied(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\nexclude = "generated/"\n',
            tree=("demo/__init__.py",),
        )
        surface = declared_typed_surface(project)
        reasons = [u.why for u in surface.unresolved if u.source == "[tool.mypy] exclude"]
        assert reasons and "does not apply it to files named on the command line" in reasons[0]

    def test_a_mypy_ini_beside_pyproject_is_named_as_unread(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\n',
            tree=("demo/__init__.py",),
        )
        (project / "mypy.ini").write_text("[mypy]\nfiles = other\n", encoding="utf-8")
        sources = [u.source for u in declared_typed_surface(project).unresolved]
        assert "mypy.ini" in sources

    def test_a_glob_matching_nothing_is_named(self, tmp_path: Path) -> None:
        project = _write(tmp_path / "p", '[tool.mypy]\nfiles = ["pkg_*"]\n')
        surface = declared_typed_surface(project)
        assert not surface.declared
        assert "matches nothing here" in surface.unresolved[0].why

    def test_a_glob_naming_one_root_resolves(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p", '[tool.mypy]\nfiles = ["pkg_*"]\n', tree=("pkg_one/a.py",)
        )
        assert [r.path for r in declared_typed_surface(project).roots] == ["pkg_one"]


class TestAnUndeclaredSurfaceIsUnjudgedNotClean:
    """Three ways to declare nothing, and each says which one it was."""

    def test_no_mypy_table(self, tmp_path: Path) -> None:
        project = _write(tmp_path / "p", '[tool.ruff]\nsrc = ["src", "tests"]\n')
        surface = declared_typed_surface(project)
        assert not surface.declared
        assert surface.why_undeclared == "pyproject.toml declares no [tool.mypy] section"

    def test_a_mypy_table_that_names_no_surface(self, tmp_path: Path) -> None:
        project = _write(tmp_path / "p", "[tool.mypy]\nstrict = true\n")
        surface = declared_typed_surface(project)
        assert not surface.declared
        assert "names no packages, modules or files" in (surface.why_undeclared or "")

    def test_an_empty_array_names_no_surface(self, tmp_path: Path) -> None:
        project = _write(tmp_path / "p", "[tool.mypy]\npackages = []\n")
        surface = declared_typed_surface(project)
        assert "names no packages, modules or files" in (surface.why_undeclared or "")

    def test_no_pyproject_at_all(self, tmp_path: Path) -> None:
        project = tmp_path / "p"
        project.mkdir()
        surface = declared_typed_surface(project)
        assert not surface.declared
        assert "no pyproject.toml" in (surface.why_undeclared or "")


class TestThePopulationHasThreeSentencesNotTwo:
    """A check whose population is empty must not read as a check that passed."""

    def _surface(self, tmp_path: Path, pyproject: str) -> TypedSurface:
        project = _write(tmp_path / "p", pyproject, tree=("src/demo/__init__.py",))
        return declared_typed_surface(project)

    def test_files_inside_the_surface_are_counted_as_checked(self, tmp_path: Path) -> None:
        surface = self._surface(
            tmp_path, '[tool.mypy]\npackages = ["demo"]\nmypy_path = "src"\n'
        )
        part = surface.partition(("src/demo/a.py", "tests/t.py", "docs/x.py"))
        assert part.inside == ("src/demo/a.py",)
        assert part.describe() == (
            "Typed surface (src/demo): 1 of 3 staged Python file(s) inside it, "
            "2 outside."
        )

    def test_an_empty_population_says_nothing_to_check(self, tmp_path: Path) -> None:
        surface = self._surface(
            tmp_path, '[tool.mypy]\npackages = ["demo"]\nmypy_path = "src"\n'
        )
        part = surface.partition(("tests/t.py", "tests/u.py"))
        assert part.inside == ()
        assert part.describe() == (
            "Typed surface (src/demo): NOTHING TO CHECK -- 0 of 2 staged Python "
            "file(s) are inside it, 2 outside."
        )

    def test_an_underivable_surface_says_not_checked_with_the_reason(
        self, tmp_path: Path
    ) -> None:
        surface = self._surface(tmp_path, "[tool.mypy]\nstrict = true\n")
        part = surface.partition(("src/demo/a.py",))
        assert part.inside == ()
        assert part.describe().startswith("Typed surface: NOT CHECKED -- ")
        assert "[tool.mypy]" in part.describe()

    def test_the_three_sentences_are_distinguishable(self, tmp_path: Path) -> None:
        declared = self._surface(
            tmp_path / "a", '[tool.mypy]\npackages = ["demo"]\nmypy_path = "src"\n'
        )
        undeclared = self._surface(tmp_path / "b", "[tool.mypy]\nstrict = true\n")
        said = {
            declared.partition(("src/demo/a.py",)).describe(),
            declared.partition(("tests/t.py",)).describe(),
            undeclared.partition(("tests/t.py",)).describe(),
        }
        assert len(said) == 3


class TestThisRepositorysOwnSurface:
    """The regression `beadloom-mr2l.82` shipped: a list that stopped agreeing."""

    def test_the_derived_surface_is_the_one_ci_type_checks(self) -> None:
        surface = declared_typed_surface(REPO_ROOT)
        assert [r.path for r in surface.roots] == ["src/beadloom"]
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        checked = [
            line.split("uv run mypy", 1)[1].strip()
            for line in workflow.splitlines()
            if "uv run mypy" in line
        ]
        assert checked, "ci.yml no longer runs mypy; this surface has no CI leg"
        for target in checked:
            assert surface.roots[0].path.startswith(target.rstrip("/")), (
                f"pyproject declares {surface.roots[0].path} typed and ci.yml "
                f"checks {target}; one of the two moved without the other"
            )

    def test_the_tests_tree_is_outside_the_declared_surface(self) -> None:
        """970 errors in 90 files, and not one a violation of a declared standard."""
        surface = declared_typed_surface(REPO_ROOT)
        assert not surface.contains("tests/conftest.py")
        assert surface.contains("src/beadloom/application/typed_surface.py")


class TestTheHookTemplatesAskRatherThanList:
    """The surface is derived at the moment the hook asks, in both modes."""

    @pytest.mark.parametrize(
        ("name", "template"),
        [("warn", _HOOK_TEMPLATE_WARN), ("block", _HOOK_TEMPLATE_BLOCK)],
        ids=("warn", "block"),
    )
    def test_the_template_derives_the_surface(self, name: str, template: str) -> None:
        assert "beadloom typed-surface --filter" in template

    @pytest.mark.parametrize(
        ("name", "template"),
        [("warn", _HOOK_TEMPLATE_WARN), ("block", _HOOK_TEMPLATE_BLOCK)],
        ids=("warn", "block"),
    )
    def test_the_template_hands_mypy_only_the_filtered_paths(
        self, name: str, template: str
    ) -> None:
        assert 'echo "$typed_staged" | xargs uv run mypy 2>&1' in template
        assert 'echo "$staged_py" | xargs uv run mypy' not in template

    @pytest.mark.parametrize(
        ("name", "template"),
        [("warn", _HOOK_TEMPLATE_WARN), ("block", _HOOK_TEMPLATE_BLOCK)],
        ids=("warn", "block"),
    )
    def test_the_template_prints_what_mypy_said(self, name: str, template: str) -> None:
        assert 'echo "$mypy_out"' in template

    def test_only_the_verdict_line_differs_between_the_modes(self) -> None:
        warn = _hook_type_check(blocking=False).splitlines()
        block = _hook_type_check(blocking=True).splitlines()
        differing = [line for line in block if line not in warn]
        assert differing == [
            '        echo "Error: mypy type errors in this commit — commit blocked"',
            "        failed=1",
        ]

    def test_the_blocking_mode_blocks_and_the_warn_mode_does_not(self) -> None:
        assert "failed=1" in _hook_type_check(blocking=True)
        assert "failed=1" not in _hook_type_check(blocking=False)

    def test_a_surface_that_could_not_be_derived_never_blocks(self) -> None:
        """A check that did not happen must not turn into a refused commit."""
        block = _hook_type_check(blocking=True)
        not_checked = block[block.index("NOT CHECKED") : block.index("echo \"$typed_verdict\"")]
        assert "failed=1" not in not_checked


# ---------------------------------------------------------------------------
# The four states, through a real /bin/sh
# ---------------------------------------------------------------------------

_STUB_UV = """\
#!/bin/sh
# `uv run <tool> <paths...>`. Only `mypy` judges anything: the ruff leg shares
# this stub and must stay green, or a mypy assertion below would be passing for
# the wrong reason. A rejection is written where mypy writes it -- stdout.
#
# The ruff branch NAMES what it was handed (`uv run ruff check <paths...>`, so
# the paths start at $4). A leg narrowed by a spelling of its own is silent
# rather than wrong, and silence is the whole subject of `beadloom-0mdo.42`: a
# stub that only exits 0 lets that narrowing survive every assertion here.
if [ "$2" != "mypy" ]; then
  shift 3
  echo "ruff was handed: $*"
  exit 0
fi
shift 2
for f in "$@"; do
  case " $REJECT " in
    *" $f "*)
      echo "$f:1: error: Incompatible return value type  [return-value]"
      echo "Found 1 error in 1 file (checked $# source files)"
      exit 1
      ;;
  esac
done
echo "Success: no issues found in $# source files"
exit 0
"""

_DECLARED = '[tool.mypy]\nstrict = true\npackages = ["demo"]\nmypy_path = "src"\n'


@dataclass(frozen=True)
class HookLayout:
    """One project layout, as the facts the hook's typed leg has to answer over.

    A LAYOUT IS AN ARGUMENT, for the reason
    :class:`beadloom.application.guards.paths.PathFlavour` is one and
    ``tests/room_simulation.py`` makes a CI leg one: a property that can only be
    exercised on the shape the author happens to have is a property nobody has
    measured. `beadloom-gsal` derived the typed surface from the project's own
    declaration and left the GATE in front of that derivation spelled
    ``^(src|tests)/``, and five waves passed over it because this repository is
    src-layout and every fixture built here was too (BDL-UX #240).

    ``inside`` is what the declaration puts in the typed surface, stated per
    layout rather than computed, so a derivation that changed its mind would
    disagree with this file instead of agreeing with itself.
    """

    name: str
    pyproject: str
    tree: tuple[str, ...]
    inside: tuple[str, ...]

    @property
    def staged_python(self) -> tuple[str, ...]:
        """Every Python file the commit stages -- the population, whatever its shape."""
        return tuple(rel for rel in self.tree if rel.endswith(".py"))


#: This repository's own shape, and the only one the leg had ever been tried on.
SRC_LAYOUT = HookLayout(
    name="src-layout",
    pyproject=_DECLARED,
    tree=("src/demo/__init__.py", "src/demo/alpha.py", "tests/test_alpha.py"),
    inside=("src/demo/__init__.py", "src/demo/alpha.py"),
)

#: The flat layout: the package at the repository root, which is where a Python
#: project sits unless someone chose otherwise. The staged tests DO match the old
#: `^(src|tests)/` regex, so the leg here does not fall silent -- it speaks over
#: a population that excludes the whole package, which is the sharper half of the
#: same defect and the one a reader would never suspect.
FLAT_LAYOUT = HookLayout(
    name="flat-layout",
    pyproject='[tool.mypy]\nstrict = true\npackages = ["demo"]\n',
    tree=("demo/__init__.py", "demo/alpha.py", "tests/test_alpha.py"),
    inside=("demo/__init__.py", "demo/alpha.py"),
)

#: The same layout before anyone adds a `tests/` directory, which is the state
#: the bead reports: nothing staged matches the old regex and the leg prints no
#: line at all -- not a verdict, not NOTHING TO CHECK, not NOT CHECKED.
FLAT_LAYOUT_WITHOUT_TESTS = HookLayout(
    name="flat-layout-without-tests",
    pyproject='[tool.mypy]\nstrict = true\npackages = ["demo"]\n',
    tree=("demo/__init__.py", "demo/alpha.py"),
    inside=("demo/__init__.py", "demo/alpha.py"),
)

#: A source directory that is not called `src`. There is no list of the names a
#: project may choose, which is the argument against having one.
NAMED_SOURCE_DIR_LAYOUT = HookLayout(
    name="a-source-directory-not-called-src",
    pyproject='[tool.mypy]\nstrict = true\npackages = ["demo"]\nmypy_path = "lib"\n',
    tree=("lib/demo/__init__.py", "lib/demo/alpha.py", "tests/test_alpha.py"),
    inside=("lib/demo/__init__.py", "lib/demo/alpha.py"),
)

#: A single module at the root, declared through `files` rather than `packages` --
#: a script-shaped project, and the smallest thing that can declare a surface.
SINGLE_MODULE_LAYOUT = HookLayout(
    name="a-single-module-at-the-root",
    pyproject='[tool.mypy]\nstrict = true\nfiles = ["app.py"]\n',
    tree=("app.py", "tests/test_app.py"),
    inside=("app.py",),
)

#: A project declaring no typed surface at all, on the flat layout: the state
#: whose sentence is NOT CHECKED, and it has to be reached before it can be read.
UNDECLARED_LAYOUT = HookLayout(
    name="no-declared-surface",
    pyproject="[tool.ruff]\nline-length = 90\n",
    tree=("demo/alpha.py",),
    inside=(),
)

#: Five layouts, of which this repository can show one.
EVERY_LAYOUT = (
    SRC_LAYOUT,
    FLAT_LAYOUT,
    FLAT_LAYOUT_WITHOUT_TESTS,
    NAMED_SOURCE_DIR_LAYOUT,
    SINGLE_MODULE_LAYOUT,
)

_LAYOUT_IDS = [layout.name for layout in EVERY_LAYOUT]


def _hook_project(tmp_path: Path, layout: HookLayout) -> tuple[Path, Path]:
    """A real repository with a real hook and a stubbed toolchain on PATH."""
    project = _write(tmp_path / "proj", layout.pyproject, tree=layout.tree)
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
    for args in (("init", "-q"), ("add", "-A")):
        subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=project,
            check=True,
            capture_output=True,
        )
    return project, bindir


def _run_hook(
    project: Path,
    bindir: Path,
    template: str,
    *,
    reject: str = "",
    on_path: bool = True,
) -> subprocess.CompletedProcess[str]:
    hook = project.parent / "pre-commit"
    hook.write_text(template, encoding="utf-8")
    hook.chmod(0o755)
    env = dict(os.environ)
    env["REJECT"] = reject
    # `on_path=False` keeps git and the shell's own tools reachable and removes
    # only `beadloom`, because the state being pinned is one missing command --
    # a PATH with nothing on it would prove the hook cannot run at all.
    system = os.pathsep.join(("/usr/bin", "/bin", "/usr/sbin", "/sbin"))
    env["PATH"] = (
        f"{bindir}{os.pathsep}{env['PATH']}"
        if on_path
        else f"{bindir}{os.pathsep}{system}"
    )
    if not on_path:
        (bindir / "beadloom").unlink()
    # The codec is the HOOK's, not the image's. `text=True` leaves it to
    # `locale.getpreferredencoding(False)`, and the hook carries an em dash in
    # every blocking verdict: `tests-locale (C)` on PR #61 raised
    # `UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 288`
    # on 33 rows of this file. `_HOOK_ENCODING` is imported rather than spelled
    # so the reader cannot drift from the writer, and `errors` stays strict
    # because a mangled verdict is the failure this reader exists to catch.
    return subprocess.run(  # noqa: S603
        ["/bin/sh", str(hook)],
        cwd=project,
        capture_output=True,
        encoding=_HOOK_ENCODING,
        errors="strict",
        env=env,
        check=False,
    )


class TestWhatACommitterActuallySees:
    """Four states, and the point of the bead is that they read differently."""

    def test_a_clean_typed_commit_states_the_count_it_checked(
        self, tmp_path: Path
    ) -> None:
        project, bindir = _hook_project(tmp_path, SRC_LAYOUT)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        assert (
            "Typed surface (src/demo): 2 of 3 staged Python file(s) inside it, "
            "1 outside." in out
        )
        assert "mypy type errors" not in out

    def test_a_test_only_commit_reads_as_nothing_to_check(self, tmp_path: Path) -> None:
        project, bindir = _hook_project(tmp_path, SRC_LAYOUT)
        subprocess.run(
            ["git", "reset", "-q", "--", "src"],  # noqa: S607
            cwd=project,
            check=True,
            capture_output=True,
        )
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        assert "NOTHING TO CHECK" in out
        assert "0 of 1 staged Python file(s) are inside it" in out

    def test_a_project_declaring_no_surface_reads_as_not_checked(
        self, tmp_path: Path
    ) -> None:
        project, bindir = _hook_project(tmp_path, UNDECLARED_LAYOUT)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        assert "Typed surface: NOT CHECKED -- pyproject.toml declares no" in out

    def test_beadloom_absent_from_path_reads_as_not_checked(self, tmp_path: Path) -> None:
        project, bindir = _hook_project(tmp_path, SRC_LAYOUT)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN, on_path=False).stdout
        assert "Typed surface: NOT CHECKED -- uv or beadloom is not on PATH here" in out

    def test_a_real_error_arrives_in_mypys_own_words(self, tmp_path: Path) -> None:
        project, bindir = _hook_project(tmp_path, SRC_LAYOUT)
        result = _run_hook(
            project, bindir, _HOOK_TEMPLATE_WARN, reject="src/demo/alpha.py"
        )
        assert "src/demo/alpha.py:1: error: Incompatible return value type" in result.stdout
        assert "Warning: mypy type errors in this commit" in result.stdout
        assert result.returncode == 0, "the warn hook must not block"

    def test_the_blocking_mode_refuses_a_real_error_and_nothing_else(
        self, tmp_path: Path
    ) -> None:
        project, bindir = _hook_project(tmp_path, SRC_LAYOUT)
        clean = _run_hook(project, bindir, _HOOK_TEMPLATE_BLOCK)
        assert clean.returncode == 0, clean.stdout
        red = _run_hook(
            project, bindir, _HOOK_TEMPLATE_BLOCK, reject="src/demo/alpha.py"
        )
        assert red.returncode == 1
        assert "commit blocked" in red.stdout

    def test_a_test_file_the_checker_would_reject_is_never_handed_to_it(
        self, tmp_path: Path
    ) -> None:
        """The 970: the old block handed these over and went red on every one."""
        project, bindir = _hook_project(tmp_path, SRC_LAYOUT)
        result = _run_hook(
            project, bindir, _HOOK_TEMPLATE_BLOCK, reject="tests/test_alpha.py"
        )
        assert result.returncode == 0, result.stdout
        assert "mypy type errors" not in result.stdout


# ---------------------------------------------------------------------------
# BDL-068 S4, `beadloom-0mdo.42` (BDL-UX #240) — the gate in front of the
# derivation, over every layout rather than over this repository's
# ---------------------------------------------------------------------------


def _typed_line(out: str) -> str | None:
    """The typed leg's one line, or ``None`` when the leg said nothing at all."""
    return next((ln for ln in out.splitlines() if ln.startswith("Typed surface")), None)


class TestTheTypedLegSpeaksOnEveryLayout:
    """The leg's population is the Python a commit stages, whatever its shape.

    `beadloom-gsal` derived the typed surface from the project's own declaration
    and reached that derivation through ``grep -E '^(src|tests)/.*[.]py$'``. So a
    rule stated as a shape was gated by a rule stated as a spelling, and the
    spelling decided whether the shape ran. On the flat layout the gate admits no
    package file at all: with no ``tests/`` directory the leg prints NOTHING —
    not a verdict, not NOTHING TO CHECK, not NOT CHECKED — and with one it prints
    a confident sentence about a population the package is not in, which is the
    half a reader would never suspect.
    """

    @pytest.mark.parametrize("layout", EVERY_LAYOUT, ids=_LAYOUT_IDS)
    def test_the_leg_says_something_on_every_layout(
        self, layout: HookLayout, tmp_path: Path
    ) -> None:
        project, bindir = _hook_project(tmp_path, layout)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        assert _typed_line(out) is not None, out

    @pytest.mark.parametrize("layout", EVERY_LAYOUT, ids=_LAYOUT_IDS)
    def test_the_count_is_over_every_python_file_the_commit_stages(
        self, layout: HookLayout, tmp_path: Path
    ) -> None:
        """The denominator is the commit's Python, not the part of it under `src/`."""
        project, bindir = _hook_project(tmp_path, layout)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        line = _typed_line(out)
        assert line is not None, out
        total = len(layout.staged_python)
        outside = total - len(layout.inside)
        assert (
            f"{len(layout.inside)} of {total} staged Python file(s) inside it, "
            f"{outside} outside." in line
        ), line

    @pytest.mark.parametrize("layout", EVERY_LAYOUT, ids=_LAYOUT_IDS)
    def test_the_hook_says_what_the_derivation_says_when_asked_directly(
        self, layout: HookLayout, tmp_path: Path
    ) -> None:
        """One fact, one home: the hook renders the derivation and adds nothing.

        The comparison is against `partition().describe()` rather than against a
        string written here, so a change to the vocabulary moves both or fails.
        """
        project, bindir = _hook_project(tmp_path, layout)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        expected = declared_typed_surface(project).partition(layout.staged_python)
        assert _typed_line(out) == expected.describe(), out

    @pytest.mark.parametrize("layout", EVERY_LAYOUT, ids=_LAYOUT_IDS)
    def test_the_declared_files_reach_the_checker_on_every_layout(
        self, layout: HookLayout, tmp_path: Path
    ) -> None:
        """A rejection inside the surface reaches the committer wherever it lives."""
        project, bindir = _hook_project(tmp_path, layout)
        target = layout.inside[0]
        result = _run_hook(project, bindir, _HOOK_TEMPLATE_BLOCK, reject=target)
        assert f"{target}:1: error:" in result.stdout, result.stdout
        assert result.returncode == 1, result.stdout

    @pytest.mark.parametrize("layout", EVERY_LAYOUT, ids=_LAYOUT_IDS)
    def test_the_lint_leg_shares_the_repaired_population(
        self, layout: HookLayout, tmp_path: Path
    ) -> None:
        """`staged_py` gates ruff too, so the silence was never the typed leg's alone.

        Asserted over the files the checker was HANDED and not over the banner
        the leg prints before it: the banner is printed whatever the filter then
        admits, so a leg narrowed to nothing announces itself and checks nothing.
        A mutant reintroducing `^src/` into this leg alone survived the banner
        assertion this replaces.
        """
        project, bindir = _hook_project(tmp_path, layout)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        assert "Running ruff check on the staged Python file(s)..." in out, out
        handed = next(
            (ln for ln in out.splitlines() if ln.startswith("ruff was handed: ")), None
        )
        assert handed is not None, out
        assert set(handed.removeprefix("ruff was handed: ").split()) == set(
            layout.staged_python
        ), out

    def test_an_undeclared_surface_on_the_flat_layout_reads_as_not_checked(
        self, tmp_path: Path
    ) -> None:
        """The third state has to be REACHED before it can be read.

        `gsal` gave the leg three sentences and this one was unreachable on any
        layout the regex did not admit — a project with nothing under `src/` or
        `tests/` and no `[tool.mypy]` printed neither its verdict nor its reason.
        """
        project, bindir = _hook_project(tmp_path, UNDECLARED_LAYOUT)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        assert "Typed surface: NOT CHECKED -- pyproject.toml declares no" in out, out

    def test_a_commit_staging_no_python_stays_silent(self, tmp_path: Path) -> None:
        """The fourth population, and `gsal`'s decision about it, re-examined.

        A commit with no Python in it has no subject for either leg, and 17 of
        this branch's first 24 commits were that commit — printing a sentence
        about a check with no subject seven times in ten is noise within a day.
        The decision stands; what changes is what it now rests on. It used to
        mean "no Python under `src/` or `tests/`", which on the flat layout is a
        different statement from the one the silence was read as.
        """
        project, bindir = _hook_project(tmp_path, FLAT_LAYOUT)
        subprocess.run(
            ["git", "reset", "-q"],  # noqa: S607
            cwd=project,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "add", "pyproject.toml"],  # noqa: S607
            cwd=project,
            check=True,
            capture_output=True,
        )
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        assert _typed_line(out) is None, out
        assert "Running ruff check" not in out, out


#: The bytes the controls below feed their own reader, and the reason they are
#: SUPPLIED rather than observed. The first version of this control ran the real
#: hook and asserted that an ``ascii`` double must raise on its output. That
#: premise is a property of the room: the hook's only non-ASCII byte comes from
#: `beadloom scope-check`'s `Declared axes: NOT CHECKED \u2014 ...` line, which is
#: a Python child choosing an encoder. MEASURED on one machine, one commit, one
#: fixture -- under ``LC_ALL=C`` the child emits the raw ``e2 80 94`` (3 non-ASCII
#: bytes in 537) and the control passes; under ``LC_ALL=en_US.ISO8859-1``
#: ``console_streams.tolerate_unencodable_output`` degrades the em dash to the
#: literal text ``\u2014`` and the whole 540-byte output is ASCII, so nothing can
#: raise and the control reports DID NOT RAISE. That is BDL-061.42's own fix
#: working exactly as designed, and it is why "run the real thing and expect
#: undecodable bytes" is not an arrangement any control may rest on.
_CONTROL_TEXT = "verdict \u2014 blocked\n"

#: The same text as bytes. ``latin-1`` decodes all 256 values, so it MANGLES this
#: silently; ``ascii`` REFUSES it. One payload therefore exercises both directions
#: the two locale legs exist to separate, in every room.
_CONTROL_BYTES = _CONTROL_TEXT.encode("utf-8")


class TestTheRoomTheMatrixAboveDidNotVary:
    """The image's codec, as the second argument the matrix takes.

    ``beadloom-0mdo.42`` made the LAYOUT a substitutable input and left the ROOM
    fixed at this machine's. The reader above then decoded the hook's stdout in
    whatever codec the image chose, and that stdout carries an em dash, so
    ``tests-locale (C)`` on PR #61 raised ``UnicodeDecodeError: 'ascii' codec
    can't decode byte 0xe2 in position 288`` on 33 rows of this file. Reproduced
    byte for byte at the same position with ``LC_ALL=C PYTHONUTF8=0
    PYTHONCOERCECLOCALE=0``, and the byte was then traced rather than assumed: it
    is `beadloom scope-check`'s ``Declared axes: NOT CHECKED -- ...`` line and not
    one of the three em dashes in the template, which fire only on a rejection.
    Which of the two produced it decides whether the payload is room-dependent,
    and the controls at the foot of this class are what that distinction cost.

    The WRITER was measured before the reader was changed, because the two answers
    have different owners: ``install-hooks`` pins ``_HOOK_ENCODING`` at its own
    call site, exits 0 under that environment and writes three well-formed
    ``e2 80 94`` sequences, and the hook's own ``echo`` is ``/bin/sh`` moving those
    bytes with no encoder in the path. The defect is the reader's alone.

    The rows below are :data:`tests.ambient_codec.AMBIENT_CODECS` for the reason
    that module exists: an ambient codec cannot be arranged inside a running
    process, so it is injected. Measured red before the fix, 7 of the 15 rows,
    and the split is the point rather than the count: the BLOCKING row fails
    under both non-UTF-8 codecs, because ``ascii`` RAISES and ``latin-1`` mangles
    the em dash the assertion reads; the WARN row fails under ``ascii`` only,
    because the typed line it reads carries no em dash of its own and a mangled
    byte 200 characters away leaves it intact. So ``latin-1`` is not redundant
    with ``ascii`` here, and it is not sufficient either -- which is why the
    project runs two locale legs and not one.

    THE CONTROLS SUPPLY THEIR OWN BYTES, and that is the correction this class
    cost rather than a refinement of it: the first version ran the real hook and
    asserted an ``ascii`` double must raise on its output, which turned
    ``tests-locale (en_US.ISO-8859-1)`` red while turning ``tests-locale (C)``
    green. See :data:`_CONTROL_BYTES` for the measurement. A control that proves
    an instrument works must not read the room, or it proves the instrument works
    only where it happened to run.
    """

    @staticmethod
    def _reader_module() -> ModuleType:
        """The module whose ``subprocess`` calls are the subject: this one.

        Every other caller of ``under_ambient_codec`` names a product module
        because the reader under test lives there. Here the reader is
        :func:`_run_hook`, so the module under test is this file.
        """
        return sys.modules[__name__]

    @pytest.mark.parametrize("ambient", AMBIENT_CODECS)
    def test_the_blocking_verdict_reaches_the_committer_under_every_ambient_codec(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ambient: str
    ) -> None:
        """MEASURED before the fix: ascii -> UnicodeDecodeError, latin-1 -> mojibake."""
        project, bindir = _hook_project(tmp_path, SRC_LAYOUT)
        under_ambient_codec(monkeypatch, self._reader_module(), ambient)

        out = _run_hook(
            project, bindir, _HOOK_TEMPLATE_BLOCK, reject="src/demo/alpha.py"
        ).stdout

        assert "\u2014 commit blocked" in out, (ambient, out)

    @pytest.mark.parametrize("ambient", AMBIENT_CODECS)
    @pytest.mark.parametrize("layout", EVERY_LAYOUT, ids=_LAYOUT_IDS)
    def test_the_typed_line_is_the_same_on_every_layout_in_every_room(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: HookLayout, ambient: str
    ) -> None:
        """The layout and the room are two axes, and the verdict crosses both."""
        project, bindir = _hook_project(tmp_path, layout)
        under_ambient_codec(monkeypatch, self._reader_module(), ambient)

        line = _typed_line(_run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout)

        assert line is not None, (layout.name, ambient)
        assert f"{len(layout.staged_python)} staged Python file(s)" in line

    @staticmethod
    def _emitting(tmp_path: Path, payload: bytes) -> list[str]:
        """A child that writes exactly *payload* and consults no locale to do it.

        ``write_bytes`` states no codec because it has none to state, and ``cat``
        moves bytes. So the control's premise -- what this reader is handed -- is
        an argument, in the shape :class:`HookLayout` gives the layout.
        """
        target = tmp_path / "payload"
        target.write_bytes(payload)
        return ["/bin/cat", str(target)]

    @pytest.mark.parametrize(
        ("ambient", "expected"),
        [
            ("utf-8", _CONTROL_TEXT),
            ("latin-1", _CONTROL_BYTES.decode("latin-1")),
        ],
        ids=("utf-8-reads-it", "latin-1-mangles-it"),
    )
    def test_an_unstated_reader_takes_whatever_codec_the_double_supplies(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ambient: str, expected: str
    ) -> None:
        """Control, direction one: the double really decides, and it can mangle."""
        assert _CONTROL_BYTES.decode("latin-1") != _CONTROL_TEXT, (
            "the payload no longer distinguishes the codecs, so the row below "
            "would pass whatever the double did"
        )
        under_ambient_codec(monkeypatch, self._reader_module(), ambient)

        out = subprocess.run(  # noqa: S603
            self._emitting(tmp_path, _CONTROL_BYTES),
            capture_output=True,
            # The defect itself, held down as a control. Ruff cannot flag it:
            # `PLW1514` is selected in this project and reports a `noqa` here as
            # UNUSED, which is the measurement behind the cost on this bead.
            text=True,
            check=False,
        ).stdout

        assert out == expected, (ambient, out)

    def test_an_unstated_reader_is_refused_by_an_ascii_double(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Control, direction two: the codec that RAISES rather than mangles."""
        under_ambient_codec(monkeypatch, self._reader_module(), "ascii")

        with pytest.raises(UnicodeDecodeError):
            subprocess.run(  # noqa: S603
                self._emitting(tmp_path, _CONTROL_BYTES),
                capture_output=True,
                text=True,
                check=False,
            )

    @pytest.mark.parametrize("ambient", AMBIENT_CODECS)
    def test_a_reader_that_states_its_codec_is_unmoved_by_any_double(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ambient: str
    ) -> None:
        """And the control's other half: stating the codec is what the fix DID.

        Without this row the three above would be consistent with a double that
        ignores ``encoding=``, which is the one behaviour that would make the two
        matrix rows pass for a reason that has nothing to do with the repair.
        """
        under_ambient_codec(monkeypatch, self._reader_module(), ambient)

        out = subprocess.run(  # noqa: S603
            self._emitting(tmp_path, _CONTROL_BYTES),
            capture_output=True,
            encoding="utf-8",
            errors="strict",
            check=False,
        ).stdout

        assert out == _CONTROL_TEXT, (ambient, out)


class TestNoLegNamesADirectory:
    """The template states which KIND of file it stages, never where code lives.

    A path filter naming directories is a second list beside the declaration, and
    a second list is a second thing to forget — the argument `beadloom-gsal` made
    about the surface, applied to the gate that reaches it.
    """

    @staticmethod
    def _staged_py_pattern(template: str) -> str:
        """The regex `staged_py` selects with, taken out of the shell quoting."""
        line = next(ln for ln in template.splitlines() if ln.startswith("staged_py="))
        quoted = re.search(r"grep -E '(?P<pattern>[^']*)'", line)
        assert quoted is not None, line
        return quoted.group("pattern")

    @pytest.mark.parametrize(
        ("name", "template"),
        [("warn", _HOOK_TEMPLATE_WARN), ("block", _HOOK_TEMPLATE_BLOCK)],
        ids=("warn", "block"),
    )
    def test_the_population_is_selected_by_suffix_and_not_by_directory(
        self, name: str, template: str
    ) -> None:
        pattern = self._staged_py_pattern(template)
        assert "/" not in pattern, f"{name}: the gate still names a directory: {pattern}"

    @pytest.mark.parametrize(
        ("name", "template"),
        [("warn", _HOOK_TEMPLATE_WARN), ("block", _HOOK_TEMPLATE_BLOCK)],
        ids=("warn", "block"),
    )
    def test_the_pattern_still_selects_python(self, name: str, template: str) -> None:
        """The control: a filter selecting everything would pass the test above."""
        pattern = self._staged_py_pattern(template)
        assert re.search(pattern, "demo/alpha.py"), name
        assert not re.search(pattern, "docs/guide.md"), name


# ---------------------------------------------------------------------------
# The command, and the population the decision was taken over
# ---------------------------------------------------------------------------


class TestTheCommandsContract:
    """`--filter` is what the hook consumes; the codes are what a caller reads."""

    def _run(self, project: Path, args: list[str], stdin: str = "") -> Result:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        return CliRunner().invoke(
            main, ["typed-surface", "--project", str(project), *args], input=stdin
        )

    def test_a_derived_surface_exits_zero(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\n',
            tree=("demo/__init__.py",),
        )
        result = self._run(project, [])
        assert result.exit_code == 0
        assert "Covered (1):" in result.output
        assert "demo    [tool.mypy] packages = 'demo'" in result.output

    def test_an_underivable_surface_exits_two_and_says_so(self, tmp_path: Path) -> None:
        project = _write(tmp_path / "p", "[tool.ruff]\nline-length = 90\n")
        result = self._run(project, [])
        assert result.exit_code == 2
        assert "NOT DECLARED:" in result.output
        assert "is not checked. It is not clean." in result.output

    def test_the_human_report_names_what_it_could_not_resolve(
        self, tmp_path: Path
    ) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo", "ghost"]\n',
            tree=("demo/__init__.py",),
        )
        result = self._run(project, [])
        assert "Unresolved (1):" in result.output
        assert "[tool.mypy] packages = 'ghost'" in result.output

    def test_the_json_payload_carries_both_halves(self, tmp_path: Path) -> None:
        import json

        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo", "ghost"]\n',
            tree=("demo/__init__.py",),
        )
        payload = json.loads(self._run(project, ["--json"]).stdout)
        assert payload["declared"] is True
        assert payload["roots"] == [
            {"path": "demo", "source": "[tool.mypy] packages = 'demo'"}
        ]
        assert payload["unresolved"][0]["source"] == "[tool.mypy] packages = 'ghost'"

    def test_the_filter_leads_with_the_marker_scope_check_uses(
        self, tmp_path: Path
    ) -> None:
        from beadloom.application.declared_scope import VERDICT_MARKER

        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\n',
            tree=("demo/__init__.py",),
        )
        output = self._run(
            project, ["--filter"], stdin="demo/a.py\ntests/t.py\n"
        ).output.splitlines()
        assert output[0].startswith(VERDICT_MARKER)
        assert output[1:] == ["demo/a.py"]

    def test_no_reported_path_can_begin_with_the_marker(self, tmp_path: Path) -> None:
        """The hook splits verdict from payload on a shape, not on an agreement."""
        from beadloom.application.declared_scope import VERDICT_MARKER

        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\n',
            tree=("demo/__init__.py",),
        )
        payload = self._run(
            project, ["--filter"], stdin="demo/a.py\ndemo/b.py\n"
        ).output.splitlines()[1:]
        assert payload and not any(p.startswith(VERDICT_MARKER) for p in payload)

    def test_a_blank_line_on_stdin_is_not_a_staged_path(self, tmp_path: Path) -> None:
        project = _write(
            tmp_path / "p",
            '[tool.mypy]\npackages = ["demo"]\n',
            tree=("demo/__init__.py",),
        )
        verdict = self._run(
            project, ["--filter"], stdin="demo/a.py\n\n  \n"
        ).output.splitlines()[0]
        assert "1 of 1 staged Python file(s)" in verdict


#: The commits of `features/BDL-068` that staged Python at all, with the two
#: counts the warn/block decision was taken over: paths matching the filter the
#: hook carried AT THE TIME, `^(src|tests)/.*\.py$`, and how many of those are
#: inside the surface `pyproject` declares. MEASURED at `b7c9476..49c2ebe`, each
#: commit against its own tree in a linked worktree. `beadloom-0mdo.42` has since
#: replaced that filter, and the counts below are deliberately still taken with
#: it: they record the population a past decision was taken over, and rewriting
#: them to today's filter would restate the decision as one nobody made.
#:
#: The mypy half of that measurement is NOT re-run here and is deliberately not:
#: it takes 24 checkouts and 31 type-check runs. It is recorded instead --
#: the old block warned on 4 of these 7 and all 4 warnings were false; a
#: surface-scoped check is clean on all 7. What the test holds is the
#: POPULATION, so a decision taken over these seven commits cannot quietly come
#: to be about a different seven.
_MEASURED_COMMITS = {
    "9d73c995f343e49f82005c863602b632ffe447e2": (6, 3),
    "5fd96360d91026e495a44465012d90a66087da6c": (16, 8),
    "a1988326be8ced470090472641644ccc0f72e35d": (6, 4),
    "a5bf5aeda823b9247c384e1b10adfb5927099dfb": (12, 5),
    "4fce7d29d00912fdc5ed3008aa7b9497b39eef72": (7, 2),
    "204fc95846f08b6f7f70ff9919a6c495c2c88507": (2, 1),
    "ded748d18a83fc9305edc30d29147622ce179825": (14, 8),
}


class TestThePopulationTheDecisionWasTakenOver:
    """Seven real commits, and how much of each the old block judged.

    Skipped where the history is not reachable -- a clean room built with
    ``git archive`` has no ``.git``, and a measurement that cannot be made is
    reported as not made rather than as passing.
    """

    @staticmethod
    def _staged(commit: str) -> list[str] | None:
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "git",
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "--diff-filter=ACMR",
                commit,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            # git writes path names as bytes; UTF-8 is what it produces for a
            # non-ASCII one, and leaving the codec to the image is the same
            # defect `_run_hook` above carries a comment about.
            encoding="utf-8",
            errors="strict",
            check=False,
        )
        if result.returncode != 0:
            return None
        pattern = re.compile(r"^(src|tests)/.*\.py$")
        return [p for p in result.stdout.splitlines() if pattern.match(p)]

    @pytest.mark.parametrize("commit", sorted(_MEASURED_COMMITS))
    def test_each_commits_two_counts_are_the_ones_measured(self, commit: str) -> None:
        staged = self._staged(commit)
        if staged is None:
            pytest.skip(f"{commit[:8]} is not reachable from here")
        surface = declared_typed_surface(REPO_ROOT)
        inside = [p for p in staged if surface.contains(p)]
        assert (len(staged), len(inside)) == _MEASURED_COMMITS[commit]

    def test_the_old_block_judged_more_than_half_of_what_it_was_handed_wrongly(
        self,
    ) -> None:
        """Across the seven: 63 paths handed to mypy, 31 of them declared typed."""
        totals = [self._staged(c) for c in _MEASURED_COMMITS]
        if any(t is None for t in totals):
            pytest.skip("the branch history is not reachable from here")
        surface = declared_typed_surface(REPO_ROOT)
        staged = [p for t in totals if t is not None for p in t]
        inside = [p for p in staged if surface.contains(p)]
        assert (len(staged), len(inside)) == (63, 31)
