"""The wave decision: what serialises a pair, what orders a wave, what an override does.

The acceptance suite states the behaviour; these cover the reasons the scenarios
do not reach individually — the file and edge overlaps, the tracker's own
ordering, the override arithmetic and the configuration errors.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest

from beadloom.application.waves import (
    GATE_COMMIT_SCOPED,
    REASON_BLOCKED_BY_BEAD,
    REASON_DEPENDENCY_EDGE,
    REASON_OVERRIDE_SERIAL,
    REASON_SHARED_FILE,
    REASON_SHARED_NODE,
    REASON_UNRESOLVED_SCOPE,
    SHARED_MEDIA,
    BeadRecord,
    WaveConfigError,
    WaveEnvironment,
    WaveOverride,
    declared_refs,
    load_overrides,
    plan_waves,
    resolve_scope,
    room_for,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _node(conn: sqlite3.Connection, ref: str, source: str, kind: str = "feature") -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        (ref, kind, ref, source),
    )


def _file(conn: sqlite3.Connection, path: str) -> None:
    conn.execute(
        "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
        (path, f"h-{path}", "code", "2026-08-24T00:00:00Z"),
    )


def _edge(conn: sqlite3.Connection, src: str, dst: str, kind: str) -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        (src, dst, kind),
    )


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """A small real index: two disjoint features, and one domain over both."""
    connection = open_db(tmp_path / "beadloom.db")
    create_schema(connection)
    _node(connection, "billing", "src/billing/")
    _node(connection, "shipping", "src/shipping/")
    _file(connection, "src/billing/core.py")
    _file(connection, "src/shipping/core.py")
    connection.commit()
    return connection


def _bead(bead_id: str, refs: str = "", blocked_by: frozenset[str] = frozenset()) -> BeadRecord:
    return BeadRecord(
        bead_id=bead_id,
        declaration=f"work.\nrefs: {refs}" if refs else "work.",
        blocked_by=blocked_by,
    )


class TestDeclaredRefs:
    """The one place a bead's declaration is read."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("refs: a, b", ("a", "b")),
            ("ref: a", ("a",)),
            ("area: a", ("a",)),
            ("refs: a\nrefs: b", ("a", "b")),
            # Every OCCURRENCE is read, but only where one opens a line: the
            # second `refs:` below sits inside a sentence and is prose.
            ("refs: a\nand then refs: b", ("a",)),
            ("refs: a. Then some prose about b", ("a",)),
            # A declaration written inside prose: the id, then talk about it.
            ("ref: FEAT-1 Touches FEAT-1", ("FEAT-1",)),
            ("refs: a, b are the two nodes", ("a", "b")),
            ("no declaration at all", ()),
            ("refs: `a`, 'b'", ("a", "b")),
        ],
    )
    def test_reads_every_accepted_spelling(self, text: str, expected: tuple[str, ...]) -> None:
        assert declared_refs(text) == expected

    def test_the_mcp_bead_context_tool_reads_through_this_one_parser(self) -> None:
        """One fact, one source: `bead_context` must not re-implement the parse."""
        from beadloom.services import mcp_server

        assert mcp_server.declared_refs is declared_refs


class TestScope:
    def test_a_declared_ref_the_graph_lacks_is_unresolved_not_empty(
        self, conn: sqlite3.Connection
    ) -> None:
        scope = resolve_scope(conn, _bead("a", "nowhere"))
        assert not scope.resolved
        assert scope.unknown_refs == ("nowhere",)

    def test_a_scope_expands_downward_through_part_of(
        self, conn: sqlite3.Connection
    ) -> None:
        _node(conn, "payments", "src/", kind="domain")
        _edge(conn, "billing", "payments", "part_of")
        conn.commit()
        assert resolve_scope(conn, _bead("a", "payments")).refs == {"payments", "billing"}


