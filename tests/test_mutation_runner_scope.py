"""The runner's scope and the declared scope are the same scope (BDL-068 S3.1).

The mutation scope is stated twice in this repository and has to be, because the
two readers are different programs: `.beadloom/flow.yml` carries
`mutation.targets`, which is what SHIPS and what `config-check` reads, and
`[tool.mutmut]` in pyproject.toml is what the runner reads. Two authored homes
are two things that can disagree, which is the class BDL-068 exists to remove —
so the agreement is a test rather than a convention.

The runner itself is never imported here. `mutmut` is this repository's own dev
dependency and an adopter needs none: what these tests read is configuration.
"""

from __future__ import annotations

import ast
import sys
from fnmatch import fnmatch
from pathlib import Path

import yaml

# The reader is selected on the VERSION and not by catching an ImportError, so
# mypy analyses exactly one branch per `--python-version` (BDL-UX #227: a
# `type: ignore` needed on 3.10 is an unused-ignore error on 3.11+, and a
# try/except form is both at once). 3.10 has no `tomllib`; pytest requires
# `tomli` there, so the else branch resolves on every leg that runs this file.
if sys.version_info >= (3, 11):
    from tomllib import loads as _toml_loads
else:
    from tomli import loads as _toml_loads


def toml_loads(text: str) -> dict[str, object]:
    """The TOML reader, with a stated return type at the untyped boundary."""
    data = _toml_loads(text)
    assert isinstance(data, dict)
    return data

REPO_ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict[str, object]:
    return toml_loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _mutmut_config() -> dict[str, object]:
    tool = _pyproject()["tool"]
    assert isinstance(tool, dict)
    config = tool["mutmut"]
    assert isinstance(config, dict)
    return config


def _declared_targets() -> list[str]:
    flow = yaml.safe_load((REPO_ROOT / ".beadloom" / "flow.yml").read_text(encoding="utf-8"))
    targets = flow["mutation"]["targets"]
    assert isinstance(targets, list)
    return [str(target) for target in targets]


def _target_sources(target: str) -> list[Path]:
    """The Python files a declared target resolves to, as the runner walks them."""
    path = REPO_ROOT / target
    return sorted(path.rglob("*.py")) if path.is_dir() else [path]


def _mutated_paths() -> list[str]:
    """The paths `only_mutate` selects, with the glob suffix removed."""
    patterns = _mutmut_config()["only_mutate"]
    assert isinstance(patterns, list)
    return [str(pattern).removesuffix("*") for pattern in patterns]


class TestTheTwoHomesAgree:
    def test_every_path_the_runner_mutates_is_a_declared_target(self) -> None:
        declared = {target.rstrip("/") for target in _declared_targets()}
        for path in _mutated_paths():
            assert path.rstrip("/") in declared, (
                f"{path} is mutated by the runner and declared nowhere in "
                f"`mutation.targets`, so what ships describes a scope the run "
                f"does not have"
            )

    def test_the_paths_the_runner_mutates_are_on_disk(self) -> None:
        """A `only_mutate` pattern matching nothing runs zero mutants — the exact
        failure `mutation-zero-mutants` exists to report, one config file over."""
        for path in _mutated_paths():
            assert (REPO_ROOT / path).exists(), path

    def test_every_declared_target_is_mutated_by_the_runner(self) -> None:
        """The direction the other test cannot see, and the one that went wrong.

        `only_mutate` names a subset of `mutation.targets`, so the check above
        passes while a declared target is reached by no run of this project's
        job at all — not "awaiting a run", unreachable by configuration. That is
        the phantom gate BDL-068 exists to remove, sitting in the epic's own
        declaration: measured 2026-09-04, `doc_quality.py` and `doc_shape.py`
        had been declared since S3 and `only_mutate` named `graph/rules/` alone.
        """
        patterns = _mutmut_config()["only_mutate"]
        assert isinstance(patterns, list)
        unreachable = [
            str(path.relative_to(REPO_ROOT))
            for target in _declared_targets()
            for path in _target_sources(target)
            if not any(fnmatch(str(path.relative_to(REPO_ROOT)), str(p)) for p in patterns)
        ]
        assert unreachable == [], (
            f"{len(unreachable)} declared source file(s) match no `only_mutate` "
            f"pattern, so no run of this project's job can mutate them and the "
            f"shipped declaration names a scope nothing measures: {unreachable}"
        )

    def test_the_mutated_paths_lie_under_a_source_path_the_runner_copies(self) -> None:
        """mutmut mutates a copy under `mutants/`; a path outside `source_paths`
        is never copied, so it is never mutated however it is spelled."""
        sources = _mutmut_config()["source_paths"]
        assert isinstance(sources, list)
        roots = [str(source).rstrip("/") for source in sources]
        for path in _mutated_paths():
            assert any(path.rstrip("/").startswith(root) for root in roots), (path, roots)


