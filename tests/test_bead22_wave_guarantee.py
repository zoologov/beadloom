"""BDL-061.22 — the wave guarantee, held to its own two clauses.

``beadloom waves`` promises: *for any two beads placed in the same wave, no
medium they share can carry one bead's in-progress state into the other's result
— and where a medium cannot give that guarantee, the wave says so and names the
one bead that measures the combined outcome.*

The first clause is decided from the graph, and ``tests/test_wave_plan.py``
covers its main paths. This module attacks what a happy-path suite does not
reach:

* the first clause under overlaps that are transitive, absent, or shaped like
  containment rather than equality;
* the second clause's silencing conditions. The four media are a constant tuple
  and a wave of one names none of them, so the question worth asking is whether
  a wave that genuinely holds two can ever fail to name all four;
* the override path — the third exclusion mechanism this epic has shipped, after
  the guard exclusions (``.48``, whose dead entries went unreported) and the
  ``forbid_import`` exemptions (``.49``, whose ``until`` was never parsed);
* the two failures this session actually had, replayed: BDL-UX #181 (four agents
  green, the tree red) and BDL-UX #171 (a valid-but-wrong dependency edge).

Five defects were measured while writing it. Each was stated as the behaviour it
SHOULD have and marked ``xfail(strict=True)`` with ``FINDING BDL-061.22-N`` in
its docstring — the convention ``.18`` set. A finding that lives only in a review
report is a finding nobody re-measures, and a non-strict xfail can be an artefact
of a broken fixture rather than a real defect (TESTS MUST BITE).

``beadloom-mr2l.80`` CLOSED all five. A strict xfail turns red the moment its
defect is fixed, so closing one means removing the marker, and the five tests
below are now ordinary regression tests. Each keeps its ``FINDING BDL-061.22-N``
id, and ``TestEveryFindingHereIsStrictAndNamesItself`` asserts that every id is
still owned by a test that passes — otherwise a closed finding becomes a test
nobody can trace back to the defect it was written for.
"""

