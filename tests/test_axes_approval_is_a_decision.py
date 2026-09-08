"""BDL-068 S6 / BDL-UX #250, #245 — what the approval list is, and what it is not.

**#250: provenance is not consent.** ``WorkItemAxes.approved`` was
``kept | targets``: every node owning a file the ``Derived by`` field names was
inside the approval whatever its row said. The rule held while a slice CHANGED
what it derived from, which was true of S1 through S4. S5's subject is where this
project calls ``bd``, so its derivation targets include files it only reads, and
``doc-spaces`` and ``intent-reader`` sat in BDL-068's approved set with rows that
say ``no``. Measured on this repository before the fix: 39 approved nodes, two of
them ruled out by their own row.

**#245: the approval is a CEILING, not a per-bead scope.** A work item's axes are
the UNION of its slices'; a bead's scope is a SUBSET chosen for that bead. The
``unguarded_axis`` remedy told its reader to generate every bead's ``refs:`` from
the work item's section, and ``beadloom axes --refs`` renders that section as one
line for the whole work item — 24 nodes when the entry was filed, 52 today. Every
bead would then declare every node, ``shared_node`` would fire on every pair, and
every wave would collapse to a wave of one. The remedy would switch off the
parallelism the command exists to plan.

The collapse is held here as an executable consequence rather than as prose, so
the sentence cannot be written back without a number moving.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.waves import (
    AXIS_RULED_OUT,
    AXIS_SWEPT_UNDECIDED,
    GATE_COMMIT_SCOPED,
    BeadRecord,
    BeadScope,
    Wave,
    WaveEnvironment,
    WorkItemAxes,
    compare_declarations,
    derivation_findings,
    plan_waves,
    unguarded_axes,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """A small real index: three disjoint features, one file each."""
    connection = open_db(tmp_path / "beadloom.db")
    create_schema(connection)
    for ref in ("billing", "shipping", "invoicing"):
        connection.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref, "feature", ref, f"src/{ref}/"),
        )
        connection.execute(
            "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
            (f"src/{ref}/core.py", f"h-{ref}", "code", "2026-08-24T00:00:00Z"),
        )
    connection.commit()
    return connection


def _bead(bead_id: str, refs: str) -> BeadRecord:
    return BeadRecord(bead_id=bead_id, declaration=f"work.\nrefs: {refs}")


#: A machine whose shared media were measured and are clean, so a concurrent
#: wave in these cases is decided by the node scopes and by nothing else.
_CLEAN = WaveEnvironment(
    tree_changed_paths=(),
    commit_gate=GATE_COMMIT_SCOPED,
    doc_baseline_stale_pairs=0,
    landing_lock_sites=(),
)

_APPROVING = WorkItemAxes(
    work_item="KEY-1",
    document="docs/KEY-1/RFC.md",
    seed="none",
    kept=frozenset({"billing", "shipping", "invoicing"}),
)


def _scope(bead: str, *declared: str) -> BeadScope:
    return BeadScope(
        bead_id=bead,
        refs=frozenset(declared),
        files=frozenset(),
        declared=declared,
    )


class TestApprovalFollowsTheScopeDecision:
    """#250 — a node reaches the approval list because a row decided it."""

    def test_a_swept_target_is_not_approved_by_having_been_swept(self) -> None:
        axes = WorkItemAxes(
            kept=frozenset({"billing"}), targets=frozenset({"shipping"})
        )

        assert axes.approved == frozenset({"billing"})

    def test_a_target_a_row_rules_out_is_not_approved(self) -> None:
        axes = WorkItemAxes(
            kept=frozenset({"billing"}),
            targets=frozenset({"shipping"}),
            ruled_out=frozenset({"shipping"}),
        )

        assert "shipping" not in axes.approved

    def test_declaring_a_ruled_out_target_is_a_finding_rather_than_agreement(self) -> None:
        """The measured shape: `doc-spaces` and `intent-reader` in BDL-068."""
        axes = WorkItemAxes(
            work_item="KEY-1",
            document="docs/KEY-1/RFC.md",
            kept=frozenset({"billing"}),
            targets=frozenset({"shipping"}),
            ruled_out=frozenset({"shipping"}),
        )

        agreements = compare_declarations([_scope("a", "shipping")], axes)

        assert [agreement.verdict for agreement in agreements] == [AXIS_RULED_OUT]

    def test_a_swept_target_no_row_names_is_swept_and_not_decided(self) -> None:
        """Honest, and different from approval: the table never ruled on it.

        And different from `not_derived`, which would be false — the derivation
        reached it, which is why its absence from the table is worth saying.
        """
        axes = WorkItemAxes(
            work_item="KEY-1",
            document="docs/KEY-1/RFC.md",
            kept=frozenset({"billing"}),
            targets=frozenset({"shipping"}),
        )

        agreements = compare_declarations([_scope("a", "shipping")], axes)

        assert [agreement.verdict for agreement in agreements] == [
            AXIS_SWEPT_UNDECIDED
        ]


class TestTheRemedyDoesNotCollapseTheWaves:
    """#245 — following the remedy must not serialise the plan it is printed on."""

    def test_the_work_item_union_given_to_every_bead_collapses_every_wave(
        self, conn: sqlite3.Connection
    ) -> None:
        """The consequence of the old remedy, run through the real planner.

        Three beads, each given the work item's whole approved set exactly as
        `beadloom axes --refs` renders it: every pair shares a node, so the plan
        is three waves of one.
        """
        union = "billing, shipping, invoicing"
        records = [_bead(name, union) for name in ("alpha", "beta", "gamma")]

        plan = plan_waves(records, conn=conn, axes=_APPROVING, environment=_CLEAN)

        assert [len(wave.beads) for wave in plan.waves] == [1, 1, 1]

    def test_a_subset_per_bead_leaves_the_same_three_beads_in_one_wave(
        self, conn: sqlite3.Connection
    ) -> None:
        """The same three beads, each declaring only the node it occupies."""
        records = [
            _bead("alpha", "billing"),
            _bead("beta", "shipping"),
            _bead("gamma", "invoicing"),
        ]

        plan = plan_waves(records, conn=conn, axes=_APPROVING, environment=_CLEAN)

        assert [len(wave.beads) for wave in plan.waves] == [3]

    def test_the_finding_sends_the_reader_to_a_per_bead_derivation(self) -> None:
        axes = WorkItemAxes(
            work_item="KEY-1",
            document="docs/KEY-1/RFC.md",
            kept=frozenset({"billing", "shipping", "invoicing"}),
        )
        waves = [Wave(index=1, beads=("alpha", "beta"), gate_owner="beta")]
        scopes = [_scope("alpha", "billing"), _scope("beta", "shipping")]

        gaps = unguarded_axes(waves, scopes, axes)
        findings = derivation_findings(waves, (), gaps, axes)

        assert len(findings) == 1
        message = findings[0]
        assert "beadloom impact" in message
        assert "union" in message

    def test_the_finding_does_not_prescribe_the_work_item_wide_refs_line(self) -> None:
        """The sentence that would collapse the plan it is printed on."""
        axes = WorkItemAxes(
            work_item="KEY-1",
            document="docs/KEY-1/RFC.md",
            kept=frozenset({"billing", "shipping", "invoicing"}),
        )
        waves = [Wave(index=1, beads=("alpha", "beta"), gate_owner="beta")]
        scopes = [_scope("alpha", "billing"), _scope("beta", "shipping")]

        findings = derivation_findings(
            waves, (), unguarded_axes(waves, scopes, axes), axes
        )

        assert "generate each bead's `refs:` from the `## Axes` section" not in findings[0]
