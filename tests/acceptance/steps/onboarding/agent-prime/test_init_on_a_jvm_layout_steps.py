"""Step implementations for `onboarding/agent-prime/init_on_a_jvm_layout.feature`.

BDL-076 B6 (`beadloom-ujzb.15`). The real `beadloom init --yes` and `beadloom
reindex` run through the CLI on a Maven project and on a Gradle build written to
disk. What init writes is read back from its YAML, which is what an adopter
commits; what reindex derives is read from the index. Nothing is patched.

**FAKES PROVE FAKES.** This repository holds no Java or Kotlin. Each project
imports a third-party class whose package path shares a segment with one of its
own packages (`org.springframework.web...` beside a package `web`), which the
scan's segment reading would draw as an edge.
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

scenarios("../../../onboarding/agent-prime/init_on_a_jvm_layout.feature")

_TOLL = "src/main/java/org/acme/toll"

_MAVEN: dict[str, str] = {
    "pom.xml": "<project><artifactId>tollbooth</artifactId></project>\n",
    f"{_TOLL}/web/GateController.java": (
        "package org.acme.toll.web;\n\n"
        "import org.acme.toll.pricing.Tariff;\n\n"
        "public class GateController { Tariff tariff; }\n"
    ),
    f"{_TOLL}/pricing/Tariff.java": (
        "package org.acme.toll.pricing;\n\n"
        "import org.acme.toll.model.Vehicle;\n"
        "import org.springframework.web.client.RestClient;\n\n"
        "public class Tariff { Vehicle vehicle; RestClient client; }\n"
    ),
    f"{_TOLL}/model/Vehicle.java": "package org.acme.toll.model;\n\npublic class Vehicle {}\n",
    "src/test/java/org/acme/toll/pricing/TariffTest.java": (
        "package org.acme.toll.pricing;\n\n"
        "import org.acme.toll.model.Vehicle;\n"
        "import org.junit.jupiter.api.Test;\n\n"
        "class TariffTest { @Test void charges() {} }\n"
    ),
}

_APP = "app/src/main/kotlin/org/acme/app"
_CORE = "core/src/main/java/org/acme/core"

_GRADLE: dict[str, str] = {
    "settings.gradle.kts": 'rootProject.name = "orchardline"\n\ninclude("core", "app")\n',
    "build.gradle.kts": "",
    "core/build.gradle.kts": "plugins { java }\n",
    "app/build.gradle.kts": 'plugins { kotlin("jvm") }\n',
    f"{_CORE}/geo/Point.java": "package org.acme.core.geo;\n\npublic class Point {}\n",
    f"{_CORE}/model/Tree.java": (
        "package org.acme.core.model;\n\n"
        "import org.acme.core.geo.Point;\n\n"
        "public class Tree { Point at; }\n"
    ),
    f"{_APP}/planner/Plan.kt": (
        "package org.acme.app.planner\n\n"
        "import org.acme.core.geo.Point\n\n"
        "class Plan(val p: Point)\n"
    ),
    f"{_APP}/routing/Main.kt": (
        "package org.acme.app.routing\n\n"
        "import org.acme.app.planner.Plan\n"
        "import org.acme.core.model.Tree\n"
        "import io.ktor.server.routing.get\n\n"
        "fun main() { println(Plan::class) }\n"
    ),
    "app/src/test/kotlin/org/acme/app/planner/PlanTest.kt": (
        "package org.acme.app.planner\n\nimport kotlin.test.Test\n\nclass PlanTest\n"
    ),
}


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _write(root: Path, files: dict[str, str]) -> None:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


@given("a Maven project with the packages web, pricing and model under src/main/java")
def _maven(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = tmp_path / "tollbooth"
    _write(state["root"], _MAVEN)


@given("a Gradle build whose settings include the modules core in Java and app in Kotlin")
def _gradle(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = tmp_path / "orchardline"
    _write(state["root"], _GRADLE)


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


@then(parsers.parse("the graph init writes has exactly the depends_on edges {edges}"))
def _written_edges(state: dict[str, Any], edges: str) -> None:
    written = {
        (str(edge["src"]), str(edge["dst"]))
        for data in _graph(state["root"])
        for edge in data.get("edges") or []
        if edge.get("kind") == "depends_on"
    }
    assert written == _pairs(edges)


def _query(root: Path, sql: str, *params: str) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]


@then(parsers.parse("the index holds exactly the depends_on edges {edges}"))
def _indexed_edges(state: dict[str, Any], edges: str) -> None:
    rows = _query(
        state["root"], "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
    )
    assert {(str(src), str(dst)) for src, dst in rows} == _pairs(edges)


@then(parsers.parse('the test file "{path}" is bound to "{ref_id}"'))
def _bound(state: dict[str, Any], path: str, ref_id: str) -> None:
    assert _query(state["root"], "SELECT ref_id FROM test_files WHERE path = ?", path) == [
        (ref_id,)
    ]
