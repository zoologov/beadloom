"""Step implementations for `features/version_subject.feature`.

BDL-068 S6, `beadloom-0mdo.63`, closing BDL-UX #253 and the foreign-subject face
of #190. The steps run the real :func:`run_audit` over a real project directory:
a stubbed scanner would agree with whatever the fix asserted and would say
nothing about the manifest and config reads the subject vocabulary is derived
from.

The module is named ``test_*`` so default pytest collection picks the scenarios
up: the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.doc_sync.audit import run_audit
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/version_subject.feature")


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


@given(
    parsers.parse(
        'a project at version "{version}" whose documentation declares '
        "{subject} a subject"
    )
)
def _project(
    world: dict[str, Any], version: str, subject: str, tmp_path: Path
) -> None:
    root = tmp_path / "adopter"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "beadloom"\n'
        f'version = "{version}"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["click>=8.1"]\n',
        encoding="utf-8",
    )
    (root / ".beadloom").mkdir()
    (root / ".beadloom" / "config.yml").write_text(
        f"docs_audit:\n  subjects:\n    - {subject}\n", encoding="utf-8"
    )
    world["root"] = root


@given(parsers.parse('a document reading "{line}"'))
def _document(world: dict[str, Any], line: str) -> None:
    (world["root"] / "README.md").write_text(f"# Title\n\n{line}\n", encoding="utf-8")


@when("the audit reads that project")
def _run(world: dict[str, Any]) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    world["result"] = run_audit(world["root"], conn)
    conn.close()


def _stale_versions(world: dict[str, Any]) -> list[Any]:
    return [
        finding
        for finding in world["result"].findings
        if finding.mention.fact_name == "version" and finding.status == "stale"
    ]


@then("no finding reports a stale version")
def _no_stale(world: dict[str, Any]) -> None:
    assert _stale_versions(world) == []


@then("a finding reports a stale version")
def _stale(world: dict[str, Any]) -> None:
    assert _stale_versions(world), "expected a stale version finding, got none"


@then(parsers.parse("the audit attributes {count:d} version token to {subject}"))
def _attributed(world: dict[str, Any], count: int, subject: str) -> None:
    attributed = [
        mention
        for mention in world["result"].attributed
        if mention.subject == subject
    ]
    assert len(attributed) == count, (
        f"expected {count} token(s) attributed to {subject}, "
        f"got {[(m.value, m.subject) for m in world['result'].attributed]}"
    )
