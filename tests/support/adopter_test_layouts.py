"""Three adopter projects whose tests are not `tests/**/test_*.py` (BDL-074 G2).

Review ``beadloom-b9ll`` M3 reproduced the regression on a two-package Go module
and named two Python layouts beside it: tests kept in ``test/`` and tests kept
beside the code. Each builder writes one of them under a directory the caller
owns and returns its root; the reindex, ``ctx`` and the debt report are then run
against it by the test that asked. The Go module is the reviewer's, file for file
(``goproj`` in the review's scratchpad), less the files ``beadloom init`` wrote.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

_GO_TEST = (
    "package {package}\n\n"
    'import "testing"\n\n'
    'func TestTotal(t *testing.T) {{ if Total(1, 2) != 3 {{ t.Fatal("bad") }} }}\n'
)
_GO_CODE = "package {package}\n\nfunc Total(a, b int) int {{ return a + b }}\n"

_PY_CODE = "def total(a: int, b: int) -> int:\n    return a + b\n"
_PY_TEST = (
    "from shop.{package}.{package} import total\n\n\n"
    "def test_total() -> None:\n    assert total(1, 2) == 3\n\n\n"
    "def test_zero() -> None:\n    assert total(0, 0) == 0\n"
)

#: The two packages every project here holds, each with a node of its own.
PACKAGES = ("billing", "orders")


def write(root: Path, relative: str, text: str) -> None:
    """Write *text* at *relative* under *root*, creating its folders."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _graph(root: Path, sources: dict[str, str]) -> None:
    nodes: list[dict[str, object]] = [
        {"ref_id": "shop", "kind": "service", "summary": "Root: shop", "source": ""}
    ]
    edges: list[dict[str, str]] = []
    for ref_id, source in sources.items():
        nodes.append({"ref_id": ref_id, "kind": "domain", "summary": ref_id, "source": source})
        edges.append({"src": ref_id, "dst": "shop", "kind": "part_of"})
    graph = {"nodes": nodes, "edges": edges}
    write(root, ".beadloom/_graph/services.yml", yaml.safe_dump(graph, sort_keys=False))


def _config(root: Path, *, language: str, scan_path: str, tests: object = None) -> None:
    config: dict[str, object] = {"languages": [language], "scan_paths": [scan_path]}
    if tests is not None:
        config["tests"] = tests
    write(root, ".beadloom/config.yml", yaml.safe_dump(config, sort_keys=False))


def go_module(root: Path) -> Path:
    """The reviewer's Go module: two packages, each with one test beside its code."""
    write(root, "go.mod", "module example.com/shop\n\ngo 1.22\n")
    for package in PACKAGES:
        write(root, f"internal/{package}/{package}.go", _GO_CODE.format(package=package))
        write(root, f"internal/{package}/{package}_test.go", _GO_TEST.format(package=package))
    _config(root, language=".go", scan_path="internal")
    _graph(root, {package: f"internal/{package}/" for package in PACKAGES})
    return root


def _python_code(root: Path) -> None:
    write(root, "pyproject.toml", '[project]\nname = "shop"\nversion = "0.1.0"\n')
    write(root, "src/shop/__init__.py", "")
    for package in PACKAGES:
        write(root, f"src/shop/{package}/__init__.py", "")
        write(root, f"src/shop/{package}/{package}.py", _PY_CODE)
    _graph(root, {package: f"src/shop/{package}/" for package in PACKAGES})


def python_with_a_test_root(root: Path, *, mirrored: bool) -> Path:
    """A Python project whose tests live in `test/`, declared as its test root.

    *mirrored* lays them out as ``test/unit/<package>/test_<package>.py``; otherwise
    they sit flat in ``test/``, which binds them to nothing.
    """
    _python_code(root)
    for package in PACKAGES:
        folder = f"test/unit/{package}/" if mirrored else "test/"
        write(root, f"{folder}test_{package}.py", _PY_TEST.format(package=package))
    _config(root, language=".py", scan_path="src", tests={"roots": ["test"]})
    return root


def python_beside_the_code(root: Path) -> Path:
    """A Python project whose tests sit beside the modules they test."""
    _python_code(root)
    for package in PACKAGES:
        write(root, f"src/shop/{package}/test_{package}.py", _PY_TEST.format(package=package))
    _config(root, language=".py", scan_path="src")
    return root
