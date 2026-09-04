"""BDL-061.80 — the second clause of the wave guarantee, made able to fail.

`.21` stated the guarantee in two clauses and `.22` measured that only the first
one was enforced: the four shared media were a constant tuple with a deterministic
gate owner, and nothing checked that the tree was measured, that the gate ran
scoped, that the baseline was reconciled, or that a tracker id matched the id in
its title. This module covers the half that was prose.

What is checked here is a PRECONDITION per medium, and the tests are written to
say so: each one names what was observed, and the ``unmeasured`` cases exist
because "nobody looked" and "looked and it was fine" must not print with one word.
The conduct of the wave AFTER it is planned is not covered, here or anywhere —
`beadloom.application.waves.__init__` names that split.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.waves import (
    GATE_ABSENT,
    GATE_COMMIT_SCOPED,
    GATE_WHOLE_TREE,
    MEDIUM_COMMIT_GATE,
    MEDIUM_DOC_BASELINE,
    MEDIUM_LANDING_ORDER,
    MEDIUM_TRACKER_IDS,
    MEDIUM_WORKING_TREE,
    SHARED_MEDIA,
    STATUS_FAILED,
    STATUS_NOT_APPLICABLE,
    STATUS_PASSED,
    STATUS_UNMEASURED,
    BeadRecord,
    LockSite,
    MediumCheck,
    WaveEnvironment,
    WorkItemAxes,
    check_media,
    finding_for,
    lock_sites,
    plan_waves,
    title_id_mismatches,
)
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.bd_seam.assumptions import lock_invocations
from beadloom.services.bd_seam.invocations import text_invocations

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _lock_sites(sources: list[tuple[str, str]]) -> tuple[LockSite, ...]:
    """Judge the lock instructions in *sources*, through the one shared grammar.

    `beadloom-0mdo.51` moved the grammar to the seam and left the judgement here,
    so a test that starts from TEXT composes the two the same way the services
    edge does. Composing them here rather than mocking keeps these tests over the
    real path.
    """
    return lock_sites(lock_invocations(text_invocations(sources)))


CLEAN = WaveEnvironment(
    tree_changed_paths=(),
    commit_gate=GATE_COMMIT_SCOPED,
    doc_baseline_stale_pairs=0,
    landing_lock_sites=(),
)

#: One instruction of the landing lock in the form that grants nothing — the
#: form four of this project's own five sites carried until BDL-068 S5.
GRANTS_NOTHING = _lock_sites([("a.md", "bd merge-slot acquire --wait\n")])


def _approving(*nodes: str) -> WorkItemAxes:
    """A recorded derivation keeping exactly *nodes* in scope.

    Supplied wherever a case asserts a CLEAN plan, because a concurrent wave
    whose declarations were held against no derivation is a finding — the same
    rule, and for the same reason, as a shared medium nobody measured. And it
    keeps exactly the nodes the case's beads declare, because a work item
    approving a node no bead of a wave names is the OTHER finding (BDL-UX #232).
    """
    return WorkItemAxes(
        work_item="KEY-1",
        document="docs/KEY-1/RFC.md",
        seed="none",
        kept=frozenset(nodes),
    )


def _bead(bead_id: str, refs: str = "", title: str = "") -> BeadRecord:
    return BeadRecord(
        bead_id=bead_id,
        declaration=f"work.\nrefs: {refs}" if refs else "work.",
        title=title,
    )


def _check(checks: tuple[MediumCheck, ...], medium: str) -> MediumCheck:
    return next(check for check in checks if check.medium == medium)


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = open_db(tmp_path / "beadloom.db")
    create_schema(connection)
    for ref in ("billing", "shipping"):
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


class TestEveryMediumHasACheckThatCanFail:
    """The answer to `.22`'s headline: a verdict per medium, none of them constant."""

    def test_every_stated_medium_is_also_checked(self) -> None:
        """A medium stated and not checked is exactly the defect `.80` closed."""
        checks = check_media([_bead("a")], environment=CLEAN)
        assert {c.medium for c in checks} == {m.name for m in SHARED_MEDIA}

    @pytest.mark.parametrize(
        ("medium", "broken"),
        [
            (
                MEDIUM_WORKING_TREE,
                WaveEnvironment(
                    tree_changed_paths=("src/elsewhere.py",),
                    commit_gate=GATE_COMMIT_SCOPED,
                    doc_baseline_stale_pairs=0,
                    landing_lock_sites=(),
                ),
            ),
            (
                MEDIUM_COMMIT_GATE,
                WaveEnvironment(
                    tree_changed_paths=(),
                    commit_gate=GATE_WHOLE_TREE,
                    doc_baseline_stale_pairs=0,
                    landing_lock_sites=(),
                ),
            ),
            (
                MEDIUM_DOC_BASELINE,
                WaveEnvironment(
                    tree_changed_paths=(),
                    commit_gate=GATE_COMMIT_SCOPED,
                    doc_baseline_stale_pairs=3,
                    landing_lock_sites=(),
                ),
            ),
            (
                MEDIUM_LANDING_ORDER,
                WaveEnvironment(
                    tree_changed_paths=(),
                    commit_gate=GATE_COMMIT_SCOPED,
                    doc_baseline_stale_pairs=0,
                    landing_lock_sites=GRANTS_NOTHING,
                ),
            ),
        ],
    )
    def test_each_machine_observed_medium_can_come_back_failed(
        self, medium: str, broken: WaveEnvironment
    ) -> None:
        """One observation per medium is enough to redden it, and only it."""
        checks = check_media([_bead("a")], environment=broken)
        assert _check(checks, medium).status == STATUS_FAILED
        others = [c for c in checks if c.medium != medium]
        assert all(c.status == STATUS_PASSED for c in others)

    @pytest.mark.parametrize(
        "medium",
        [
            MEDIUM_WORKING_TREE,
            MEDIUM_COMMIT_GATE,
            MEDIUM_DOC_BASELINE,
            MEDIUM_LANDING_ORDER,
        ],
    )
    def test_a_medium_nobody_observed_is_unmeasured_rather_than_passed(
        self, medium: str
    ) -> None:
        """UNKNOWN IS NOT ZERO, applied to the media themselves."""
        checks = check_media([_bead("a")])
        assert _check(checks, medium).status == STATUS_UNMEASURED
        assert _check(checks, medium).is_finding

    def test_a_serial_plan_checks_the_between_bead_media_too(self) -> None:
        """BDL-UX #228 — the counter-claim this test replaces.

        It used to assert `not_applicable` for the three media that carry state
        between beads whenever no wave held two of them, on the reasoning that
        nothing is carried between beads there. The reasoning read the width of
        ONE plan as solitude: `_check_working_tree` fails on paths owned by no
        bead in the plan, which is this module already knowing that work from
        outside the plan lands in the same tree, under the same hook, against the
        same doc baseline.
        """
        checks = check_media([_bead("a")], environment=CLEAN)
        for medium in (
            MEDIUM_WORKING_TREE,
            MEDIUM_COMMIT_GATE,
            MEDIUM_DOC_BASELINE,
            MEDIUM_LANDING_ORDER,
        ):
            assert _check(checks, medium).status != STATUS_NOT_APPLICABLE
            assert not _check(checks, medium).is_finding

    def test_no_verdict_is_ever_not_applicable(self) -> None:
        """No medium can be switched off by the shape of the plan (#228)."""
        for environment in (None, CLEAN):
            checks = check_media([_bead("a")], environment=environment)
            assert all(check.status != STATUS_NOT_APPLICABLE for check in checks)

    def test_a_serial_plan_still_checks_the_id_space(self) -> None:
        """OBSERVATION `.22`-B, first answered on the check alone.

        The mis-wiring in #171 happened at bead creation, before any wave ran, so
        a plan that serialises the beads it mis-wired is exactly the plan whose
        ids most need checking. `.80` made this one check unconditional while the
        statement stayed conditional; #228 made every other check unconditional
        too, so this is no longer the exception it was written as.
        """
        checks = check_media([_bead("proj.41", title="[BDL-061.39] work")])
        assert _check(checks, MEDIUM_TRACKER_IDS).status == STATUS_FAILED

    @pytest.mark.parametrize(
        ("status", "prefix"),
        [(STATUS_FAILED, "medium_failed"), (STATUS_UNMEASURED, "medium_unmeasured")],
    )
    def test_a_finding_names_its_medium_and_its_verdict(
        self, status: str, prefix: str
    ) -> None:
        line = finding_for(MediumCheck("some-medium", status, "because"))
        assert line == f"{prefix}: some-medium — because"

    @pytest.mark.parametrize("status", [STATUS_PASSED, STATUS_NOT_APPLICABLE])
    def test_a_medium_that_is_fine_contributes_no_finding(self, status: str) -> None:
        assert finding_for(MediumCheck("some-medium", status, "fine")) is None


class TestTheTrackerIdComparisonThatWouldHaveCaughtBdlux171:
    """#171: the data was in hand and the comparison was never made."""

    def test_the_number_in_the_title_is_compared_with_the_number_allocated(
        self,
    ) -> None:
        """The replay: authored as `.39`, allocated `.41`, and nobody compared.

        In #171 the coordinator authored two beads as `.39` and `.40`, a
        concurrent agent's own `bd create` took `.39` first, and the two landed as
        `.40` and `.41` still carrying the old numbers. `bd dep add` then built a
        real, valid, WRONG edge; it was caught only because the command echoes
        full titles and a human read the echo.
        """
        records = [
            _bead("beadloom-mr2l.40", title="[BDL-061.39][dev] S2 core"),
            _bead("beadloom-mr2l.41", title="[BDL-061.40][dev] Windows CI"),
        ]
        assert title_id_mismatches(records) == (
            ("beadloom-mr2l.40", "BDL-061.39"),
            ("beadloom-mr2l.41", "BDL-061.40"),
        )

    def test_a_title_numbering_a_bead_the_way_the_tracker_did_agrees(self) -> None:
        """Only the trailing number is compared — the prefixes differ by design."""
        record = _bead("beadloom-mr2l.51", title="[BDL-061.51][dev] three modules")
        assert title_id_mismatches([record]) == ()

    def test_a_title_that_numbers_nothing_claims_nothing(self) -> None:
        record = _bead("beadloom-mr2l.80", title="[BDL-061][dev] the S6 fix cycle")
        assert title_id_mismatches([record]) == ()

    @pytest.mark.parametrize(
        "title",
        [
            "release v2.2.0 to PyPI",
            "require Python 3.10",
            "bump mcp to 2.0",
            "the 100 % case",
        ],
    )
    def test_a_version_string_is_not_read_as_a_bead_reference(
        self, title: str
    ) -> None:
        """BDL-UX #169's lesson: do not read a number out of a larger token.

        `docs-audit` once failed the Gate because it read `BDL-061.29` as a CLI
        count. A check that reports a version string as a mis-numbered bead would
        be the same misparse pointing the other way, and it would train authors to
        write titles for the checker.
        """
        assert title_id_mismatches([_bead("proj.7", title=title)]) == ()

    def test_a_tracker_id_carrying_no_number_still_reports_a_numbered_title(
        self,
    ) -> None:
        """The title claims a number the id does not have, which is the same defect."""
        record = _bead("beadloom-uxqc", title="[BDL-061.12][dev] work")
        assert title_id_mismatches([record]) == (("beadloom-uxqc", "BDL-061.12"),)

    def test_the_title_is_read_from_the_title_not_from_the_body(self) -> None:
        """A bead that MENTIONS another bead is not a bead that mis-numbers itself.

        The description of this very bead names `.21` and `.22` repeatedly. Reading
        the whole declaration would report every one of them, which is how a check
        becomes noise and then becomes ignored.
        """
        record = BeadRecord(
            bead_id="beadloom-mr2l.80",
            declaration="[BDL-061][dev] the S6 fix cycle\nsupersedes BDL-061.22",
            title="[BDL-061][dev] the S6 fix cycle",
        )
        assert title_id_mismatches([record]) == ()

    def test_a_caller_that_kept_the_title_in_the_declaration_is_still_checked(
        self,
    ) -> None:
        """The documented fallback: the first line, which is how the CLI composes it."""
        record = BeadRecord(
            bead_id="proj.41", declaration="[BDL-061.39][dev] work\nbody text"
        )
        assert title_id_mismatches([record]) == (("proj.41", "BDL-061.39"),)


class TestTheWorkingTreeCheckAsksBdlux181sQuestion:
    """#181 was not "the tree was dirty" — it was work in nobody's clean room."""

    def test_a_changed_path_no_bead_in_the_plan_owns_is_the_finding(
        self, conn: sqlite3.Connection
    ) -> None:
        environment = WaveEnvironment(
            tree_changed_paths=("src/reporting/core.py",),
            commit_gate=GATE_COMMIT_SCOPED,
            doc_baseline_stale_pairs=0,
            landing_lock_sites=(),
        )
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "shipping")],
            conn=conn,
            environment=environment,
        )
        check = _check(plan.media_checks, MEDIUM_WORKING_TREE)
        assert check.status == STATUS_FAILED
        assert "src/reporting/core.py" in check.detail
        assert plan.exit_code == 1

    def test_a_changed_path_inside_a_beads_scope_is_that_beads_own_work(
        self, conn: sqlite3.Connection
    ) -> None:
        """Attributable work is not unattributed work, and the check says so."""
        environment = WaveEnvironment(
            tree_changed_paths=("src/billing/core.py",),
            commit_gate=GATE_COMMIT_SCOPED,
            doc_baseline_stale_pairs=0,
            landing_lock_sites=(),
        )
        plan = plan_waves(
            [_bead("a", "billing"), _bead("b", "shipping")],
            conn=conn,
            environment=environment,
            axes=_approving("billing", "shipping"),
        )
        assert _check(plan.media_checks, MEDIUM_WORKING_TREE).status == STATUS_PASSED
        assert plan.exit_code == 0


