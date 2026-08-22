"""Guard primitive core: verdict model, config validation, evaluation matrix (BDL-061 S1)."""

from __future__ import annotations

import pytest

from beadloom.application.guards.config import (
    DEFAULT_STRICTNESS,
    GuardConfigError,
    load_guards_config,
)
from beadloom.application.guards.models import (
    EXIT_CODE_BY_OUTCOME,
    GuardOutcome,
    GuardVerdict,
)


def _write_flow(root, body: str) -> None:
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "flow.yml").write_text(body, encoding="utf-8")


class TestVerdictModel:
    def test_outcomes_are_the_five_declared_names(self) -> None:
        assert [o.value for o in GuardOutcome] == [
            "pass",
            "warn",
            "block",
            "skip",
            "error",
        ]

    def test_exit_codes_separate_block_from_usage_error(self) -> None:
        assert EXIT_CODE_BY_OUTCOME[GuardOutcome.PASS] == 0
        assert EXIT_CODE_BY_OUTCOME[GuardOutcome.SKIP] == 0
        assert EXIT_CODE_BY_OUTCOME[GuardOutcome.WARN] == 1
        assert EXIT_CODE_BY_OUTCOME[GuardOutcome.BLOCK] == 2

    def test_an_error_blocks_because_it_is_the_only_code_that_blocks(self) -> None:
        """"I could not tell" must stop the edit, and 2 is the code that does.

        Measured against the adapter this ships (Claude Code): exit 2 is fed back
        to the agent and blocks the tool call, every other non-zero code is shown
        to the human and the call proceeds. 1 is the warn code, and 3 is reserved
        for a configuration defect, which is a statement about the project's own
        files rather than about this edit.
        """
        assert EXIT_CODE_BY_OUTCOME[GuardOutcome.ERROR] == 2

    def test_an_error_must_name_what_it_did_not_check(self) -> None:
        """An error is a verdict with no finding behind it — so it owes the reader one."""
        with pytest.raises(ValueError, match="did not check"):
            GuardVerdict(
                guard="bead-claimed",
                outcome=GuardOutcome.ERROR,
                why="the guard could not be evaluated: boom",
            )

    def test_verdict_serializes_every_declared_field(self) -> None:
        verdict = GuardVerdict(
            guard="bead-claimed",
            outcome=GuardOutcome.WARN,
            why="no bead is in progress",
            not_covered=("whether the bead's scope covers this path",),
            remediation="bd ready --claim",
        )
        assert verdict.to_dict() == {
            "guard": "bead-claimed",
            "outcome": "warn",
            "why": "no bead is in progress",
            "not_covered": ["whether the bead's scope covers this path"],
            "remediation": "bd ready --claim",
            "context": {},
        }

    def test_skip_without_a_reason_is_rejected_at_construction(self) -> None:
        with pytest.raises(ValueError, match="skip"):
            GuardVerdict(guard="g", outcome=GuardOutcome.SKIP, why="")

    def test_warn_must_name_what_it_did_not_check(self) -> None:
        with pytest.raises(ValueError, match="not_covered"):
            GuardVerdict(guard="g", outcome=GuardOutcome.WARN, why="broken", not_covered=())


