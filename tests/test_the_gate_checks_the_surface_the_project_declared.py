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
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.application.typed_surface import TypedSurface, declared_typed_surface
from beadloom.services.commands.docsync import (
    _HOOK_TEMPLATE_BLOCK,
    _HOOK_TEMPLATE_WARN,
    _hook_type_check,
)

if TYPE_CHECKING:
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
    )
    def test_the_template_derives_the_surface(self, name: str, template: str) -> None:
        assert "beadloom typed-surface --filter" in template

    @pytest.mark.parametrize(
        ("name", "template"),
        [("warn", _HOOK_TEMPLATE_WARN), ("block", _HOOK_TEMPLATE_BLOCK)],
    )
    def test_the_template_hands_mypy_only_the_filtered_paths(
        self, name: str, template: str
    ) -> None:
        assert 'echo "$typed_staged" | xargs uv run mypy 2>&1' in template
        assert 'echo "$staged_py" | xargs uv run mypy' not in template

    @pytest.mark.parametrize(
        ("name", "template"),
        [("warn", _HOOK_TEMPLATE_WARN), ("block", _HOOK_TEMPLATE_BLOCK)],
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
if [ "$2" != "mypy" ]; then
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


def _hook_project(tmp_path: Path, pyproject: str) -> tuple[Path, Path]:
    """A real repository with a real hook and a stubbed toolchain on PATH."""
    project = _write(
        tmp_path / "proj",
        pyproject,
        tree=("src/demo/__init__.py", "src/demo/alpha.py", "tests/test_alpha.py"),
    )
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
    return subprocess.run(  # noqa: S603
        ["/bin/sh", str(hook)],
        cwd=project,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class TestWhatACommitterActuallySees:
    """Four states, and the point of the bead is that they read differently."""

    def test_a_clean_typed_commit_states_the_count_it_checked(
        self, tmp_path: Path
    ) -> None:
        project, bindir = _hook_project(tmp_path, _DECLARED)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        assert (
            "Typed surface (src/demo): 2 of 3 staged Python file(s) inside it, "
            "1 outside." in out
        )
        assert "mypy type errors" not in out

    def test_a_test_only_commit_reads_as_nothing_to_check(self, tmp_path: Path) -> None:
        project, bindir = _hook_project(tmp_path, _DECLARED)
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
        project, bindir = _hook_project(tmp_path, "[tool.ruff]\nline-length = 90\n")
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN).stdout
        assert "Typed surface: NOT CHECKED -- pyproject.toml declares no" in out

    def test_beadloom_absent_from_path_reads_as_not_checked(self, tmp_path: Path) -> None:
        project, bindir = _hook_project(tmp_path, _DECLARED)
        out = _run_hook(project, bindir, _HOOK_TEMPLATE_WARN, on_path=False).stdout
        assert "Typed surface: NOT CHECKED -- uv or beadloom is not on PATH here" in out

    def test_a_real_error_arrives_in_mypys_own_words(self, tmp_path: Path) -> None:
        project, bindir = _hook_project(tmp_path, _DECLARED)
        result = _run_hook(
            project, bindir, _HOOK_TEMPLATE_WARN, reject="src/demo/alpha.py"
        )
        assert "src/demo/alpha.py:1: error: Incompatible return value type" in result.stdout
        assert "Warning: mypy type errors in this commit" in result.stdout
        assert result.returncode == 0, "the warn hook must not block"

    def test_the_blocking_mode_refuses_a_real_error_and_nothing_else(
        self, tmp_path: Path
    ) -> None:
        project, bindir = _hook_project(tmp_path, _DECLARED)
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
        project, bindir = _hook_project(tmp_path, _DECLARED)
        result = _run_hook(
            project, bindir, _HOOK_TEMPLATE_BLOCK, reject="tests/test_alpha.py"
        )
        assert result.returncode == 0, result.stdout
        assert "mypy type errors" not in result.stdout


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
#: counts the warn/block decision was taken over: paths matching the hook's
#: `^(src|tests)/.*\.py$` filter, and how many of those are inside the surface
#: `pyproject` declares. MEASURED at `b7c9476..49c2ebe`, each commit against its
#: own tree in a linked worktree.
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
        import re

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
            text=True,
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