from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from beadloom.application.waves import (
    GATE_COMMIT_SCOPED,
    MEDIUM_COMMIT_GATE,
    MEDIUM_DOC_BASELINE,
    MEDIUM_TRACKER_IDS,
    MEDIUM_WORKING_TREE,
    REASON_BLOCKED_BY_BEAD,
    REASON_DEPENDENCY_EDGE,
    REASON_SHARED_NODE,
    REASON_UNRESOLVED_SCOPE,
    SHARED_MEDIA,
    UNRESOLVED_UNKNOWN_REF,
    BeadRecord,
    WaveConfigError,
    WaveEnvironment,
    WaveOverride,
    WavePlan,
    declared_refs,
    load_overrides,
    plan_waves,
    resolve_scope,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The log every shared medium cites its evidence from.
_UX_LOG = REPO_ROOT / ".claude" / "development" / "BDL-UX-Issues.md"


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


def _wave(plan: WavePlan, bead_id: str) -> int:
    """The wave a bead was placed in — asserted present, so `<` compares two ints."""
    index = plan.wave_of(bead_id)
    assert index is not None, f"{bead_id} was not placed in any wave"
    return index


def _bead(
    bead_id: str, refs: str = "", blocked_by: frozenset[str] = frozenset()
) -> BeadRecord:
    return BeadRecord(
        bead_id=bead_id,
        declaration=f"work.\nrefs: {refs}" if refs else "work.",
        blocked_by=blocked_by,
    )


def _measured() -> WaveEnvironment:
    """An environment in which all three machine-observed media check out.

    Spelled once, because a test that wants to talk about the SHAPE should not
    have to restate what a clean tree looks like — and because the default
    (nothing observed) is deliberately not clean, so every shape test that wants
    exit 0 has to say who measured what.
    """
    return WaveEnvironment(
        tree_changed_paths=(),
        commit_gate=GATE_COMMIT_SCOPED,
        doc_baseline_stale_pairs=0,
    )


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """A layered index: one domain over two components, plus a shared platform.

    Deliberately layered rather than flat, because the interesting overlaps are
    containment (`payments` holds `billing`) and transit (`billing` and
    `shipping` both reach `platform`) — neither of which a two-flat-node fixture
    can express.
    """
    connection = open_db(tmp_path / "beadloom.db")
    create_schema(connection)
    _node(connection, "payments", "src/payments/", kind="domain")
    _node(connection, "billing", "src/payments/billing/", kind="component")
    _node(connection, "invoices", "src/payments/invoices/", kind="component")
    _node(connection, "shipping", "src/shipping/")
    _node(connection, "platform", "src/platform/", kind="domain")
    for path in (
        "src/payments/core.py",
        "src/payments/billing/core.py",
        "src/payments/invoices/core.py",
        "src/shipping/core.py",
        "src/platform/core.py",
    ):
        _file(connection, path)
    _edge(connection, "billing", "payments", "part_of")
    _edge(connection, "invoices", "payments", "part_of")
    _edge(connection, "billing", "platform", "depends_on")
    _edge(connection, "shipping", "platform", "depends_on")
    connection.commit()
    return connection


class TestTheFirstClauseUnderOverlapsThatAreNotEquality:
    """Two beads that share a node must never share a wave — attacked sideways."""

    @pytest.mark.parametrize(
        ("left_ref", "right_ref"),
        [("payments", "billing"), ("billing", "payments")],
    )
    def test_containment_serialises_in_either_declaration_order(
        self, conn: sqlite3.Connection, left_ref: str, right_ref: str
    ) -> None:
        """A parent scope holds its children, whichever bead names which."""
        plan = plan_waves([_bead("a", left_ref), _bead("b", right_ref)], conn=conn)
        assert [c.reason for c in plan.conflicts] == [REASON_SHARED_NODE]
        assert plan.wave_of("a") != plan.wave_of("b")

    def test_two_components_of_one_domain_share_a_wave(
        self, conn: sqlite3.Connection
    ) -> None:
        """The stated boundary: siblings own disjoint files, so they are disjoint.

        `part_of` expands DOWNWARD only. Two components of one domain therefore
        do not meet in the domain, and their file sets are disjoint under the
        most-specific-source ownership rule — so they are independent, and the
        expansion is not a proxy for "anything under one package serialises".
        """
        plan = plan_waves([_bead("a", "billing"), _bead("b", "invoices")], conn=conn)
        assert plan.conflicts == ()
        assert plan.wave_of("a") == plan.wave_of("b")

    def test_a_node_both_beads_reach_but_neither_declares_is_not_judged(
        self, conn: sqlite3.Connection
    ) -> None:
        """The stated boundary of decision 5: transit is not reach.

        `billing` and `shipping` both `depends_on` `platform`, and no bead
        declared `platform`. They share a wave. This is deliberate — on a real
        graph everything reaches infrastructure and the answer would be
        "serialise everything" — but it is the ONE way two beads that will both
        recompile against one module can legitimately run at once, so it is
        pinned here rather than left to the module docstring.
        """
        plan = plan_waves([_bead("a", "billing"), _bead("b", "shipping")], conn=conn)
        assert plan.conflicts == ()
        assert plan.wave_of("a") == plan.wave_of("b")

    def test_a_declared_dependency_between_the_two_scopes_still_serialises(
        self, conn: sqlite3.Connection
    ) -> None:
        """The other side of the same boundary: declare the intermediate and it bites."""
        plan = plan_waves([_bead("a", "billing"), _bead("b", "platform")], conn=conn)
        assert [c.reason for c in plan.conflicts] == [REASON_DEPENDENCY_EDGE]
        assert plan.conflicts[0].detail == "billing -> platform"

    def test_one_absent_ref_among_real_ones_leaves_the_whole_scope_unresolved(
        self, conn: sqlite3.Connection
    ) -> None:
        """Fail closed on the bead, not just on the name it got wrong."""
        scope = resolve_scope(conn, _bead("a", "billing, nowhere"))
        assert scope.unresolved == UNRESOLVED_UNKNOWN_REF
        assert scope.unknown_refs == ("nowhere",)
        plan = plan_waves([_bead("a", "billing, nowhere"), _bead("b", "shipping")], conn=conn)
        assert [c.reason for c in plan.conflicts] == [REASON_UNRESOLVED_SCOPE]

    def test_a_ref_that_differs_only_in_case_is_absent_rather_than_matched(
        self, conn: sqlite3.Connection
    ) -> None:
        """Node lookup is exact, so `Billing` is unknown and serialises."""
        assert resolve_scope(conn, _bead("a", "Billing")).unknown_refs == ("Billing",)

    def test_a_declaration_header_with_nothing_after_it_declares_nothing(
        self, conn: sqlite3.Connection
    ) -> None:
        """FINDING BDL-061.22-5, closed by `.80` — the separator is spaces and tabs.

        `_DECLARATION` was `\\b(?:refs?|area)\\s*:\\s*([^\\n.;]+)`. The comment above
        it said the list "ends at the first newline", and the capture did — but
        the `\\s*` between the colon and the capture matched newlines, so an empty
        `refs:` header skipped forward to the next non-empty line and read THAT as
        the declaration. Measured before the fix: `"Scope\\nrefs:\\nbilling is the
        one we mean"` resolved to `("billing",)`, and a blank line in between did
        not stop it. The separator is now `[ \\t]*`, so a dangling header ends the
        match rather than moving it.

        The harmless version of this is a bead whose adopted word is not a node:
        the scope is unresolved and it serialises, which is the fail-closed
        default. The version that costs is the one measured here — the adopted
        word IS a node, so the bead is handed a RESOLVED scope it never declared,
        and every pairwise verdict that follows rests on it. A dangling `refs:`
        left by a template is the ordinary way a bead acquires one.
        """
        assert declared_refs("Scope\nrefs:\nbilling is the one we mean\n") == ()
        adopted = BeadRecord("a", "Scope\nrefs:\nbilling is the one we mean\n")
        assert not resolve_scope(conn, adopted).resolved

    def test_a_part_of_cycle_terminates_and_still_reports_the_shared_node(
        self, conn: sqlite3.Connection
    ) -> None:
        """A malformed graph must not hang the expansion or lose the overlap."""
        _edge(conn, "payments", "billing", "part_of")
        conn.commit()
        assert resolve_scope(conn, _bead("a", "billing")).refs == {"billing", "payments",
                                                                  "invoices"}
        plan = plan_waves([_bead("a", "billing"), _bead("b", "invoices")], conn=conn)
        assert [c.reason for c in plan.conflicts] == [REASON_SHARED_NODE]


class TestTheParserRefusesRatherThanNarrows:
    """What the declaration parser does with a separator it does not accept.

    OBSERVATION BDL-061.22-A was pinned here as behaviour rather than filed as a
    defect, because the trade-off looked real in both directions: a declaration is
    written inside prose, and reading every following word as a ref id found
    nothing at all. `beadloom-mr2l.23` R1 ruled it a defect and named the repair
    the observation itself had identified — report a dropped word that IS a node
    in the graph — which has neither horn: it needs no guess at prose and it fails
    closed. `beadloom-mr2l.83` closed it.
    """

    def test_a_second_ref_after_a_semicolon_is_a_second_ref(self) -> None:
        """OBSERVATION BDL-061.22-A, first half: `;` separates a list."""
        assert declared_refs("refs: billing; shipping") == ("billing", "shipping")

    @pytest.mark.parametrize(
        ("declaration", "kept", "dropped"),
        [
            ("refs: billing shipping", ("billing",), "shipping"),
            ("refs: billing. shipping too", ("billing",), "shipping"),
        ],
    )
    def test_a_second_ref_written_without_a_comma_is_dropped_but_not_in_silence(
        self,
        conn: sqlite3.Connection,
        declaration: str,
        kept: tuple[str, ...],
        dropped: str,
    ) -> None:
        """OBSERVATION BDL-061.22-A, second half — the narrowing is now reported.

        Every other unknown in this command fails closed: no declaration and an
        absent ref both serialise the bead against everything. A ref written after
        a sentence stop or a space is still not read as a ref — that rule cannot
        change without breaking every declaration written inside prose — but the
        word is checked against the graph, and one the graph confirms is a node
        leaves the scope UNRESOLVED, which serialises the bead.
        """
        assert declared_refs(declaration) == kept
        scope = resolve_scope(conn, BeadRecord("a", declaration))
        assert scope.dropped_refs == (dropped,)
        assert not scope.resolved

    def test_a_narrowed_scope_no_longer_lets_two_beads_share_a_wave(
        self, conn: sqlite3.Connection
    ) -> None:
        """The consequence of OBSERVATION BDL-061.22-A, measured on the planner.

        Before the fix: `plan.conflicts == ()`, one wave, exit 0, and two beads
        that both declared `billing` were placed side by side with nothing said.
        """
        both = BeadRecord("a", "work.\nrefs: shipping; billing")
        plan = plan_waves([both, _bead("b", "billing")], conn=conn)
        assert plan.conflicts != ()
        assert plan.wave_of("a") != plan.wave_of("b")


class TestTheSecondClauseCannotBeSilencedWhileAWaveHoldsTwo:
    """Where a medium cannot be made independent, the wave has to say so."""

    def test_every_exported_medium_constant_is_in_the_stated_tuple(self) -> None:
        """Adding a medium name without stating it would be the silent half."""
        exported = {
            MEDIUM_WORKING_TREE,
            MEDIUM_COMMIT_GATE,
            MEDIUM_DOC_BASELINE,
            MEDIUM_TRACKER_IDS,
        }
        assert {medium.name for medium in SHARED_MEDIA} == exported
        assert len(SHARED_MEDIA) == len(exported)

    def test_every_medium_cites_an_issue_that_exists_in_the_log(self) -> None:
        """TRUE HERE IS NOT TRUE — the evidence has to resolve to a real entry."""
        log = _UX_LOG.read_text(encoding="utf-8")
        # `~~` marks a CLOSED entry, which is still an entry: the citation
        # resolves to a real observation whether or not the defect is fixed.
        # Reading only the open form made closing a cited issue delete the
        # evidence for a medium that is still shared (`beadloom-mr2l.78`).
        numbered = set(re.findall(r"^(\d+)\. (?:~~)?\[", log, flags=re.MULTILINE))
        historical = set(re.findall(r"Opened #(\d+)", log))
        known = numbered | historical
        assert known, "the UX log yielded no entries — the fixture, not the code, is wrong"
        for medium in SHARED_MEDIA:
            cited = re.findall(r"#(\d+)", medium.evidence)
            assert cited, f"{medium.name} cites no issue"
            for number in cited:
                assert number in known, f"{medium.name} cites #{number}, absent from the log"

    def test_a_serialised_neighbour_does_not_silence_a_wave_that_holds_two(
        self, conn: sqlite3.Connection
    ) -> None:
        """The media follow the WIDEST wave, so a third serialised bead adds none.

        The attack this answers: if the statement were derived from the last wave,
        or from an average, one undeclared bead pushed into its own wave would
        turn the four media off for the two that really do run together.
        """
        beads = [_bead("a", "billing"), _bead("b", "shipping"), _bead("mute")]
        plan = plan_waves(beads, conn=conn)
        assert plan.wave_of("a") == plan.wave_of("b") != plan.wave_of("mute")
        assert {m.name for m in plan.shared_media} == {m.name for m in SHARED_MEDIA}

    def test_only_a_plan_with_no_concurrency_at_all_states_no_medium(
        self, conn: sqlite3.Connection
    ) -> None:
        plan = plan_waves([_bead("a", "billing"), _bead("b", "payments")], conn=conn)
        assert all(len(wave.beads) == 1 for wave in plan.waves)
        assert plan.shared_media == ()

    def test_a_forced_parallel_wave_states_the_media_it_did_not_earn(
        self, conn: sqlite3.Connection
    ) -> None:
        """An override buys concurrency, and concurrency is what states the media."""
        override = WaveOverride(("a", "b"), "parallel", "measured", "2099-01-01")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "billing")], conn=conn, overrides=[override]
        )
        assert plan.wave_of("a") == plan.wave_of("b")
        assert {m.name for m in plan.shared_media} == {m.name for m in SHARED_MEDIA}

    def test_a_bead_whose_scope_is_unknown_still_names_itself_when_forced_parallel(
        self, conn: sqlite3.Connection
    ) -> None:
        """An override can put an undeclared bead in a wave; the finding survives it.

        This is the load-bearing interaction between the two mechanisms: a human
        may outrank the computed decision, but the reason the decision was taken
        is reported from the SCOPES, not from the conflict set, so overriding the
        conflict away does not also delete the sentence that said why it existed.
        """
        override = WaveOverride(("a", "mute"), "parallel", "measured", "2099-01-01")
        plan = plan_waves([_bead("a", "billing"), _bead("mute")], conn=conn,
                          overrides=[override])
        assert plan.wave_of("a") == plan.wave_of("mute")
        assert plan.exit_code == 1
        assert any("unresolved_scope: mute" in finding for finding in plan.findings)

    def test_every_wave_that_holds_more_than_one_bead_names_one_gate_owner(
        self, conn: sqlite3.Connection
    ) -> None:
        """One bead per wave measures the combined outcome — not zero, not two."""
        beads = [
            _bead("a", "billing"),
            _bead("b", "shipping"),
            _bead("c", "invoices"),
            _bead("d", "payments"),
        ]
        plan = plan_waves(beads, conn=conn)
        wide = [wave for wave in plan.waves if len(wave.beads) > 1]
        assert wide, "the fixture produced no concurrent wave — nothing was tested"
        for wave in plan.waves:
            assert wave.gate_owner in wave.beads