class TestGuardConfig:
    def test_absent_flow_yml_yields_default_warn_strictness(self, tmp_path) -> None:
        config = load_guards_config(tmp_path)
        spec = config.spec_for("bead-claimed")
        assert spec.strictness_for(None) == DEFAULT_STRICTNESS == "warn"

    def test_exclusion_without_reason_is_a_config_error(self, tmp_path) -> None:
        _write_flow(
            tmp_path,
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        until: 'BDL-999'\n",
        )
        with pytest.raises(GuardConfigError, match="reason"):
            load_guards_config(tmp_path)

    def test_exclusion_without_until_is_a_config_error(self, tmp_path) -> None:
        _write_flow(
            tmp_path,
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational scripts are not bead-scoped'\n",
        )
        with pytest.raises(GuardConfigError, match="until"):
            load_guards_config(tmp_path)

    def test_unknown_guard_name_in_flow_yml_is_a_config_error(self, tmp_path) -> None:
        _write_flow(tmp_path, "guards:\n  no-such-guard:\n    strictness: {default: warn}\n")
        with pytest.raises(GuardConfigError, match="no-such-guard"):
            load_guards_config(tmp_path)

    def test_unknown_strictness_value_is_a_config_error(self, tmp_path) -> None:
        _write_flow(tmp_path, "guards:\n  bead-claimed:\n    strictness: {default: shout}\n")
        with pytest.raises(GuardConfigError, match="shout"):
            load_guards_config(tmp_path)

    def test_strictness_resolves_per_work_kind_with_default_fallback(self, tmp_path) -> None:
        _write_flow(
            tmp_path,
            "guards:\n"
            "  bead-claimed:\n"
            "    strictness: {default: warn, epic: block, chore: 'off'}\n",
        )
        spec = load_guards_config(tmp_path).spec_for("bead-claimed")
        assert spec.strictness_for("epic") == "block"
        assert spec.strictness_for("chore") == "off"
        assert spec.strictness_for("bug") == "warn"
        assert spec.strictness_for(None) == "warn"

    def test_exclusion_glob_does_not_over_match_across_directories(self, tmp_path) -> None:
        _write_flow(
            tmp_path,
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/*.sh'\n"
            "        reason: 'operational scripts are not bead-scoped'\n"
            "        until: 'BDL-999 introduces a scripts node'\n",
        )
        spec = load_guards_config(tmp_path).spec_for("bead-claimed")
        assert spec.exclusion_for("scripts/deploy.sh") is not None
        assert spec.exclusion_for("scripts/nested/deploy.sh") is None
        assert spec.exclusion_for("src/app.py") is None

    def test_double_star_matches_across_directories(self, tmp_path) -> None:
        _write_flow(
            tmp_path,
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational scripts are not bead-scoped'\n"
            "        until: 'BDL-999 introduces a scripts node'\n",
        )
        spec = load_guards_config(tmp_path).spec_for("bead-claimed")
        assert spec.exclusion_for("scripts/nested/deploy.sh") is not None


class _StubTracker:
    def __init__(self, beads):
        self._beads = beads

    def claimed_beads(self):
        return self._beads


class _StubWorkspace:
    def __init__(self, branch):
        self._branch = branch

    def current_branch(self):
        return self._branch


def _probes(*, beads=(), branch="features/x"):
    from beadloom.application.guards.contract import GuardProbes

    return GuardProbes(tracker=_StubTracker(beads), workspace=_StubWorkspace(branch))


class TestEvaluation:
    """The verdict matrix: strictness x exclusion x check outcome."""

    def test_violation_defaults_to_warn_that_names_what_it_missed(self, tmp_path) -> None:
        from beadloom.application.guards.evaluation import evaluate_guard

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=_probes(beads=()),
        )
        assert verdict.outcome is GuardOutcome.WARN
        assert verdict.not_covered
        assert verdict.exit_code == 1

    def test_block_strictness_turns_the_same_violation_into_block(self, tmp_path) -> None:
        from beadloom.application.guards.evaluation import evaluate_guard

        _write_flow(
            tmp_path,
            "guards:\n  bead-claimed:\n    strictness: {default: warn, epic: block}\n",
        )
        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py", "work_kind": "epic"},
            probes=_probes(beads=()),
        )
        assert verdict.outcome is GuardOutcome.BLOCK
        assert verdict.exit_code == 2

    def test_off_strictness_skips_and_says_so(self, tmp_path) -> None:
        from beadloom.application.guards.evaluation import evaluate_guard

        _write_flow(
            tmp_path,
            "guards:\n  bead-claimed:\n    strictness: {default: warn, chore: 'off'}\n",
        )
        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py", "work_kind": "chore"},
            probes=_probes(beads=()),
        )
        assert verdict.outcome is GuardOutcome.SKIP
        assert "chore" in verdict.why
        assert verdict.exit_code == 0

    def test_excluded_path_skips_with_the_declared_reason_and_until(self, tmp_path) -> None:
        from beadloom.application.guards.evaluation import evaluate_guard

        _write_flow(
            tmp_path,
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational scripts are not bead-scoped'\n"
            "        until: 'BDL-999 introduces a scripts node'\n",
        )
        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "scripts/deploy.sh"},
            probes=_probes(beads=()),
        )
        assert verdict.outcome is GuardOutcome.SKIP
        assert "operational scripts" in verdict.why
        assert "BDL-999" in verdict.why

    def test_unavailable_probe_skips_rather_than_passing(self, tmp_path) -> None:
        from beadloom.application.guards.evaluation import evaluate_guard

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=_probes(beads=None),
        )
        assert verdict.outcome is GuardOutcome.SKIP
        assert verdict.why

    def test_satisfied_condition_passes(self, tmp_path) -> None:
        from beadloom.application.guards.contract import ClaimedBead
        from beadloom.application.guards.evaluation import evaluate_guard

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=_probes(beads=(ClaimedBead(id="bd-1"),)),
        )
        assert verdict.outcome is GuardOutcome.PASS
        assert verdict.exit_code == 0

    def test_unknown_guard_name_raises(self, tmp_path) -> None:
        from beadloom.application.guards.evaluation import UnknownGuardError, evaluate_guard

        with pytest.raises(UnknownGuardError, match="no-such-guard"):
            evaluate_guard("no-such-guard", project_root=tmp_path)

    def test_evaluation_writes_nothing_to_the_project(self, tmp_path) -> None:
        from beadloom.application.guards.evaluation import evaluate_guard

        before = sorted(p.name for p in tmp_path.rglob("*"))
        evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=_probes(beads=()),
        )
        assert sorted(p.name for p in tmp_path.rglob("*")) == before


class TestFiringRecordAndLiveness:
    def test_recorded_firing_round_trips(self, tmp_path) -> None:
        from beadloom.application.guards.firing import read_firings, record_firing

        verdict = GuardVerdict(
            guard="bead-claimed",
            outcome=GuardOutcome.WARN,
            why="no bead is in progress",
            not_covered=("scope",),
        )
        record_firing(tmp_path, verdict)
        firings = read_firings(tmp_path)
        assert [f.guard for f in firings] == ["bead-claimed"]
        assert firings[0].outcome == "warn"
        assert firings[0].at

    def test_corrupt_line_does_not_break_the_reader(self, tmp_path) -> None:
        from beadloom.application.guards.firing import FIRINGS_RELPATH, read_firings

        path = tmp_path / FIRINGS_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('not json\n{"guard": "working-branch", "outcome": "pass"}\n')
        assert [f.guard for f in read_firings(tmp_path)] == ["working-branch"]

    def test_liveness_reports_never_fired(self, tmp_path) -> None:
        from beadloom.application.guards.liveness import build_liveness

        report = {row.guard: row for row in build_liveness(tmp_path)}
        assert report["bead-claimed"].never_fired is True
        assert report["working-branch"].never_fired is True

    def test_liveness_counts_firings(self, tmp_path) -> None:
        from beadloom.application.guards.firing import record_firing
        from beadloom.application.guards.liveness import build_liveness

        record_firing(
            tmp_path,
            GuardVerdict(guard="bead-claimed", outcome=GuardOutcome.PASS, why="ok"),
        )
        report = {row.guard: row for row in build_liveness(tmp_path)}
        assert report["bead-claimed"].fired_count == 1
        assert report["bead-claimed"].never_fired is False
        assert report["bead-claimed"].last_outcome == "pass"

    def test_liveness_reports_excluded_everywhere_via_off(self, tmp_path) -> None:
        from beadloom.application.guards.liveness import build_liveness

        _write_flow(tmp_path, "guards:\n  working-branch:\n    strictness: {default: 'off'}\n")
        report = {row.guard: row for row in build_liveness(tmp_path)}
        assert report["working-branch"].excluded_everywhere is True
        assert report["bead-claimed"].excluded_everywhere is False

    def test_liveness_reports_excluded_everywhere_via_catch_all_path(self, tmp_path) -> None:
        from beadloom.application.guards.liveness import build_liveness

        _write_flow(
            tmp_path,
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: '**'\n"
            "        reason: 'migrating'\n"
            "        until: 'BDL-999'\n",
        )
        report = {row.guard: row for row in build_liveness(tmp_path)}
        assert report["bead-claimed"].excluded_everywhere is True
