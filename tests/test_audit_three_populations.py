"""The audit reports three populations, not one (BDL-062 `.3`).

Before this bead the audit had a single population and a denominator that moved
without saying so.  A fact the registry could not compute was "silently omitted"
— the collector's own docstring — so ``3 of 9 declared fact(s) verified`` became
``3 of 8`` when the CLI surface was not registered, and nothing named the fact
that left.  Two of the nine were worse than uncounted: ``mcp_tool_count`` and
``cli_command_count`` were read out of the RUNNING package, so every adopter was
told Beadloom's numbers about their own documentation.

The report now separates:

``verified``                at least one document stated the fact and it was judged.
``not applicable``          the audit declared no value here, and says why.
``declared but unverified`` a value exists, nothing checked it — named, never
                            counted as fine.  ``version`` at zero mentions lives
                            here, and this file pins that it is visible.

Every assertion about the JSON is paired with the back-compat direction: 3.0.1
is a patch, so the payload may GAIN keys and may not lose one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.doc_sync.audit import AuditResult, FactRegistry
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    import sqlite3

#: This repository's root — the one project whose own surfaces the audit reports.
BEADLOOM_ROOT = Path(__file__).resolve().parents[1]

#: Every top-level key ``docs audit --json`` emitted in 3.0.0, captured from a
#: run on this repository at ``main``@``cdc16de``.  A consumer parsing that
#: payload must keep working, so this list may only grow.
KEYS_3_0_0: frozenset[str] = frozenset(
    {
        "facts",
        "stale",
        "fresh",
        "unmatched",
        "coverage",
        "unverified_facts",
        "scan_surface",
        "summary",
    }
)

#: The same, for the ``summary`` object.
SUMMARY_KEYS_3_0_0: frozenset[str] = frozenset(
    {
        "stale_count",
        "fresh_count",
        "unmatched_count",
        "declared_fact_count",
        "verified_fact_count",
        "unverified_count",
        "unreadable_count",
    }
)


def _adopter(tmp_path: Path, *, readme: str = "An invoicing service.") -> Path:
    """A project that is not Beadloom, indexed, with one document."""
    proj = tmp_path / "invoice-svc"
    (proj / ".beadloom").mkdir(parents=True)
    (proj / "pyproject.toml").write_text(
        '[project]\nname = "invoice-svc"\nversion = "3.7.0"\n', encoding="utf-8"
    )
    (proj / "README.md").write_text(f"# invoice-svc\n\n{readme}\n", encoding="utf-8")
    conn = open_db(proj / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    return proj


def _self_named(tmp_path: Path) -> Path:
    """A project that declares itself as this distribution, so the surfaces apply."""
    proj = tmp_path / "clone"
    (proj / ".beadloom").mkdir(parents=True)
    (proj / "pyproject.toml").write_text(
        '[project]\nname = "beadloom"\nversion = "3.0.0"\n', encoding="utf-8"
    )
    (proj / "README.md").write_text("# beadloom\n\nA tool.\n", encoding="utf-8")
    conn = open_db(proj / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    return proj


def _audit_json(project: Path, *extra: str) -> tuple[int, dict[str, object]]:
    invocation = CliRunner().invoke(
        main, ["docs", "audit", "--json", "--project", str(project), *extra]
    )
    payload = json.loads(invocation.stdout)
    assert isinstance(payload, dict)
    return invocation.exit_code, payload


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = open_db(tmp_path / "scratch.db")
    create_schema(c)
    return c


class TestJsonBackCompat:
    """3.0.1 is a patch: the payload gains keys and loses none."""

    def test_every_key_a_3_0_0_consumer_reads_is_still_there(
        self, tmp_path: Path
    ) -> None:
        _, payload = _audit_json(_adopter(tmp_path))

        missing = KEYS_3_0_0 - set(payload)
        assert not missing, f"keys a 3.0.0 consumer parses have gone: {sorted(missing)}"

    def test_every_summary_key_a_3_0_0_consumer_reads_is_still_there(
        self, tmp_path: Path
    ) -> None:
        _, payload = _audit_json(_adopter(tmp_path))

        summary = payload["summary"]
        assert isinstance(summary, dict)
        missing = SUMMARY_KEYS_3_0_0 - set(summary)
        assert not missing, f"summary keys have gone: {sorted(missing)}"

    def test_the_ci_gate_object_keeps_its_shape(self, tmp_path: Path) -> None:
        _, payload = _audit_json(_adopter(tmp_path), "--fail-if", "stale>0")

        gate = payload["ci_gate"]
        assert isinstance(gate, dict)
        assert {
            "expression",
            "stale_count",
            "metric_value",
            "threshold",
            "triggered",
        } <= set(gate)

    def test_unverified_facts_is_still_a_flat_list_of_names(
        self, tmp_path: Path
    ) -> None:
        _, payload = _audit_json(_adopter(tmp_path))

        unverified = payload["unverified_facts"]
        assert isinstance(unverified, list)
        assert all(isinstance(name, str) for name in unverified)


class TestThreePopulations:
    """Verified, not applicable, declared-but-unverified — named and disjoint."""

    def test_json_names_the_facts_it_declined_and_why(self, tmp_path: Path) -> None:
        _, payload = _audit_json(_adopter(tmp_path))

        not_applicable = payload["not_applicable"]
        assert isinstance(not_applicable, dict)
        assert "mcp_tool_count" in not_applicable
        reason = not_applicable["mcp_tool_count"]["reason"]
        assert isinstance(reason, str)
        assert "invoice-svc" in reason, reason
        assert "extra_facts" in reason, reason

    def test_json_names_the_facts_it_verified(self, tmp_path: Path) -> None:
        _, payload = _audit_json(_adopter(tmp_path))

        assert isinstance(payload["verified_facts"], list)

    def test_summary_counts_the_population_it_did_not_check(
        self, tmp_path: Path
    ) -> None:
        _, payload = _audit_json(_adopter(tmp_path))

        summary = payload["summary"]
        assert isinstance(summary, dict)
        not_applicable = payload["not_applicable"]
        assert isinstance(not_applicable, dict)
        assert summary["not_applicable_count"] == len(not_applicable)
        assert summary["not_applicable_count"] > 0, (
            "an adopter project cannot have Beadloom's surface facts"
        )

    def test_version_at_zero_mentions_is_named_not_merely_counted(
        self, tmp_path: Path
    ) -> None:
        _, payload = _audit_json(_adopter(tmp_path))

        facts = payload["facts"]
        unverified = payload["unverified_facts"]
        assert isinstance(facts, dict)
        assert isinstance(unverified, list)
        assert facts["version"]["value"] == "3.7.0", "the adopter declares a version"
        assert "version" in unverified

    def test_the_denominator_covers_exactly_the_declared_facts(
        self, tmp_path: Path
    ) -> None:
        _, payload = _audit_json(_adopter(tmp_path))

        summary = payload["summary"]
        assert isinstance(summary, dict)
        facts = payload["facts"]
        assert isinstance(facts, dict)
        assert summary["declared_fact_count"] == len(facts)
        assert (
            summary["verified_fact_count"] + summary["unverified_count"]
            == summary["declared_fact_count"]
        )

    def test_a_declined_fact_is_outside_the_denominator(self, tmp_path: Path) -> None:
        """Not applicable is neither verified nor unverified — it is not declared."""
        _, payload = _audit_json(_adopter(tmp_path))

        facts = payload["facts"]
        not_applicable = payload["not_applicable"]
        unverified = payload["unverified_facts"]
        assert isinstance(facts, dict)
        assert isinstance(not_applicable, dict)
        assert isinstance(unverified, list)
        assert not set(facts) & set(not_applicable)
        assert not set(unverified) & set(not_applicable)


class TestRichOutput:
    """The human report states the same three populations."""

    def test_it_names_the_facts_it_declined_with_the_reason(
        self, tmp_path: Path
    ) -> None:
        invocation = CliRunner().invoke(
            main, ["docs", "audit", "--project", str(_adopter(tmp_path))]
        )

        assert invocation.exit_code == 0
        assert "not applicable" in invocation.output.lower(), invocation.output
        assert "mcp_tool_count" in invocation.output

    def test_it_says_nothing_extra_when_every_declared_fact_applies(
        self, tmp_path: Path
    ) -> None:
        """This repository's output is unchanged: no declines, no extra line."""
        invocation = CliRunner().invoke(
            main, ["docs", "audit", "--project", str(_self_named(tmp_path))]
        )

        assert invocation.exit_code == 0
        assert "not applicable" not in invocation.output.lower(), invocation.output


