"""The full guard verdict matrix: strictness x exclusion x check outcome (BDL-061 S1).

``tests/test_guards.py`` proves six cells of this matrix. The cells it does not
enumerate are exactly where a wrong verdict hides — a ``block`` project that
silently blocks on an *unavailable* probe, an exclusion that loses to strictness,
a ``skip`` whose reason does not say which of the three skips it is. This module
enumerates the rest and asserts the precedence order between them.
"""

from __future__ import annotations

import pytest

from beadloom.application.guards.checks import BUILTIN_GUARDS
from beadloom.application.guards.config import GuardConfigError, build_guards_config
from beadloom.application.guards.contract import ClaimedBead, Guard, GuardFinding
from beadloom.application.guards.evaluation import UnknownGuardError, evaluate_guard
from beadloom.application.guards.models import GuardOutcome

# The three check outcomes `bead-claimed` can produce, addressed by the probe
# state that produces them. `None` is not `()`: "cannot tell" is not "nothing".
_PROBE_STATE = {
    "satisfied": (ClaimedBead(id="bd-1"),),
    "violated": (),
    "unavailable": None,
}

# strictness x check outcome -> the outcome the evaluator must produce.
_EXPECTED = {
    ("off", "satisfied"): GuardOutcome.SKIP,
    ("off", "violated"): GuardOutcome.SKIP,
    ("off", "unavailable"): GuardOutcome.SKIP,
    ("warn", "satisfied"): GuardOutcome.PASS,
    ("warn", "violated"): GuardOutcome.WARN,
    ("warn", "unavailable"): GuardOutcome.SKIP,
    ("block", "satisfied"): GuardOutcome.PASS,
    ("block", "violated"): GuardOutcome.BLOCK,
    ("block", "unavailable"): GuardOutcome.SKIP,
}

_EXIT_CODE = {
    GuardOutcome.PASS: 0,
    GuardOutcome.SKIP: 0,
    GuardOutcome.WARN: 1,
    GuardOutcome.BLOCK: 2,
}


def _strictness_flow(value: str) -> str:
    return f"guards:\n  bead-claimed:\n    strictness: {{default: '{value}'}}\n"


class TestStrictnessTimesCheckOutcome:
    """Every cell of strictness x check outcome, with no exclusion in play."""

    @pytest.mark.parametrize(("strictness", "check"), sorted(_EXPECTED))
    def test_verdict_matrix(
        self, tmp_path, write_flow_yml, make_guard_probes, strictness, check
    ) -> None:
        # Arrange
        write_flow_yml(_strictness_flow(strictness))
        expected = _EXPECTED[(strictness, check)]

        # Act
        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=make_guard_probes(beads=_PROBE_STATE[check]),
        )

        # Assert
        assert verdict.outcome is expected
        assert verdict.exit_code == _EXIT_CODE[expected]

    @pytest.mark.parametrize("strictness", ["warn", "block"])
    def test_an_unavailable_probe_never_hardens_into_a_violation(
        self, tmp_path, write_flow_yml, make_guard_probes, strictness
    ) -> None:
        """Strictness raises the price of a *violation*, never of "cannot tell"."""
        write_flow_yml(_strictness_flow(strictness))

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=make_guard_probes(beads=None),
        )

        assert verdict.outcome is GuardOutcome.SKIP
        assert "tracker" in verdict.why

    @pytest.mark.parametrize("strictness", ["warn", "block"])
    def test_a_satisfied_condition_passes_at_every_strictness(
        self, tmp_path, write_flow_yml, make_guard_probes, strictness
    ) -> None:
        write_flow_yml(_strictness_flow(strictness))

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            probes=make_guard_probes(beads=(ClaimedBead(id="bd-7"),)),
        )

        assert verdict.outcome is GuardOutcome.PASS
        assert verdict.remediation == ""

    def test_the_three_skips_are_distinguishable_by_their_reason(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """off, excluded and unavailable all exit 0 — only ``why`` tells them apart."""
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    strictness: {default: warn, chore: 'off'}\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational scripts are not bead-scoped'\n"
            "        until: 'BDL-999'\n"
        )
        probes = make_guard_probes(beads=())

        off = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py", "work_kind": "chore"},
            probes=probes,
        )
        excluded = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "scripts/deploy.sh"},
            probes=probes,
        )
        unavailable = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=make_guard_probes(beads=None),
        )

        reasons = {off.why, excluded.why, unavailable.why}
        assert len(reasons) == 3
        assert "off" in off.why and "chore" in off.why
        assert "operational scripts" in excluded.why and "BDL-999" in excluded.why
        assert "tracker" in unavailable.why
        assert {off.outcome, excluded.outcome, unavailable.outcome} == {GuardOutcome.SKIP}