class TestSerialisationReasons:
    def test_disjoint_scopes_share_a_wave(self, conn: sqlite3.Connection) -> None:
        """Independent subgraphs share a wave, and a measured wave is exit 0.

        The environment is supplied because a concurrent wave whose shared media
        nobody measured reaches exit 1 by design — the assertion below is about
        the shape, so it says who measured what rather than relying on a default
        that no longer means "clean".
        """
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "shipping")],
            conn=conn,
            environment=WaveEnvironment(
                tree_changed_paths=(),
                commit_gate=GATE_COMMIT_SCOPED,
                doc_baseline_stale_pairs=0,
            ),
        )
        assert plan.wave_of("a") == plan.wave_of("b")
        assert plan.conflicts == ()
        assert plan.exit_code == 0

    def test_a_domain_and_its_component_are_serialised_as_a_shared_node(
        self, conn: sqlite3.Connection
    ) -> None:
        _node(conn, "payments", "src/", kind="domain")
        _edge(conn, "billing", "payments", "part_of")
        conn.commit()
        plan = plan_waves([_bead("a", "payments"), _bead("b", "billing")], conn=conn)
        assert [c.reason for c in plan.conflicts] == [REASON_SHARED_NODE]
        assert plan.conflicts[0].detail == "billing"

    def test_two_nodes_over_one_file_are_serialised_as_a_shared_file(
        self, conn: sqlite3.Connection
    ) -> None:
        _node(conn, "alias", "src/billing/")
        conn.commit()
        plan = plan_waves([_bead("a", "billing"), _bead("b", "alias")], conn=conn)
        assert [c.reason for c in plan.conflicts] == [REASON_SHARED_FILE]
        assert plan.conflicts[0].detail == "src/billing/core.py"

    def test_a_depends_on_edge_between_scopes_serialises(
        self, conn: sqlite3.Connection
    ) -> None:
        _edge(conn, "billing", "shipping", "depends_on")
        conn.commit()
        plan = plan_waves([_bead("a", "billing"), _bead("b", "shipping")], conn=conn)
        assert [c.reason for c in plan.conflicts] == [REASON_DEPENDENCY_EDGE]
        assert plan.conflicts[0].detail == "billing -> shipping"

    def test_a_part_of_edge_alone_does_not_serialise_disjoint_scopes(
        self, conn: sqlite3.Connection
    ) -> None:
        """Only `depends_on` says one node's change reaches the other."""
        _edge(conn, "billing", "shipping", "touches_code")
        conn.commit()
        plan = plan_waves([_bead("a", "billing"), _bead("b", "shipping")], conn=conn)
        assert plan.conflicts == ()

    def test_the_tracker_ordering_outranks_a_code_level_verdict(
        self, conn: sqlite3.Connection
    ) -> None:
        beads = [_bead("a", "billing", frozenset({"b"})), _bead("b", "shipping")]
        plan = plan_waves(beads, conn=conn)
        assert [c.reason for c in plan.conflicts] == [REASON_BLOCKED_BY_BEAD]
        assert plan.wave_of("b") < plan.wave_of("a")

    def test_a_blocker_that_sorts_after_its_dependent_still_runs_first(
        self, conn: sqlite3.Connection
    ) -> None:
        """Sorted order alone would place the blocked bead first."""
        beads = [_bead("a", "billing", frozenset({"z"})), _bead("z", "shipping")]
        plan = plan_waves(beads, conn=conn)
        assert plan.wave_of("z") < plan.wave_of("a")

    def test_a_blocker_outside_the_request_is_not_invented(
        self, conn: sqlite3.Connection
    ) -> None:
        beads = [_bead("a", "billing", frozenset({"elsewhere"})), _bead("b", "shipping")]
        assert plan_waves(beads, conn=conn).conflicts == ()


