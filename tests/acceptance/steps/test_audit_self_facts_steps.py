"""Step implementations for `features/audit_self_facts.feature` (BDL-062, `.3`).

The steps run the real ``FactRegistry`` and the real ``run_audit`` against a
project on disk. Nothing is stubbed, and the CLI surface provider is registered
before the adopter scenarios run — a fixture the leak cannot reach proves
nothing about the leak, and an unregistered CLI group would make
``cli_command_count`` absent for a reason that has nothing to do with this fix.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.doctor import get_actual_version
from beadloom.doc_sync.audit import FactRegistry, run_audit
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.mcp_tools import MCP_TOOL_CATALOG
from beadloom.infrastructure.surface_registry import get_cli_group

if TYPE_CHECKING:
    from beadloom.doc_sync.audit import AuditResult, FactSet

scenarios("../features/audit_self_facts.feature")

def _beadloom_root() -> Path:
    """This repository's root, found from the installed package rather than here.

    ``tests/acceptance`` is copied out of the repository and run from another
    directory by ``test_bead14_s4_binding``, so a path derived from this file's
    own parents points at the copy. The package's location does not move.
    """
    import beadloom

    for candidate in Path(beadloom.__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("no manifest above the beadloom package — cannot locate its root")


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


@pytest.fixture(autouse=True)
def _cli_surface_registered() -> None:
    """Import the CLI so the running Click group is available to the audit.

    Without this the pre-fix code would omit ``cli_command_count`` for the wrong
    reason and the scenario would pass against a defect it never exercised.
    """
    import beadloom.services.cli  # noqa: F401

    assert get_cli_group() is not None, "the CLI surface must be live for these steps"


def _adopter_db(root: Path) -> sqlite3.Connection:
    """A graph database holding the adopter's own nodes, not ours."""
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.execute("INSERT INTO nodes (ref_id, kind) VALUES (?, ?)", ("billing", "domain"))
    conn.execute("INSERT INTO nodes (ref_id, kind) VALUES (?, ?)", ("ledger", "domain"))
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("billing", "ledger", "depends_on"),
    )
    conn.commit()
    return conn


#: The adopter's own identity. It is built here rather than imported from
#: ``tests.adopter_project`` because the acceptance suite is copied out of the
#: repository and run from another directory by ``test_bead14_s4_binding``, where
#: a ``tests.`` import does not resolve and the copy fails at collection.
ADOPTER_NAME = "invoice-svc"
ADOPTER_VERSION = "3.7.0"


@given("a Python project that is not Beadloom")
def _adopter(world: dict[str, Any], tmp_path: Path) -> None:
    root = tmp_path / "adopter"
    (root / "src" / "invoice_svc").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "{ADOPTER_NAME}"\nversion = "{ADOPTER_VERSION}"\n'
        'dependencies = ["fastapi", "sqlalchemy"]\n',
        encoding="utf-8",
    )
    (root / "src" / "invoice_svc" / "__init__.py").write_text("", encoding="utf-8")
    (root / "README.md").write_text(
        f"# {ADOPTER_NAME}\n\nAn invoicing service.\n", encoding="utf-8"
    )
    world["project_name"] = ADOPTER_NAME
    world["root"] = root
    world["db"] = _adopter_db(root)


@given("the project under audit is Beadloom's own repository")
def _self(world: dict[str, Any]) -> None:
    # The database contents do not enter the two surface facts; what decides
    # them is the project root, so an empty schema keeps the step honest and
    # leaves this repository's own index untouched.
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    world["root"] = _beadloom_root()
    world["db"] = conn


@when("the audit collects that project's facts")
def _collect(world: dict[str, Any]) -> None:
    world["fact_set"] = FactRegistry().collect_set(world["root"], world["db"])


@when("the audit runs over that project's documents")
def _run(world: dict[str, Any]) -> None:
    world["result"] = run_audit(world["root"], world["db"])


def _fact_set(world: dict[str, Any]) -> FactSet:
    fact_set: FactSet = world["fact_set"]
    return fact_set


def _result(world: dict[str, Any]) -> AuditResult:
    result: AuditResult = world["result"]
    return result


@then("no declared fact carries a value read from Beadloom's own source")
def _no_self_facts(world: dict[str, Any]) -> None:
    facts = _fact_set(world).facts
    ours = {
        len(MCP_TOOL_CATALOG): "the MCP tool catalogue's length",
        get_actual_version(): "Beadloom's own version",
    }
    offenders = [
        f"{name}={fact.value!r} ({ours[fact.value]})"
        for name, fact in facts.items()
        if fact.value in ours
    ]
    assert not offenders, f"facts read from Beadloom's own source: {offenders}"
    assert "mcp_tool_count" not in facts
    assert "cli_command_count" not in facts


@then("the MCP tool count is reported not applicable, and the reason names the project")
def _reason_names_project(world: dict[str, Any]) -> None:
    declined = _fact_set(world).not_applicable
    assert "mcp_tool_count" in declined, declined
    reason = declined["mcp_tool_count"]
    assert world["project_name"] in reason, reason
    assert "extra_facts" in reason, reason


@then("the MCP tool count equals the length of the tool catalogue")
def _self_mcp(world: dict[str, Any]) -> None:
    fact = _fact_set(world).facts["mcp_tool_count"]
    assert fact.value == len(MCP_TOOL_CATALOG)
    assert fact.source == "MCP tool catalog"


@then("the CLI command count equals the number of commands the CLI registers")
def _self_cli(world: dict[str, Any]) -> None:
    fact = _fact_set(world).facts["cli_command_count"]
    expected = FactRegistry._count_click_commands(get_cli_group())
    assert fact.value == expected
    assert fact.source == "CLI"


@then("every fact the audit declined to declare carries a reason")
def _declines_carry_reasons(world: dict[str, Any]) -> None:
    declined = _fact_set(world).not_applicable
    assert declined, "an adopter project must have at least one declined fact"
    empty = [name for name, reason in declined.items() if not reason.strip()]
    assert not empty, f"declined without a reason: {empty}"


@then("the report states how many of the declared facts were verified")
def _states_denominator(world: dict[str, Any]) -> None:
    result = _result(world)
    verified = result.verified_facts
    assert len(verified) + len(result.unverified_facts) == len(result.facts)


@then("it names version among the facts declared but unverified")
def _names_version(world: dict[str, Any]) -> None:
    result = _result(world)
    assert "version" in result.facts, "the adopter declares a version"
    assert "version" in result.unverified_facts, result.unverified_facts


@then("the three populations share no fact between them")
def _disjoint(world: dict[str, Any]) -> None:
    result = _result(world)
    verified = set(result.verified_facts)
    unverified = set(result.unverified_facts)
    not_applicable = set(result.not_applicable)
    assert not verified & unverified
    assert not verified & not_applicable
    assert not unverified & not_applicable