class TestTheOverridePathIsRecordedRatherThanSilent:
    """CONTEXT: an override is an exclusion with a reason and an exit condition."""

    def test_an_override_with_no_reason_at_all_is_a_configuration_error(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "waves:\n  overrides:\n  - beads: [a, b]\n    decision: parallel\n"
            "    reason: ''\n    until: '2099-01-01'\n",
            encoding="utf-8",
        )
        with pytest.raises(WaveConfigError, match="reason"):
            load_overrides(tmp_path)

    def test_a_reason_of_only_whitespace_is_a_configuration_error(
        self, tmp_path: Path
    ) -> None:
        """FINDING BDL-061.22-3, closed by `.80` — the check reads content, not presence.

        `config.py` rejected a missing key with `not entry.get(key)`, which catches
        `''` and `null` and passed `'   '`. The value was then `.strip()`ped to
        `''`, so the loader returned an override whose reason was empty and whose
        `until` was empty — and an empty `until` has no deadline, so
        `WaveOverride.expired` was False forever. The error message the loader
        would have printed names this exact outcome: "an unnamed, undated override
        outranks the graph permanently by accident". Measured before the fix: the
        override loaded, and `beadloom waves` rendered it as `(until )`.

        This was `.49`'s shape on a third surface — an exit condition that is
        present in the file and absent in effect.
        """
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "waves:\n  overrides:\n  - beads: [a, b]\n    decision: parallel\n"
            "    reason: '   '\n    until: '  '\n",
            encoding="utf-8",
        )
        with pytest.raises(WaveConfigError):
            load_overrides(tmp_path)

    @pytest.mark.parametrize(
        ("body", "fragment"),
        [
            ("waves: []\n", "'waves' must be a mapping"),
            # One override written without its list dash — a realistic slip.
            (
                "waves:\n  overrides:\n    beads: [a, b]\n    decision: parallel\n"
                "    reason: measured\n    until: '2099-01-01'\n",
                "waves.overrides must be a list",
            ),
            ("waves:\n  overrides:\n  - just a string\n", "must be mappings"),
            (
                "waves:\n  overrides:\n  - beads: 'a,b'\n    decision: parallel\n"
                "    reason: measured\n    until: '2099-01-01'\n",
                "must be a list of bead ids",
            ),
            (
                "waves:\n  overrides:\n  - beads: [a, 7]\n    decision: parallel\n"
                "    reason: measured\n    until: '2099-01-01'\n",
                "must be a list of bead ids",
            ),
            ("- not a mapping at all\n", "top level must be a mapping"),
            ("waves:\n  overrides:\n  - [\n", "could not be read as declared"),
        ],
    )
    def test_a_waves_block_that_is_not_the_declared_shape_is_an_error(
        self, tmp_path: Path, body: str, fragment: str
    ) -> None:
        """Every malformed shape reaches the caller as one fact it can act on.

        The command turns `WaveConfigError` into exit 2 — "no shape could be
        decided" — so a shape that fell through to a `TypeError` or to a lenient
        default would be the difference between an undecidable answer and a wrong
        one. Parametrised over the seven ways the block can be misdeclared, each
        asserting the message names WHICH one.
        """
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(body, encoding="utf-8")
        with pytest.raises(WaveConfigError, match=re.escape(fragment)):
            load_overrides(tmp_path)

    def test_a_flow_file_in_another_codec_is_a_declaration_error_not_a_traceback(
        self, tmp_path: Path
    ) -> None:
        """An unreadable declaration and an unparseable one are one fact here."""
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_bytes(b"waves:\n  overrides: \xff\xfe\n")
        with pytest.raises(WaveConfigError, match="could not be read as declared"):
            load_overrides(tmp_path)

    def test_an_expired_override_still_applies_and_the_finding_says_so(
        self, conn: sqlite3.Connection
    ) -> None:
        """Reported, not enforced — and the two are different claims.

        The override keeps working past its exit condition. That is a deliberate
        choice (a plan that silently reshaped itself on a date boundary would be
        worse), so what the test holds is that the shape it bought is still
        visible AND that the finding states both halves: past its date, and still
        in force.
        """
        override = WaveOverride(("a", "b"), "parallel", "measured", "2020-01-01")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "billing")],
            conn=conn,
            overrides=[override],
            today=date(2026, 8, 24),
        )
        assert plan.wave_of("a") == plan.wave_of("b")
        assert plan.exit_code == 1
        expired = [f for f in plan.findings if "expired_override" in f]
        assert len(expired) == 1
        assert "2020-01-01" in expired[0]
        assert "still applies" in expired[0]

    def test_an_override_expiring_today_still_covers_today(
        self, conn: sqlite3.Connection
    ) -> None:
        """The deadline names the LAST day covered — an off-by-one worth pinning."""
        override = WaveOverride(("a", "b"), "parallel", "measured", "2026-08-24")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "billing")],
            conn=conn,
            overrides=[override],
            today=date(2026, 8, 24),
        )
        assert not plan.overrides[0].expired

    def test_a_parallel_override_cannot_outrank_the_trackers_own_ordering(
        self, conn: sqlite3.Connection
    ) -> None:
        """A blocked bead stays behind its blocker whatever the override says.

        This is the right behaviour and it is asserted first, because the defect
        below is only about how it is REPORTED.
        """
        beads = [_bead("a", "billing"), _bead("b", "shipping", frozenset({"a"}))]
        override = WaveOverride(("a", "b"), "parallel", "measured", "2099-01-01")
        with_override = plan_waves(beads, conn=conn, overrides=[override])
        without = plan_waves(beads, conn=conn)
        assert _wave(with_override, "a") < _wave(with_override, "b")
        assert [w.beads for w in with_override.waves] == [w.beads for w in without.waves]

    def test_an_override_the_tracker_overrules_is_reported_inert(
        self, conn: sqlite3.Connection
    ) -> None:
        """FINDING BDL-061.22-1, closed by `.80` — `changed` counts shape changes.

        `_apply_overrides` deleted the `blocked_by_bead` conflict and counted one
        change. `_assign` then placed the blocked bead after its blocker anyway,
        via `_earliest_wave`, which reads the blockers directly. Measured before
        the fix: the wave shape was identical with and without the override, and
        it was reported as `changed 1 decision(s)`, was not `inert`, and raised no
        finding. `changed` is now the number of pairs whose co-wave status differs
        between the shape as planned and the shape with this override removed.

        `OverrideOutcome.inert` exists because "an override nobody can see doing
        anything is how a check gets switched off without anybody saying so" —
        and this was one nobody could see doing anything. It is `.48`'s dead-entry
        shape, arriving through the arithmetic rather than through the absence.
        """
        beads = [_bead("a", "billing"), _bead("b", "shipping", frozenset({"a"}))]
        override = WaveOverride(("a", "b"), "parallel", "measured", "2099-01-01")
        plan = plan_waves(beads, conn=conn, overrides=[override])
        assert plan.overrides[0].inert
        assert any("inert_override" in finding for finding in plan.findings)

    def test_a_parallel_override_naming_absent_beads_is_reported_inert(
        self, conn: sqlite3.Connection
    ) -> None:
        """One direction of "an override that overrides nothing" is caught."""
        override = WaveOverride(("gone", "vanished"), "parallel", "measured", "2099-01-01")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "shipping")], conn=conn, overrides=[override]
        )
        assert plan.overrides[0].inert
        assert any("inert_override" in finding for finding in plan.findings)

    def test_a_serial_override_naming_absent_beads_is_reported_inert(
        self, conn: sqlite3.Connection
    ) -> None:
        """FINDING BDL-061.22-2, closed by `.80` — the dead override, caught both ways.

        A `parallel` override about beads the plan does not contain finds no
        conflict to delete, counts zero, and was already correctly reported inert.
        A `serial` one about the same absent beads found no conflict either — and
        CREATED one, counted it, and was reported as having changed a decision.
        Measured before the fix: the plan's `conflicts` then carried a pair nobody
        asked about, and `beadloom waves` printed it under "Serialised because:"
        beside the real serialisations, where a reader cannot tell the two apart.
        An override now speaks only about pairs the plan actually contains.

        A stale override left behind after its beads closed is the ordinary way
        this happens, which is exactly the entry `.48` had to learn to report.
        """
        override = WaveOverride(("gone", "vanished"), "serial", "measured", "2099-01-01")
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "shipping")], conn=conn, overrides=[override]
        )
        assert plan.overrides[0].inert
        assert not any(
            conflict.left == "gone" or conflict.right == "vanished"
            for conflict in plan.conflicts
        )