class TestExclusionPrecedence:
    """An exclusion outranks strictness; ``off`` outranks the exclusion."""

    _EXCLUDED = (
        "guards:\n"
        "  bead-claimed:\n"
        "    strictness: {default: block}\n"
        "    exclusions:\n"
        "      - path: 'scripts/**'\n"
        "        reason: 'operational scripts are not bead-scoped'\n"
        "        until: 'BDL-999 introduces a scripts node'\n"
    )

    def test_an_exclusion_beats_block_strictness(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(self._EXCLUDED)

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "scripts/deploy.sh"},
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is GuardOutcome.SKIP
        assert verdict.exit_code == 0
        assert "operational scripts" in verdict.why

    def test_an_unmatched_exclusion_leaves_block_strictness_intact(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(self._EXCLUDED)

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is GuardOutcome.BLOCK

    def test_an_excluded_path_does_not_run_the_check_at_all(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """The short-circuit is real: a probe that would explode is never consulted."""
        write_flow_yml(self._EXCLUDED)

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "scripts/deploy.sh"},
            probes=make_guard_probes(exploding=True),
        )

        assert verdict.outcome is GuardOutcome.SKIP

    def test_off_is_resolved_before_the_exclusion_so_its_reason_names_the_work_kind(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """Both would skip; the recorded reason must be the one that actually applied."""
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    strictness: {default: block, chore: 'off'}\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational scripts are not bead-scoped'\n"
            "        until: 'BDL-999'\n"
        )

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "scripts/deploy.sh", "work_kind": "chore"},
            probes=make_guard_probes(exploding=True),
        )

        assert verdict.outcome is GuardOutcome.SKIP
        assert "off" in verdict.why
        assert "operational scripts" not in verdict.why

    def test_the_first_matching_exclusion_wins_in_declaration_order(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'first'\n"
            "        until: 'BDL-1'\n"
            "      - path: 'scripts/deploy.sh'\n"
            "        reason: 'second'\n"
            "        until: 'BDL-2'\n"
        )

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "scripts/deploy.sh"},
            probes=make_guard_probes(beads=()),
        )

        assert "first" in verdict.why
        assert "second" not in verdict.why

    def test_a_satisfied_check_under_an_exclusion_still_reads_as_skip_not_pass(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """An exempt path must not be reported as having been checked and passed."""
        write_flow_yml(self._EXCLUDED)

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "scripts/deploy.sh"},
            probes=make_guard_probes(beads=(ClaimedBead(id="bd-1"),)),
        )

        assert verdict.outcome is GuardOutcome.SKIP


class TestWorkKindResolution:
    """Strictness is per work kind — one config, several contexts."""

    _PER_KIND = (
        "guards:\n"
        "  bead-claimed:\n"
        "    strictness: {default: warn, epic: block, chore: 'off'}\n"
    )

    @pytest.mark.parametrize(
        ("work_kind", "expected"),
        [
            ("epic", GuardOutcome.BLOCK),
            ("chore", GuardOutcome.SKIP),
            ("bug", GuardOutcome.WARN),
            ("", GuardOutcome.WARN),
            (None, GuardOutcome.WARN),
        ],
    )
    def test_one_config_yields_a_different_verdict_per_work_kind(
        self, tmp_path, write_flow_yml, make_guard_probes, work_kind, expected
    ) -> None:
        write_flow_yml(self._PER_KIND)
        context = {"path": "src/app.py"}
        if work_kind is not None:
            context["work_kind"] = work_kind

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context=context,
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is expected

    def test_a_work_kind_with_no_default_key_falls_back_to_warn(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """No ``default:`` declared at all — the shipped floor is warn, never off."""
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {epic: block}\n")

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py", "work_kind": "spike"},
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is GuardOutcome.WARN

    def test_a_guard_switched_off_for_chores_still_blocks_for_epics(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(self._PER_KIND)
        probes = make_guard_probes(beads=())

        chore = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py", "work_kind": "chore"},
            probes=probes,
        )
        epic = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py", "work_kind": "epic"},
            probes=probes,
        )

        assert chore.outcome is GuardOutcome.SKIP
        assert epic.outcome is GuardOutcome.BLOCK