class TestTheCommitGateCheckReadsWhatIsInstalled:
    """`.21` observed its own commit judged by the hook it had just replaced."""

    @pytest.mark.parametrize(
        ("gate", "status", "word"),
        [
            (GATE_COMMIT_SCOPED, STATUS_PASSED, "stages"),
            (GATE_WHOLE_TREE, STATUS_FAILED, "install-hooks"),
            (GATE_ABSENT, STATUS_FAILED, "no pre-commit hook"),
            (None, STATUS_UNMEASURED, "could not be read"),
        ],
    )
    def test_each_answer_about_the_installed_hook_is_a_different_verdict(
        self, gate: str | None, status: str, word: str
    ) -> None:
        checks = check_media(
            [_bead("a")],
            environment=WaveEnvironment(commit_gate=gate),
        )
        check = _check(checks, MEDIUM_COMMIT_GATE)
        assert check.status == status
        assert word in check.detail

    def test_both_shipped_hook_templates_carry_the_marker_the_check_reads(
        self,
    ) -> None:
        """The check and the hook cannot drift: one marker, read from the source.

        Imported from the module that WRITES the hook rather than retyped, for the
        reason `.22` gave about the scope block — a retyped copy stays green while
        the thing it claims to describe moves.
        """
        from beadloom.services.commands.docsync import (
            _HOOK_SCOPE_MARKER,
            _HOOK_TEMPLATE_BLOCK,
            _HOOK_TEMPLATE_WARN,
        )

        assert _HOOK_SCOPE_MARKER in _HOOK_TEMPLATE_WARN
        assert _HOOK_SCOPE_MARKER in _HOOK_TEMPLATE_BLOCK


class TestTheDocBaselineCheckStatesWhatTheWaveInherits:
    @pytest.mark.parametrize(
        ("stale", "status"),
        [(0, STATUS_PASSED), (1, STATUS_FAILED), (52, STATUS_FAILED)],
    )
    def test_a_baseline_already_stale_is_drift_the_waves_doc_pass_cannot_attribute(
        self, stale: int, status: str
    ) -> None:
        checks = check_media(
            [_bead("a")],
            environment=WaveEnvironment(doc_baseline_stale_pairs=stale),
        )
        assert _check(checks, MEDIUM_DOC_BASELINE).status == status


class TestTheGuaranteeSentenceMatchesTheCode:
    """The prose is what a reader trusts, so it is held to the code by a test."""

    def test_the_package_docstring_names_the_split_it_ships(self) -> None:
        import beadloom.application.waves as waves_package

        text = waves_package.__doc__ or ""
        assert "CHECKS the medium's plan-time precondition" in text
        assert "cannot be, by anything holding a plan" in text