class TestGateLine:
    """`beadloom ci`'s docs-audit line carries the population it could not compute."""

    def test_the_line_names_a_fact_the_audit_could_not_compute(self) -> None:
        from beadloom.application.gate import _audit_summary

        result = AuditResult(
            facts={},
            findings=[],
            unmatched=[],
            coverage={},
            not_applicable={"cli_command_count": "no CLI surface is registered"},
        )

        line = _audit_summary(result, [])
        assert "cli_command_count" in line, line
        assert "not applicable" in line.lower(), line

    def test_the_line_is_unchanged_when_nothing_was_declined(self) -> None:
        from beadloom.application.gate import _audit_summary

        result = AuditResult(facts={}, findings=[], unmatched=[], coverage={})

        assert "not applicable" not in _audit_summary(result, []).lower()


class TestAnUnknownSurfaceIsNotAnAbsentFact:
    """The measured instance: an unregistered CLI turned 3/9 into 3/8, silently.

    ``_collect_cli_command_count`` used to return without a trace when no CLI
    surface was registered, so the denominator moved and no output said which
    fact had left.  Running the audit in-process — which is what
    ``beadloom ci``'s gate step does — was enough to see it.
    """

    @pytest.fixture(autouse=True)
    def _no_cli_surface(self) -> object:
        import beadloom.infrastructure.surface_registry as registry

        saved = registry._cli_group_provider
        registry.reset_surface_providers()
        yield
        registry._cli_group_provider = saved

    def test_the_fact_is_declined_with_a_reason_not_dropped(
        self, conn: sqlite3.Connection
    ) -> None:
        from beadloom.infrastructure.surface_registry import get_cli_group

        assert get_cli_group() is None, "the surface must be unknown for this test"

        fact_set = FactRegistry().collect_set(BEADLOOM_ROOT, conn)

        assert "cli_command_count" not in fact_set.facts
        reason = fact_set.not_applicable["cli_command_count"]
        assert "registered" in reason, reason


class TestThisRepository:
    """The equality the RFC demands: on Beadloom, the derivation returns today's values."""

    def test_beadloom_declines_none_of_its_own_facts(
        self, conn: sqlite3.Connection
    ) -> None:
        import beadloom.services.cli  # noqa: F401  — registers the CLI surface

        fact_set = FactRegistry().collect_set(BEADLOOM_ROOT, conn)

        assert fact_set.not_applicable == {}, (
            "this repository must lose no fact, or its audit output changed"
        )
        assert "mcp_tool_count" in fact_set.facts
        assert "cli_command_count" in fact_set.facts