class TestUnresolvedScope:
    def test_a_bead_that_declares_nothing_is_serialised_against_every_bead(
        self, conn: sqlite3.Connection
    ) -> None:
        beads = [_bead("a", "billing"), _bead("b", "shipping"), _bead("mute")]
        plan = plan_waves(beads, conn=conn)
        assert plan.wave_of("a") == plan.wave_of("b")
        assert plan.wave_of("mute") not in (None, plan.wave_of("a"))
        assert {c.reason for c in plan.conflicts} == {REASON_UNRESOLVED_SCOPE}

    def test_an_unresolved_scope_is_a_finding_with_its_remedy(
        self, conn: sqlite3.Connection
    ) -> None:
        plan = plan_waves([_bead("a", "billing"), _bead("mute")], conn=conn)
        assert plan.exit_code == 1
        assert any("mute" in f and "refs:" in f for f in plan.findings)


class TestOverrides:
    def test_a_parallel_override_reports_the_decision_it_changed(
        self, conn: sqlite3.Connection
    ) -> None:
        override = WaveOverride(("a", "b"), "parallel", "measured", "2099-01-01")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "billing")],
            conn=conn,
            overrides=[override],
        )
        assert plan.wave_of("a") == plan.wave_of("b")
        assert plan.overrides[0].changed == 1
        assert not plan.overrides[0].inert

    def test_a_serial_override_adds_a_named_conflict(
        self, conn: sqlite3.Connection
    ) -> None:
        override = WaveOverride(("a", "b"), "serial", "measured", "2099-01-01")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "shipping")],
            conn=conn,
            overrides=[override],
        )
        assert [c.reason for c in plan.conflicts] == [REASON_OVERRIDE_SERIAL]
        assert plan.wave_of("a") != plan.wave_of("b")

    def test_an_override_that_changes_nothing_is_a_finding(
        self, conn: sqlite3.Connection
    ) -> None:
        override = WaveOverride(("a", "b"), "parallel", "measured", "2099-01-01")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "shipping")],
            conn=conn,
            overrides=[override],
        )
        assert plan.overrides[0].inert
        assert any("inert_override" in f for f in plan.findings)
        assert plan.exit_code == 1

    def test_an_override_past_a_dated_exit_condition_is_a_finding(
        self, conn: sqlite3.Connection
    ) -> None:
        override = WaveOverride(("a", "b"), "parallel", "measured", "2020-01-01")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "billing")],
            conn=conn,
            overrides=[override],
            today=date(2026, 8, 24),
        )
        assert plan.overrides[0].expired
        assert any("expired_override" in f for f in plan.findings)

    def test_an_event_shaped_exit_condition_never_expires(
        self, conn: sqlite3.Connection
    ) -> None:
        override = WaveOverride(("a", "b"), "parallel", "measured", "when S6 lands")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "billing")],
            conn=conn,
            overrides=[override],
            today=date(2026, 8, 24),
        )
        assert not plan.overrides[0].expired


class TestSharedMedia:
    def test_a_wave_of_more_than_one_bead_names_four_media(
        self, conn: sqlite3.Connection
    ) -> None:
        plan = plan_waves([_bead("a", "billing"), _bead("b", "shipping")], conn=conn)
        assert plan.shared_media == SHARED_MEDIA
        assert len(SHARED_MEDIA) == 4

    def test_a_plan_that_runs_nothing_concurrently_names_the_same_media(
        self, conn: sqlite3.Connection
    ) -> None:
        """BDL-UX #228 — the counter-claim this replaces.

        The first version returned no medium at all when no wave held more than
        one bead. That read the width of ONE plan as solitude, and the silence
        landed exactly where the coordinator was not already thinking about
        concurrency: roughly twenty single-bead waves across two epics carried
        the discipline by launch prompt alone.
        """
        plan = plan_waves([_bead("a", "billing"), _bead("b", "billing")], conn=conn)
        assert all(len(wave.beads) == 1 for wave in plan.waves)
        assert plan.shared_media == SHARED_MEDIA

    def test_every_medium_carries_its_evidence(self) -> None:
        for medium in SHARED_MEDIA:
            assert medium.evidence.startswith("BDL-UX #")
            assert len(medium.statement) > 40

    def test_the_room_a_bead_owes_carries_that_bead_s_id(self) -> None:
        """BDL-UX #235 — a room whose name cannot say whose it is is shared."""
        assert room_for("beadloom-67t1") == "room-beadloom-67t1"
        assert room_for("a") != room_for("b")

    def test_every_bead_of_every_wave_is_given_a_room_of_its_own(
        self, conn: sqlite3.Connection
    ) -> None:
        plan = plan_waves([_bead("a", "billing"), _bead("b", "shipping")], conn=conn)
        beads = [bead for wave in plan.waves for bead in wave.beads]
        assert len({room_for(bead) for bead in beads}) == len(beads)

    def test_each_wave_names_a_gate_owner_from_its_own_members(
        self, conn: sqlite3.Connection
    ) -> None:
        plan = plan_waves([_bead("a", "billing"), _bead("b", "shipping")], conn=conn)
        for wave in plan.waves:
            assert wave.gate_owner in wave.beads


