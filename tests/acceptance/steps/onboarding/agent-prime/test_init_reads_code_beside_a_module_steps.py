"""Step implementations for `onboarding/agent-prime/init_reads_code_beside_a_module.feature`.

BDL-076, the re-review's finding m3, fixed by ``beadloom-ujzb.24``. The real ``beadloom
init --yes`` and ``beadloom reindex`` run through the CLI on two projects written to
disk: a Gradle module holding Python scripts outside its source roots, and a Maven
service with a Python file lying directly beside it. What init writes is read back
from its YAML, what reindex indexed from the index, and what init says from its output.

**FAKES PROVE FAKES.** The scripts define a function, so a symbol in the index proves
that reindex read the file; a scan path alone would only prove that init named it.
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
pytest.importorskip("tree_sitter_kotlin")

scenarios("../../../onboarding/agent-prime/init_reads_code_beside_a_module.feature")

_GRADLE_WITH_SCRIPTS: dict[str, str] = {
    "settings.gradle.kts": 'include(":backend")\n',
    "backend/build.gradle.kts": "\n",
    "backend/src/main/kotlin/com/acme/api/Api.kt": (
        "package com.acme.api\n\nimport com.acme.core.Core\n\nclass Api(val core: Core)\n"
    ),
    "backend/src/main/kotlin/com/acme/core/Core.kt": "package com.acme.core\n\nclass Core\n",
    "backend/src/test/kotlin/com/acme/core/CoreTest.kt": (
        "package com.acme.core\n\nclass CoreTest\n"
    ),
    "backend/scripts/deploy/__init__.py": "from deploy import helm\n",
    "backend/scripts/deploy/helm.py": "def render() -> int:\n    return 1\n",
    "web/package.json": '{"name": "web"}\n',
    "web/src/x/a.ts": "export const a = 1;\n",
}

_BILLING = "services/billing/src/main/java/org/acme/billing"

_MAVEN_WITH_A_FILE_BESIDE: dict[str, str] = {
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
    "services/notify/notify/__init__.py": "def notify() -> int:\n    return 1\n",
    "services/run.py": "def run() -> int:\n    return 0\n",
}


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _write(root: Path, files: dict[str, str]) -> None:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


@given('a Gradle project whose module "backend" holds Python scripts in "backend/scripts"')
def _gradle_with_scripts(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = tmp_path / "modscripts"
    _write(state["root"], _GRADLE_WITH_SCRIPTS)


@given(
    'a monorepo with a Maven service "services/billing" and a file "services/run.py" beside it'
)
def _maven_with_a_file_beside(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = tmp_path / "tri"
    _write(state["root"], _MAVEN_WITH_A_FILE_BESIDE)


def _run(state: dict[str, Any], *args: str) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(state["root"])])
    assert result.exit_code == 0, result.output
    return result.output


@when("beadloom init is run without prompts")
def _init(state: dict[str, Any]) -> None:
    state["init_output"] = _run(state, "init", "--yes")


@when("beadloom reindex is run")
def _reindex(state: dict[str, Any]) -> None:
    _run(state, "reindex")


def _listed(text: str) -> set[str]:
    return {part.strip().strip('"') for part in text.split(",")}


@then(parsers.parse("the scan paths init writes are exactly {paths}"))
def _scan_paths(state: dict[str, Any], paths: str) -> None:
    config = yaml.safe_load((state["root"] / ".beadloom" / "config.yml").read_text("utf-8"))
    assert set(config["scan_paths"]) == _listed(paths)


@then(parsers.parse('the index holds the symbols of "{path}"'))
def _indexed_symbols(state: dict[str, Any], path: str) -> None:
    with sqlite3.connect(state["root"] / ".beadloom" / "beadloom.db") as conn:
        rows = conn.execute(
            "SELECT symbol_name FROM code_symbols WHERE file_path = ?", (path,)
        ).fetchall()
    assert rows, f"no symbol of {path} was indexed"


@then(parsers.parse('init says it also scanned "{folder}" beside a module'))
def _says_scanned(state: dict[str, Any], folder: str) -> None:
    lines = [line for line in state["init_output"].splitlines() if "Also scanned:" in line]
    assert len(lines) == 1, state["init_output"]
    assert folder in lines[0]


@then(parsers.parse('init names "{path}" as not read'))
def _names_unread(state: dict[str, Any], path: str) -> None:
    lines = [line for line in state["init_output"].splitlines() if "Not read:" in line]
    assert len(lines) == 1, state["init_output"]
    assert path in lines[0]