class TestTheRunnerIsThisRepositorysOwn:
    """Tool-agnosticism, as a property of the dependency graph rather than a claim."""

    def test_the_runner_is_declared_in_its_own_extra(self) -> None:
        project = _pyproject()["project"]
        assert isinstance(project, dict)
        extras = project["optional-dependencies"]
        assert isinstance(extras, dict)
        assert any("mutmut" in requirement for requirement in extras["mutation"])

    def test_no_normal_install_pulls_the_runner_in(self) -> None:
        """`dev` and `all` are what CI legs and contributors install. A runner on
        that path is a runner an adopter is asked to own."""
        project = _pyproject()["project"]
        assert isinstance(project, dict)
        extras = project["optional-dependencies"]
        assert isinstance(extras, dict)
        for extra in ("dev", "all"):
            assert not any("mutmut" in requirement for requirement in extras[extra]), extra
        assert not any("mutmut" in requirement for requirement in project["dependencies"])

    def test_nothing_shipped_imports_the_runner(self) -> None:
        """The product reads counter NAMES, so no module under src/ names the tool."""
        offenders = [
            path.relative_to(REPO_ROOT)
            for path in (REPO_ROOT / "src").rglob("*.py")
            if "import mutmut" in path.read_text(encoding="utf-8")
        ]
        assert offenders == []

class TestThePoolTheRunnerSelectsFrom:
    """The 114 test files that execute the declared scope, and what keeps the
    list honest.

    mutmut needs its pool statically, so the list is authored — the shape this
    epic distrusts. Two facts are therefore checked rather than hoped for: no
    entry names a file that has since moved, and no test importing the rules
    package directly sits outside the pool. Neither catches a killer that
    reaches the slice through `beadloom lint`, and that gap has a known
    direction: a killer outside the pool leaves its mutant alive, so the score
    under-claims.
    """

    def test_every_pool_entry_is_a_test_file_that_exists(self) -> None:
        for entry in _pool():
            assert (REPO_ROOT / entry).is_file(), (
                f"{entry} is in the mutation pool and not on disk — mutmut would "
                f"select nothing for the mutants it was meant to kill"
            )

    def test_no_test_importing_the_rules_package_sits_outside_the_pool(self) -> None:
        """The lower bound the pool can be checked against without coverage.

        The population is read from each file's IMPORT statements rather than
        from its text: a check spelled as a substring match matches its own
        source and reports itself, which this one did on the first run.
        """
        pool = set(_pool())
        importers = {
            str(path.relative_to(REPO_ROOT))
            for path in (REPO_ROOT / "tests").rglob("test_*.py")
            if _imports_the_rules_package(path)
        }
        assert importers <= pool, sorted(importers - pool)

    def test_the_pool_is_not_empty(self) -> None:
        """An empty pool selects the whole suite, which does not run in the copied
        room — the run would abort at stats rather than report a smaller score."""
        assert len(_pool()) > 1


def _imports_the_rules_package(path: Path) -> bool:
    """Whether *path* imports `beadloom.graph.rules`, by its import statements."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - a test file that does not parse
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "beadloom.graph.rules"
        ):
            return True
        if isinstance(node, ast.Import) and any(
            alias.name.startswith("beadloom.graph.rules") for alias in node.names
        ):
            return True
    return False


def _pool() -> list[str]:
    entries = _mutmut_config()["pytest_add_cli_args_test_selection"]
    assert isinstance(entries, list)
    return [str(entry) for entry in entries]