class TestExclusionPathResolution:
    """The harness supplies absolute paths; exclusions are declared relative."""

    _FLOW = (
        "guards:\n"
        "  bead-claimed:\n"
        "    exclusions:\n"
        "      - path: 'scripts/**'\n"
        "        reason: 'operational scripts are not bead-scoped'\n"
        "        until: 'BDL-999'\n"
    )

    def test_an_absolute_path_inside_the_project_matches_a_relative_exclusion(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """Claude Code sends ``/abs/path``; without relativisation every exclusion is dead."""
        write_flow_yml(self._FLOW)

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": str(tmp_path / "scripts" / "deploy.sh")},
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is GuardOutcome.SKIP

    def test_a_dot_slash_prefix_is_normalised_before_matching(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(self._FLOW)

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "./scripts/deploy.sh"},
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is GuardOutcome.SKIP

    def test_an_absolute_path_outside_the_project_inherits_no_exclusion(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(self._FLOW)

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "/elsewhere/scripts/deploy.sh"},
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is GuardOutcome.WARN

    def test_a_catch_all_exclusion_does_not_cover_an_invocation_with_no_path(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """An unknown target must not inherit someone else's exemption."""
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: '**'\n"
            "        reason: 'migrating'\n"
            "        until: 'BDL-999'\n"
        )

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is GuardOutcome.WARN
        assert any("no path" in item for item in verdict.not_covered)

    def test_an_exclusion_matching_nothing_is_accepted_and_leaves_the_guard_live(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """A typo'd pattern leaves the guard LIVE — and is now reported, not silent.

        The evaluation behaviour is unchanged and is the safe direction: a
        pattern that matches nothing exempts nothing, so the guard still fires.
        What changed is that the silence is gone — ``--liveness`` names a pattern
        matching no file in the project (see
        ``tests/test_guards_liveness.py::TestExcludedEverywhere``), so an author
        who believed ``scripts/`` was exempt finds out from the tool.
        """
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scrpits/**'\n"
            "        reason: 'typo in the pattern'\n"
            "        until: 'BDL-999'\n"
        )

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "scripts/deploy.sh"},
            probes=make_guard_probes(beads=()),
        )

        assert verdict.outcome is GuardOutcome.WARN


class TestGuardOptionsReachTheCheck:
    """``options:`` in flow.yml must arrive at the check — silently dropped, it lies."""

    def test_a_configured_trunk_name_changes_which_branch_violates(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml(
            "guards:\n  working-branch:\n    options: {trunk: develop}\n"
        )

        on_develop = evaluate_guard(
            "working-branch",
            project_root=tmp_path,
            probes=make_guard_probes(branch="develop"),
        )
        on_main = evaluate_guard(
            "working-branch",
            project_root=tmp_path,
            probes=make_guard_probes(branch="main"),
        )

        assert on_develop.outcome is GuardOutcome.WARN
        assert on_main.outcome is GuardOutcome.PASS

    def test_without_options_the_default_trunk_is_main(
        self, tmp_path, make_guard_probes
    ) -> None:
        verdict = evaluate_guard(
            "working-branch", project_root=tmp_path, probes=make_guard_probes(branch="main")
        )

        assert verdict.outcome is GuardOutcome.WARN
        assert verdict.remediation

    def test_options_are_not_echoed_into_the_verdict_context(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """Configuration is not evidence about this invocation; only context is."""
        write_flow_yml("guards:\n  working-branch:\n    options: {trunk: develop}\n")

        verdict = evaluate_guard(
            "working-branch",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=make_guard_probes(branch="develop"),
        )

        assert dict(verdict.context) == {"path": "src/app.py"}


class TestVerdictInvariantsAcrossTheMatrix:
    def test_every_warn_names_something_it_did_not_check(
        self, tmp_path, make_guard_probes
    ) -> None:
        for name, probes in (
            ("bead-claimed", make_guard_probes(beads=())),
            ("working-branch", make_guard_probes(branch="main")),
        ):
            verdict = evaluate_guard(name, project_root=tmp_path, probes=probes)
            assert verdict.outcome is GuardOutcome.WARN
            assert verdict.not_covered
            assert verdict.remediation

    def test_a_check_that_names_nothing_uncovered_still_yields_an_actionable_warn(
        self, tmp_path, monkeypatch, make_guard_probes
    ) -> None:
        """The evaluator's fallback: otherwise a forgetful check would crash the verdict."""
        guard = Guard(
            name="silent-guard",
            summary="a check that forgets to say what it skipped",
            check=lambda _request: GuardFinding.violated("nope", remediation="do it"),
        )
        monkeypatch.setitem(BUILTIN_GUARDS, "silent-guard", guard)

        verdict = evaluate_guard(
            "silent-guard", project_root=tmp_path, probes=make_guard_probes()
        )

        assert verdict.outcome is GuardOutcome.WARN
        assert verdict.not_covered == (
            "anything beyond this guard's single condition: a check that forgets "
            "to say what it skipped",
        )

    def test_a_check_skip_reason_is_passed_through_verbatim(
        self, tmp_path, monkeypatch, make_guard_probes
    ) -> None:
        guard = Guard(
            name="skipping-guard",
            summary="a check that cannot apply here",
            check=lambda _request: GuardFinding.skipped("the moon is in the wrong phase"),
        )
        monkeypatch.setitem(BUILTIN_GUARDS, "skipping-guard", guard)

        verdict = evaluate_guard(
            "skipping-guard", project_root=tmp_path, probes=make_guard_probes()
        )

        assert verdict.outcome is GuardOutcome.SKIP
        assert verdict.why == "the moon is in the wrong phase"

    @pytest.mark.parametrize(
        ("beads", "outcome"),
        [
            ((ClaimedBead(id="bd-1"),), GuardOutcome.PASS),
            ((), GuardOutcome.WARN),
            (None, GuardOutcome.SKIP),
        ],
    )
    def test_the_context_is_echoed_back_on_every_outcome(
        self, tmp_path, make_guard_probes, beads, outcome
    ) -> None:
        context = {"path": "src/app.py", "tool": "Edit", "work_kind": "bug"}

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context=context,
            probes=make_guard_probes(beads=beads),
        )

        assert verdict.outcome is outcome
        assert dict(verdict.context) == context

    @pytest.mark.parametrize("outcome_name", ["pass", "skip"])
    def test_a_non_violation_carries_no_remediation(
        self, tmp_path, make_guard_probes, outcome_name
    ) -> None:
        beads = (ClaimedBead(id="bd-1"),) if outcome_name == "pass" else None

        verdict = evaluate_guard(
            "bead-claimed", project_root=tmp_path, probes=make_guard_probes(beads=beads)
        )

        assert verdict.outcome.value == outcome_name
        assert verdict.remediation == ""


class TestInjectedConfigAndUnknownNames:
    def test_an_injected_config_is_used_instead_of_the_file_on_disk(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        """The Gate will evaluate many guards against one already-parsed config."""
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: warn}\n")
        injected = build_guards_config(
            {"guards": {"bead-claimed": {"strictness": {"default": "block"}}}}
        )

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            probes=make_guard_probes(beads=()),
            config=injected,
        )

        assert verdict.outcome is GuardOutcome.BLOCK

    def test_an_injected_config_means_a_broken_file_is_never_read(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml("guards: [this is not a mapping]\n")

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            probes=make_guard_probes(beads=()),
            config=build_guards_config({}),
        )

        assert verdict.outcome is GuardOutcome.WARN

    def test_an_unknown_guard_name_is_a_config_error_not_a_clean_verdict(
        self, tmp_path
    ) -> None:
        """The CLI maps GuardConfigError to exit 3, so the subclassing is the contract."""
        assert issubclass(UnknownGuardError, GuardConfigError)
        with pytest.raises(UnknownGuardError) as exc:
            evaluate_guard("bead-clamied", project_root=tmp_path)
        assert "bead-claimed" in str(exc.value)

    def test_a_malformed_flow_yml_stops_the_evaluation_rather_than_defaulting(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: shout}\n")

        with pytest.raises(GuardConfigError):
            evaluate_guard(
                "bead-claimed", project_root=tmp_path, probes=make_guard_probes(beads=())
            )


class TestHonestDefaultsAndInvariants:
    """The corners a caller reaches by wiring nothing at all."""

    def test_unwired_probes_report_unavailable_so_the_guard_skips(self, tmp_path) -> None:
        """A caller that supplies no probes must get a skip, never a false pass."""
        from beadloom.application.guards.contract import GuardProbes

        default_probes = GuardProbes()
        assert default_probes.tracker.claimed_beads() is None
        assert default_probes.workspace.current_branch() is None

        for name in ("bead-claimed", "working-branch"):
            verdict = evaluate_guard(name, project_root=tmp_path)
            assert verdict.outcome is GuardOutcome.SKIP
            assert verdict.why.strip()

    @pytest.mark.parametrize(
        "outcome", [GuardOutcome.PASS, GuardOutcome.BLOCK, GuardOutcome.SKIP]
    )
    def test_a_verdict_with_no_reason_is_rejected_at_construction(self, outcome) -> None:
        """Not only skips: an unexplained pass is as useless to a reader as an unexplained skip."""
        from beadloom.application.guards.models import GuardVerdict

        with pytest.raises(ValueError, match=r"why|reason"):
            GuardVerdict(guard="g", outcome=outcome, why="   ", not_covered=("x",))

    def test_a_single_character_wildcard_does_not_cross_a_directory(self, tmp_path) -> None:
        """``?`` is one non-separator character — otherwise an exclusion over-reaches."""
        from beadloom.application.guards.config import build_guards_config

        spec = build_guards_config(
            {
                "guards": {
                    "bead-claimed": {
                        "exclusions": [
                            {"path": "scripts/a?.sh", "reason": "why", "until": "BDL-1"}
                        ]
                    }
                }
            }
        ).spec_for("bead-claimed")

        assert spec.exclusion_for("scripts/ab.sh") is not None
        assert spec.exclusion_for("scripts/abc.sh") is None
        assert spec.exclusion_for("scripts/a/.sh") is None