class TestDeterminism:
    def test_the_same_inputs_produce_the_same_shape(
        self, conn: sqlite3.Connection
    ) -> None:
        beads = [_bead("c", "billing"), _bead("a", "shipping"), _bead("b", "billing")]
        first = plan_waves(beads, conn=conn)
        second = plan_waves(list(reversed(beads)), conn=conn)
        assert [w.beads for w in first.waves] == [w.beads for w in second.waves]


class TestOverrideConfig:
    def _write(self, root: Path, body: str) -> Path:
        (root / ".beadloom").mkdir(parents=True, exist_ok=True)
        (root / ".beadloom" / "flow.yml").write_text(body, encoding="utf-8")
        return root

    def test_no_flow_file_declares_no_override(self, tmp_path: Path) -> None:
        assert load_overrides(tmp_path) == ()

    def test_no_waves_block_declares_no_override(self, tmp_path: Path) -> None:
        self._write(tmp_path, "tools: [claude]\n")
        assert load_overrides(tmp_path) == ()

    def test_a_complete_override_loads(self, tmp_path: Path) -> None:
        self._write(
            tmp_path,
            "waves:\n"
            "  overrides:\n"
            "  - beads: [a, b]\n"
            "    decision: parallel\n"
            "    reason: measured\n"
            "    until: '2099-01-01'\n",
        )
        loaded = load_overrides(tmp_path)
        assert loaded[0].beads == ("a", "b")
        assert loaded[0].decision == "parallel"

    @pytest.mark.parametrize(
        ("body", "fragment"),
        [
            (
                "waves:\n  overrides:\n  - beads: [a, b]\n    decision: parallel\n"
                "    reason: measured\n",
                "until",
            ),
            (
                "waves:\n  overrides:\n  - beads: [a, b]\n    decision: parallel\n"
                "    until: '2099-01-01'\n",
                "reason",
            ),
            (
                "waves:\n  overrides:\n  - beads: [a]\n    decision: parallel\n"
                "    reason: measured\n    until: '2099-01-01'\n",
                "fewer than two",
            ),
            (
                "waves:\n  overrides:\n  - beads: [a, b]\n    decision: maybe\n"
                "    reason: measured\n    until: '2099-01-01'\n",
                "unknown decision",
            ),
            (
                "waves:\n  overrides:\n  - beads: [a, b]\n    decision: parallel\n"
                "    reason: measured\n    until: '2099-01-01'\n    exclude: '*'\n",
                "unknown key",
            ),
            ("waves:\n  overides: []\n", "unknown key"),
        ],
    )
    def test_an_override_that_cannot_be_used_as_declared_is_an_error(
        self, tmp_path: Path, body: str, fragment: str
    ) -> None:
        self._write(tmp_path, body)
        with pytest.raises(WaveConfigError, match=fragment):
            load_overrides(tmp_path)
