"""BDL-074 B1 — every test finds the repository root through one helper.

Ninety-seven files used to count their own parents to reach the root
(``Path(__file__).resolve().parents[3]``), so a file moved one folder deeper
read the wrong directory. :mod:`tests.support.repository_root` walks up to the
nearest ``pyproject.toml`` instead, which holds at any depth and in each of the
three rooms the suite runs in: the checkout, a clean room (a copy with no
``.git``) and mutmut's ``mutants/`` copy, which carries its own
``pyproject.toml`` inside the checkout.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.repository_root import (
    REPO_ROOT,
    TESTS_ROOT,
    RepositoryRootNotFoundError,
    repository_root,
)


class TestTheRootIsFoundFromAnyDepth:
    def test_a_file_nested_at_any_depth_finds_the_same_root(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        deep = tmp_path / "tests" / "unit" / "graph" / "rules" / "test_x.py"
        shallow = tmp_path / "tests" / "test_x.py"

        assert repository_root(deep) == tmp_path
        assert repository_root(shallow) == tmp_path

    def test_the_nearest_manifest_wins(self, tmp_path: Path) -> None:
        """mutmut's copy sits inside the checkout and carries a manifest of its own."""
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        copy = tmp_path / "mutants"
        copy.mkdir()
        (copy / "pyproject.toml").write_text("", encoding="utf-8")

        assert repository_root(copy / "tests" / "support" / "repository_root.py") == copy

    def test_a_directory_named_like_the_manifest_is_not_one(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "tests" / "pyproject.toml").mkdir(parents=True)

        assert repository_root(tmp_path / "tests" / "test_x.py") == tmp_path

    def test_no_manifest_above_is_an_error_that_names_where_it_looked(
        self, tmp_path: Path
    ) -> None:
        start = tmp_path / "nowhere" / "test_x.py"

        with pytest.raises(RepositoryRootNotFoundError, match="nowhere"):
            repository_root(start, stop_at=tmp_path)


class TestThisSuitesRoot:
    def test_the_root_holds_the_manifest_the_suite_and_the_package(self) -> None:
        assert (REPO_ROOT / "pyproject.toml").is_file()
        assert (REPO_ROOT / "src" / "beadloom" / "__init__.py").is_file()
        assert Path(__file__).resolve().is_relative_to(REPO_ROOT)

    def test_the_tests_root_is_the_suite_under_the_repository_root(self) -> None:
        assert TESTS_ROOT == REPO_ROOT / "tests"
        assert (TESTS_ROOT / "conftest.py").is_file()