class TestThisSessionsOwnWaveFailuresReplayed:
    """The strongest available evidence: waves that already went wrong here."""

    def test_bdlux_181_four_independent_beads_get_one_named_tree_gate(
        self, conn: sqlite3.Connection
    ) -> None:
        """#181: four agents green in clean rooms, the combined tree red.

        The fix `.21` shipped is not prevention — nothing stops four beads from
        sharing a tree — it is that the combined run stops being "in nobody's
        bead". So what is checked is that a four-bead wave produces exactly one
        wave, exactly one gate owner, and a working-tree statement that
        distinguishes the two claims #181 says were reported with one word.

        `.80` added the half `.22` found missing: the same plan without a measured
        environment does not reach exit 0 at all. The two runs below are the same
        four beads, and the only difference between them is whether anybody looked
        at the tree.
        """
        _node(conn, "reporting", "src/reporting/")
        _file(conn, "src/reporting/core.py")
        conn.commit()
        beads = [
            _bead("d1", "billing"),
            _bead("d2", "shipping"),
            _bead("d3", "invoices"),
            _bead("d4", "reporting"),
        ]
        plan = plan_waves(beads, conn=conn, environment=_measured())
        assert len(plan.waves) == 1
        assert plan.waves[0].beads == ("d1", "d2", "d3", "d4")
        assert plan.waves[0].gate_owner in plan.waves[0].beads
        assert plan.exit_code == 0
        tree = next(m for m in plan.shared_media if m.name == MEDIUM_WORKING_TREE)
        assert "clean room" in tree.statement
        assert tree.evidence == "BDL-UX #181"

        unmeasured = plan_waves(beads, conn=conn)
        assert unmeasured.exit_code == 1
        assert any(
            f.startswith(f"medium_unmeasured: {MEDIUM_WORKING_TREE}")
            for f in unmeasured.findings
        )

    def test_bdlux_181_the_gate_owner_is_the_same_bead_on_every_recomputation(
        self, conn: sqlite3.Connection
    ) -> None:
        """Two agents reading the plan must find the same bead holding the gate."""
        beads = [_bead("d3", "invoices"), _bead("d1", "billing"), _bead("d2", "shipping")]
        first = plan_waves(beads, conn=conn)
        second = plan_waves(list(reversed(beads)), conn=conn)
        assert [w.gate_owner for w in first.waves] == [w.gate_owner for w in second.waves]

    def test_bdlux_171_a_valid_but_unintended_edge_is_honoured_without_a_finding(
        self, conn: sqlite3.Connection
    ) -> None:
        """#171: the mis-wired edge is well-formed, so the shape it buys is too.

        `waves` reads `blocked_by` from the tracker and reproduces it exactly. In
        #171 the coordinator wired a Windows-CI bead to depend on the S2 core:
        every id existed, the graph stayed acyclic, and nothing was malformed to
        reject. Replayed here, `waves` serialises the wrong pair, reports
        `blocked_by_bead` as the reason, and raises no finding — because there is
        nothing about the edge it could disagree with.

        What the command DOES hold and does not use: the bead's own title, read
        into the declaration by the CLI. Comparing the id written in the title
        against the id the tracker allocated is the check that would have caught
        #171 mechanically, and it is not made. The only thing said about the id
        space is the `tracker-ids` medium, which is prose.
        """
        wrong = [_bead("ci-bead", "shipping", frozenset({"core-bead"})),
                 _bead("core-bead", "billing")]
        plan = plan_waves(wrong, conn=conn)
        assert [c.reason for c in plan.conflicts] == [REASON_BLOCKED_BY_BEAD]
        assert _wave(plan, "core-bead") < _wave(plan, "ci-bead")
        assert plan.findings == ()
        assert plan.exit_code == 0

    def test_bdlux_171_serialising_the_pair_also_withdraws_the_id_space_caution(
        self, conn: sqlite3.Connection
    ) -> None:
        """OBSERVATION BDL-061.22-B — the medium is stated only under concurrency.

        `media_for` returns nothing for a wave of one, on the reasoning that a
        wave of one shares nothing with anybody. For three of the four media that
        holds. It does not hold for `tracker-ids`: #171's mis-wiring happened at
        bead CREATION, before any wave ran, and a plan that serialises the beads
        it mis-wired is exactly the plan whose ids most need checking. The
        caution is withdrawn by the failure it describes.

        The counter-argument is not weak: a command that decides concurrency
        should state what concurrency costs, and printing a creation-time caution
        on a fully serial plan is scope creep. `.23` is where that is ruled on.
        """
        wrong = [_bead("ci-bead", "shipping", frozenset({"core-bead"})),
                 _bead("core-bead", "billing")]
        plan = plan_waves(wrong, conn=conn)
        assert all(len(wave.beads) == 1 for wave in plan.waves)
        assert MEDIUM_TRACKER_IDS not in {medium.name for medium in plan.shared_media}
        assert plan.shared_media == ()

    def test_the_two_beads_this_session_ran_concurrently_would_have_been_serialised(
        self, conn: sqlite3.Connection
    ) -> None:
        """The dogfood case: neither `.21` nor `.72` declared what it occupied.

        Both were launched into one wave by the coordinator. Replayed as records
        with the declarations those beads actually carried — none — the command
        refuses the wave, at exit 1, naming the remedy for each bead separately
        rather than once for the pair.
        """
        plan = plan_waves([_bead("mr2l.21"), _bead("mr2l.72")], conn=conn)
        assert plan.wave_of("mr2l.21") != plan.wave_of("mr2l.72")
        assert plan.exit_code == 1
        assert len([f for f in plan.findings if f.startswith("unresolved_scope")]) == 2
        assert plan.shared_media == ()


