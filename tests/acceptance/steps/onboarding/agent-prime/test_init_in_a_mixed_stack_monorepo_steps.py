"""Step implementations for `onboarding/agent-prime/init_in_a_mixed_stack_monorepo.feature`.

BDL-076 R2 finding 2, fixed by `beadloom-ujzb.19`. The real `beadloom init --yes` and
`beadloom reindex` run through the CLI on two monorepos written to disk, each with one
service the slice-2 layout readers know (a Maven module, a Swift package) and one
service beside it in the same top-level folder that they do not (Python, TypeScript).
What init writes is read back from its YAML; what reindex derives, from the index.

**FAKES PROVE FAKES.** The JVM and Swift services each hold an import between two of
their own packages or targets, and the Python service one between its own two
packages, so an edge that appears proves the importing service was scanned.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_java")
pytest.importorskip("tree_sitter_swift")
pytest.importorskip("tree_sitter_typescript")

scenarios("../../../onboarding/agent-prime/init_in_a_mixed_stack_monorepo.feature")

_BILLING = "services/billing/src/main/java/org/acme/billing"

_JVM_AND_PYTHON: dict[str, str] = {
    "services/billing/pom.xml": "<project><artifactId>billing</artifactId></project>\n",
    f"{_BILLING}/api/Invoices.java": (
        "package org.acme.billing.api;\n\n"
        "import org.acme.billing.core.Ledger;\n\n"
        "public class Invoices { Ledger ledger; }\n"
    ),
    f"{_BILLING}/core/Ledger.java": "package org.acme.billing.core;\n\npublic class Ledger {}\n",
    "services/billing/src/test/java/org/acme/billing/core/LedgerTest.java": (
        "package org.acme.billing.core;\n\nclass LedgerTest {}\n"
    ),
    "services/notify/pyproject.toml": '[project]\nname = "notify"\n',
    "services/notify/notify/__init__.py": (
        "from sender import mail\n\n\ndef notify() -> int:\n    return mail.send()\n"
    ),
    "services/notify/sender/__init__.py": "",
    "services/notify/sender/mail.py": "def send() -> int:\n    return 1\n",
}

_SWIFT_AND_TYPESCRIPT: dict[str, str] = {
    "apps/ios/Package.swift": (
        "// swift-tools-version:5.9\n"
        "import PackageDescription\n\n"
        "let package = Package(\n"
        '    name: "Ios",\n'
        "    targets: [\n"
        '        .executableTarget(name: "App", dependencies: ["Core"]),\n'
        '        .target(name: "Core"),\n'
        "    ]\n"
        ")\n"
    ),
    "apps/ios/Sources/App/main.swift": "import Core\nimport SwiftUI\n\nprint(Core.version)\n",
    "apps/ios/Sources/Core/Core.swift": 'public let version = "1"\n',
    "apps/web/package.json": '{"name": "web", "version": "1.0.0"}\n',
    "apps/web/src/api/index.ts": 'import { f } from "../util/f";\n\nexport const a = f();\n',
    "apps/web/src/util/f.ts": "export function f(): number {\n  return 1;\n}\n",
}


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _write(root: Path, files: dict[str, str]) -> None:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


@given('a monorepo with a Maven service "services/billing" and a Python service "services/notify"')
def _jvm_and_python(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = tmp_path / "poly"
    _write(state["root"], _JVM_AND_PYTHON)


@given('a monorepo with a Swift package "apps/ios" and a TypeScript app "apps/web"')
def _swift_and_typescript(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = tmp_path / "swmono"
    _write(state["root"], _SWIFT_AND_TYPESCRIPT)


def _run(state: dict[str, Any], *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(state["root"])])
    assert result.exit_code == 0, result.output


@when("beadloom init is run without prompts")
def _init(state: dict[str, Any]) -> None:
    _run(state, "init", "--yes")


@when("beadloom reindex is run")
def _reindex(state: dict[str, Any]) -> None:
    _run(state, "reindex")


def _listed(text: str) -> set[str]:
    return {part.strip().strip('"') for part in text.split(",")}


def _pairs(text: str) -> set[tuple[str, str]]:
    return {(src, dst) for src, dst in (item.split(" -> ") for item in _listed(text))}


def _graph(root: Path) -> list[dict[str, Any]]:
    return [
        yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for path in sorted((root / ".beadloom" / "_graph").glob("*.yml"))
    ]


@then(parsers.parse("the code nodes init writes have exactly the sources {sources}"))
def _sources(state: dict[str, Any], sources: str) -> None:
    written = {
        str(node.get("source") or "")
        for data in _graph(state["root"])
        for node in data.get("nodes") or []
    }
    assert written - {""} == _listed(sources)


@then(parsers.parse("the scan paths init writes are exactly {paths}"))
def _scan_paths(state: dict[str, Any], paths: str) -> None:
    config = yaml.safe_load((state["root"] / ".beadloom" / "config.yml").read_text("utf-8"))
    assert set(config["scan_paths"]) == _listed(paths)


def _query(root: Path, sql: str, *params: str) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]


@then(parsers.parse("the index holds exactly the depends_on edges {edges}"))
def _indexed_edges(state: dict[str, Any], edges: str) -> None:
    rows = _query(
        state["root"], "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
    )
    assert {(str(src), str(dst)) for src, dst in rows} == _pairs(edges)


@then(parsers.parse('the index holds the import "{import_path}" of "{path}"'))
def _indexed_import(state: dict[str, Any], import_path: str, path: str) -> None:
    rows = _query(
        state["root"],
        "SELECT import_path FROM code_imports WHERE file_path = ? AND import_path = ?",
        path,
        import_path,
    )
    assert rows == [(import_path,)]
