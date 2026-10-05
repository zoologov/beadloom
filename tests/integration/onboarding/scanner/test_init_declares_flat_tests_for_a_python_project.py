"""Init declares ``flat_tests`` in the test layout of a Python project (BDL-078 ``beadloom-76mk``).

Observed by BDL-076 ``beadloom-ujzb.17``: on the Python adopter fixture every test
directly under ``tests/`` bound to no node after ``init``, because nothing laid
them out where the mirror reads. The binding of a flat Python test by its name and
its imports is something a project declares, so ``init`` declares it — for a
project whose code is Python, and for no other, so a Go, JVM or Swift project's
config is the one it wrote before.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.onboarding.scanner.bootstrap import bootstrap_project

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _config(root: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (root / ".beadloom" / "config.yml").read_text(encoding="utf-8")
    )
    return loaded


def test_a_python_project_is_given_flat_tests(tmp_path: Path) -> None:
    _write(tmp_path, "src/shop/__init__.py", "")
    _write(tmp_path, "src/shop/billing/__init__.py", "")
    _write(tmp_path, "src/shop/billing/invoice.py", "def total() -> int:\n    return 0\n")
    bootstrap_project(tmp_path)
    assert _config(tmp_path)["tests"] == {"flat_tests": True}


def test_a_go_project_is_not_given_a_tests_block(tmp_path: Path) -> None:
    _write(tmp_path, "go.mod", "module example.com/shop\n\ngo 1.22\n")
    _write(
        tmp_path,
        "internal/billing/billing.go",
        "package billing\n\nfunc Total() int { return 0 }\n",
    )
    bootstrap_project(tmp_path)
    assert "tests" not in _config(tmp_path)


def test_a_python_project_with_a_jvm_tree_keeps_its_mirrors_beside_flat_tests(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "tools/release/__init__.py", "")
    _write(tmp_path, "tools/release/run.py", "def main() -> None:\n    pass\n")
    _write(tmp_path, "pom.xml", "<project><artifactId>ledger</artifactId></project>\n")
    _write(
        tmp_path,
        "src/main/java/org/example/ledger/Ledger.java",
        "package org.example.ledger;\n\npublic class Ledger {}\n",
    )
    _write(
        tmp_path,
        "src/test/java/org/example/ledger/LedgerTest.java",
        "package org.example.ledger;\n\npublic class LedgerTest {}\n",
    )
    bootstrap_project(tmp_path)
    tests = _config(tmp_path)["tests"]
    assert tests["flat_tests"] is True
    assert "mirrors" in tests