def _hook_scope_block() -> str:
    """The commit-scope block from the shipped hook, read rather than retyped.

    Retyping the two lines would test a copy of the hook, which is the "TRUE
    HERE IS NOT TRUE" failure: the copy stays green while the hook drifts.
    """
    from beadloom.services.commands.docsync import _HOOK_COMMIT_SCOPE

    return _HOOK_COMMIT_SCOPE


def _git(project: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=project,
        check=True,
        capture_output=True,
    )


def _repo_with_one_committed_module(tmp_path: Path) -> Path:
    project = tmp_path / "shared-tree"
    project.mkdir()
    _git(project, "init", "-q", "-b", "main")
    _git(project, "config", "user.email", "t@example.invalid")
    _git(project, "config", "user.name", "t")
    (project / "src").mkdir()
    (project / "src" / "shared.py").write_text("mine = 1\ntheirs = 1\n", encoding="utf-8")
    (project / "src" / "other.py").write_text("other = 1\n", encoding="utf-8")
    _git(project, "add", "-A")
    _git(project, "commit", "-qm", "init")
    return project


def _run_scope_block(project: Path) -> dict[str, str]:
    """Run the hook's own scope block and report the two variables it sets."""
    script = _hook_scope_block() + '\nprintf "%s\\n" "$outside"\nprintf "%s\\n" "$staged_py"\n'
    result = subprocess.run(  # noqa: S603
        ["sh", "-c", script],  # noqa: S607
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = result.stdout.splitlines()
    return {"outside": lines[0] if lines else "", "staged_py": "\n".join(lines[1:]).strip()}


class TestTheCommitGateAndTheHunkItCannotSee:
    """BDL-UX #118's fix, measured against the collision it exists to prevent."""

    def test_a_neighbours_unstaged_edit_is_counted_as_not_judged(
        self, tmp_path: Path
    ) -> None:
        """The number next to the verdict is what makes the narrowing honest."""
        project = _repo_with_one_committed_module(tmp_path)
        (project / "src" / "shared.py").write_text("mine = 2\ntheirs = 1\n", encoding="utf-8")
        (project / "src" / "other.py").write_text("other = 2\n", encoding="utf-8")
        _git(project, "add", "src/shared.py")
        answer = _run_scope_block(project)
        assert answer["outside"] == "1"
        assert answer["staged_py"] == "src/shared.py"

    def test_a_clean_neighbour_leaves_nothing_unjudged(self, tmp_path: Path) -> None:
        """The count is a measurement, not a constant — zero has to be reachable."""
        project = _repo_with_one_committed_module(tmp_path)
        (project / "src" / "shared.py").write_text("mine = 2\ntheirs = 1\n", encoding="utf-8")
        _git(project, "add", "src/shared.py")
        assert _run_scope_block(project)["outside"] == "0"

    def test_a_neighbours_hunk_swept_into_a_staged_file_reads_as_this_commits_work(
        self, tmp_path: Path
    ) -> None:
        """OBSERVATION BDL-061.22-C — the gate narrows scope, not authorship.

        This is the concrete failure two agents hit in this session: `git add -p`
        is unavailable to an agent, so committing one's own change to a file a
        neighbour is also editing stages the neighbour's hunk too. Measured on
        the hook's own scope block: `outside` reads 0 and `staged_py` names the
        file, so the hook prints a confident "0 modified file(s) outside this
        commit were not judged" over a commit that contains someone else's work.

        The gate would NOT have caught it, and cannot: the swept hunk is inside
        the commit, which is precisely the region the gate judges. What is
        available at this layer is a different check — comparing the staged diff
        against the paths the committer declared — and that is a wave-protocol
        question rather than a hook one.
        """
        project = _repo_with_one_committed_module(tmp_path)
        (project / "src" / "shared.py").write_text("mine = 2\ntheirs = 2\n", encoding="utf-8")
        _git(project, "add", "src/shared.py")
        answer = _run_scope_block(project)
        assert answer["outside"] == "0"
        assert answer["staged_py"] == "src/shared.py"

    def test_a_neighbours_untracked_module_is_counted_as_not_judged(
        self, tmp_path: Path
    ) -> None:
        """FINDING BDL-061.22-4, closed by `.80` — A GREEN COUNT IS NOT A CHECKED COUNT.

        `outside=$(git diff --name-only | wc -l)` listed tracked files with
        unstaged modifications. A neighbouring agent's brand-new module is
        untracked, so it was not listed. Measured before the fix: with one tracked
        neighbour edit and one untracked neighbour module present, the hook
        reported 1.

        The word the hook printed was "modified", and an untracked file is
        literally not modified — so the line was not a lie. But the line exists to
        state the unjudged remainder, and a new module is the largest unjudged
        thing a neighbour can leave in a shared tree. `git status --porcelain`
        answers both in one call, and is what the hook now reads.
        """
        project = _repo_with_one_committed_module(tmp_path)
        (project / "src" / "shared.py").write_text("mine = 2\ntheirs = 1\n", encoding="utf-8")
        (project / "src" / "other.py").write_text("other = 2\n", encoding="utf-8")
        (project / "src" / "neighbour_new.py").write_text("new = 1\n", encoding="utf-8")
        _git(project, "add", "src/shared.py")
        assert _run_scope_block(project)["outside"] == "2"


#: The five findings this module pinned. `.80` closed all five, so each pin is
#: now a regression test rather than an expected failure — but the id must
#: survive the transition, or a closed finding becomes a test nobody can trace
#: back to the defect it was written for.
CLOSED_FINDINGS: tuple[str, ...] = tuple(f"FINDING BDL-061.22-{n}" for n in range(1, 6))


def _test_functions() -> list[tuple[str, Any]]:
    """Every test function this module defines, with its owning class's name."""
    import inspect
    import sys

    module = sys.modules[__name__]
    found: list[tuple[str, Any]] = []
    for _, klass in inspect.getmembers(module, inspect.isclass):
        if not klass.__name__.startswith("Test"):
            continue
        found.extend(inspect.getmembers(klass, inspect.isfunction))
    return found


class TestEveryFindingHereIsStrictAndNamesItself:
    """The meta-check `.18` introduced, carried through the transition `.80` made.

    A strict xfail turns red the moment the defect is fixed, which is what makes
    it a finding rather than a habit. That property has a consequence nobody
    stated until `.80` had to act on it: closing the finding means REMOVING the
    marker, and a module that removes its last marker also loses the only record
    that the finding ever existed. So the meta-check now asserts two things — any
    marker still here is strict and cites a finding, and every finding this module
    ever pinned is still named by a test that now passes.
    """

    def test_every_xfail_in_this_module_is_strict_and_cites_a_finding(self) -> None:
        for name, function in _test_functions():
            for mark in getattr(function, "pytestmark", []):
                if mark.name != "xfail":
                    continue
                assert mark.kwargs.get("strict") is True, f"{name}: xfail is not strict"
                assert "FINDING BDL-061.22-" in mark.kwargs.get("reason", ""), name

    @pytest.mark.parametrize("finding", CLOSED_FINDINGS)
    def test_every_closed_finding_is_still_named_by_a_passing_test(
        self, finding: str
    ) -> None:
        """The finding id outlives its marker, and the test that owns it passes."""
        owners = [
            (name, function)
            for name, function in _test_functions()
            if finding in (function.__doc__ or "")
        ]
        assert owners, f"{finding} is named by no test — it cannot be traced"
        for name, function in owners:
            marks = [m.name for m in getattr(function, "pytestmark", [])]
            assert "xfail" not in marks, f"{name}: {finding} is claimed closed but is xfail"
