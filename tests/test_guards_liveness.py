"""Guard liveness — a gate that cannot be shown to have run counts as not run (BDL-061 S1).

Four states matter and only two of them are covered elsewhere: never-fired,
fired-then-stopped, misconfigured, and excluded-everywhere. The dangerous one is
the third: a liveness report that swallows a broken ``flow.yml`` would show every
guard as quietly idle, which is the same output a healthy fresh clone produces.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from click.testing import CliRunner

from beadloom.application.guards.checks import GUARD_NAMES
from beadloom.application.guards.config import GuardConfigError, load_guards_config
from beadloom.application.guards.firing import FIRINGS_RELPATH, read_firings, record_firing
from beadloom.application.guards.liveness import build_liveness
from beadloom.application.guards.models import GuardOutcome, GuardVerdict
from beadloom.services.cli import main


def _verdict(guard: str, outcome: GuardOutcome) -> GuardVerdict:
    """A minimal well-formed verdict for the given outcome."""
    return GuardVerdict(
        guard=guard,
        outcome=outcome,
        why=f"{outcome.value} for the record",
        not_covered=("everything else",),
        remediation="do the thing" if outcome is GuardOutcome.BLOCK else "",
    )


def _fire(root, guard: str, outcome: GuardOutcome, *, at: str = "2026-01-01T00:00:00+00:00"):
    """Record one firing at a fixed instant so assertions are deterministic."""
    return record_firing(root, _verdict(guard, outcome), at=datetime.fromisoformat(at))


def _rows(root) -> dict:
    return {row.guard: row for row in build_liveness(root)}


class TestNeverFired:
    def test_a_fresh_project_reports_every_guard_as_never_fired_and_idle(self, tmp_path) -> None:
        rows = _rows(tmp_path)

        assert set(rows) == set(GUARD_NAMES)
        for row in rows.values():
            assert row.never_fired is True
            assert row.idle is True
            assert row.fired_count == 0
            assert row.last_fired_at == ""
            assert row.last_outcome == ""

    def test_rows_come_back_in_deterministic_name_order(self, tmp_path) -> None:
        assert tuple(row.guard for row in build_liveness(tmp_path)) == GUARD_NAMES

    def test_a_guard_declared_in_flow_yml_but_never_run_is_still_never_fired(
        self, tmp_path, write_flow_yml
    ) -> None:
        """Declaring a guard is not evidence it runs — the two columns are independent."""
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: block}\n")

        rows = _rows(tmp_path)

        assert rows["bead-claimed"].declared is True
        assert rows["bead-claimed"].strictness == "block"
        assert rows["bead-claimed"].never_fired is True
        assert rows["bead-claimed"].idle is True

    def test_an_empty_firing_file_is_not_evidence_of_a_firing(self, tmp_path) -> None:
        path = tmp_path / FIRINGS_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n   \n", encoding="utf-8")

        assert _rows(tmp_path)["bead-claimed"].never_fired is True

    @pytest.mark.parametrize(
        "line",
        [
            "not json",
            "[]",
            '"a string"',
            "3",
            '{"outcome": "pass"}',
            '{"guard": "bead-claimed"}',
            '{"guard": 7, "outcome": "pass"}',
        ],
    )
    def test_a_record_of_the_wrong_shape_never_counts_as_a_firing(
        self, tmp_path, line
    ) -> None:
        """A junk line must not manufacture evidence that a gate ran."""
        path = tmp_path / FIRINGS_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(line + "\n", encoding="utf-8")

        assert read_firings(tmp_path) == ()
        assert _rows(tmp_path)["bead-claimed"].never_fired is True


class TestFiredAndStopped:
    def test_one_guard_firing_does_not_mark_another_as_having_run(self, tmp_path) -> None:
        _fire(tmp_path, "working-branch", GuardOutcome.PASS)

        rows = _rows(tmp_path)

        assert rows["working-branch"].fired_count == 1
        assert rows["bead-claimed"].fired_count == 0
        assert rows["bead-claimed"].never_fired is True

    def test_the_last_outcome_is_the_most_recent_one_not_the_first(self, tmp_path) -> None:
        _fire(tmp_path, "bead-claimed", GuardOutcome.WARN, at="2026-01-01T00:00:00+00:00")
        _fire(tmp_path, "bead-claimed", GuardOutcome.BLOCK, at="2026-01-02T00:00:00+00:00")
        _fire(tmp_path, "bead-claimed", GuardOutcome.PASS, at="2026-01-03T00:00:00+00:00")

        row = _rows(tmp_path)["bead-claimed"]

        assert row.fired_count == 3
        assert row.last_outcome == "pass"
        assert row.last_fired_at == "2026-01-03T00:00:00+00:00"

    def test_a_guard_that_fired_long_ago_carries_the_evidence_of_when(
        self, tmp_path
    ) -> None:
        """Recorded gap: "fired then stopped" has no threshold, only a timestamp.

        Deciding that an old firing is a dead gate is the Gate's call (S2+),
        because a fresh clone is legitimately idle. What the report must do is
        carry the date so the judgement is possible at all.
        """
        _fire(tmp_path, "bead-claimed", GuardOutcome.PASS, at="2020-03-01T09:00:00+00:00")

        row = _rows(tmp_path)["bead-claimed"]

        assert row.last_fired_at == "2020-03-01T09:00:00+00:00"
        assert row.never_fired is False
        assert row.idle is False

    def test_a_firing_for_a_name_no_longer_registered_is_not_reported(
        self, tmp_path
    ) -> None:
        """A guard deleted from the registry must not linger as a phantom row."""
        path = tmp_path / FIRINGS_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"guard": "retired-guard", "outcome": "pass", "at": "2026-01-01"})
            + "\n",
            encoding="utf-8",
        )

        rows = _rows(tmp_path)

        assert "retired-guard" not in rows
        assert all(row.never_fired for row in rows.values())

    def test_the_recorded_instant_defaults_to_now_in_utc(self, tmp_path) -> None:
        record_firing(tmp_path, _verdict("bead-claimed", GuardOutcome.PASS))

        stamp = datetime.fromisoformat(_rows(tmp_path)["bead-claimed"].last_fired_at)

        assert stamp.tzinfo is not None
        assert abs((datetime.now(timezone.utc) - stamp).total_seconds()) < 60


class TestExcludedEverywhere:
    @pytest.mark.parametrize("pattern", ["'**'", "'*'", "'**/*'"])
    def test_a_catch_all_exclusion_is_reported(
        self, tmp_path, write_flow_yml, pattern
    ) -> None:
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            f"      - path: {pattern}\n"
            "        reason: 'migrating'\n"
            "        until: 'BDL-999'\n"
        )

        rows = _rows(tmp_path)

        assert rows["bead-claimed"].excluded_everywhere is True
        assert rows["bead-claimed"].idle is True
        assert rows["working-branch"].excluded_everywhere is False

    def test_a_narrow_exclusion_is_not_reported_as_excluded_everywhere(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational scripts'\n"
            "        until: 'BDL-999'\n"
        )

        assert _rows(tmp_path)["bead-claimed"].excluded_everywhere is False

    def test_a_catch_all_spelled_another_way_is_not_recognised(
        self, tmp_path, write_flow_yml
    ) -> None:
        """Recorded gap: the check is a literal pattern list, not a coverage test.

        ``**/**`` matches every path exactly as ``**`` does, but is not in the
        recognised set — so a guard excluded everywhere can still report as live.
        Pinned because it is a *false negative in the honesty report*, which is
        the one number this command exists to produce.
        """
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: '**/**'\n"
            "        reason: 'migrating'\n"
            "        until: 'BDL-999'\n"
        )
        exclusion = load_guards_config(tmp_path).spec_for("bead-claimed").exclusions[0]

        # The pattern demonstrably covers everything...
        assert exclusion.matches("src/app.py")
        assert exclusion.matches("README.md")
        # ...and the honesty report still calls the guard live.
        assert _rows(tmp_path)["bead-claimed"].excluded_everywhere is False

    def test_off_for_every_declared_work_kind_is_excluded_everywhere(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml(
            "guards:\n  bead-claimed:\n    strictness: {default: 'off', epic: 'off'}\n"
        )

        assert _rows(tmp_path)["bead-claimed"].excluded_everywhere is True

    def test_off_for_one_work_kind_only_still_protects_the_others(
        self, tmp_path, write_flow_yml
    ) -> None:
        """A guard off for chores is not a dead guard — reporting it as one is a lie."""
        write_flow_yml(
            "guards:\n  bead-claimed:\n    strictness: {default: block, chore: 'off'}\n"
        )

        row = _rows(tmp_path)["bead-claimed"]

        assert row.excluded_everywhere is False
        assert row.strictness == "block"

    def test_a_guard_can_be_both_excluded_everywhere_and_have_fired(
        self, tmp_path, write_flow_yml
    ) -> None:
        """Firings from before the exclusion landed must not hide the exclusion."""
        write_flow_yml(
            "guards:\n  bead-claimed:\n    strictness: {default: 'off'}\n"
        )
        _fire(tmp_path, "bead-claimed", GuardOutcome.WARN)

        row = _rows(tmp_path)["bead-claimed"]

        assert row.never_fired is False
        assert row.excluded_everywhere is True
        assert row.idle is True


class TestMisconfigured:
    def test_a_broken_flow_yml_makes_liveness_raise_rather_than_report_all_idle(
        self, tmp_path, write_flow_yml
    ) -> None:
        """Silently reporting idle would look exactly like a healthy fresh clone."""
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'no expiry declared'\n"
        )

        with pytest.raises(GuardConfigError, match="until"):
            build_liveness(tmp_path)

    def test_the_cli_reports_a_broken_flow_yml_on_the_config_error_code(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: shout}\n")

        result = CliRunner().invoke(main, ["guard", "--liveness", "--project", str(tmp_path)])

        assert result.exit_code == 3, result.output
        assert "shout" in result.stderr

    def test_an_unknown_guard_name_in_flow_yml_fails_the_liveness_report(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  bead-clamied: {}\n")

        result = CliRunner().invoke(main, ["guard", "--liveness", "--project", str(tmp_path)])

        assert result.exit_code == 3, result.output


class TestLivenessOutput:
    def test_the_json_row_carries_every_field_the_report_promises(self, tmp_path) -> None:
        result = CliRunner().invoke(
            main, ["guard", "--liveness", "--project", str(tmp_path), "--json"]
        )

        rows = json.loads(result.stdout)
        assert {row["guard"] for row in rows} == set(GUARD_NAMES)
        assert set(rows[0]) == {
            "guard",
            "declared",
            "strictness",
            "fired_count",
            "never_fired",
            "excluded_everywhere",
            "last_fired_at",
            "last_outcome",
            "idle",
        }

    def test_the_text_report_flags_a_guard_that_never_fired(self, tmp_path) -> None:
        result = CliRunner().invoke(main, ["guard", "--liveness", "--project", str(tmp_path)])

        assert result.exit_code == 0, result.output
        for name in GUARD_NAMES:
            assert name in result.output
        assert result.output.count("never-fired") == len(GUARD_NAMES)

    def test_the_text_report_names_the_source_of_the_strictness(
        self, tmp_path, write_flow_yml
    ) -> None:
        """"default" vs "flow.yml" is how a reader tells a decision from an accident."""
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: block}\n")

        result = CliRunner().invoke(main, ["guard", "--liveness", "--project", str(tmp_path)])

        assert "bead-claimed: strictness=block (flow.yml)" in result.output
        assert "working-branch: strictness=warn (default)" in result.output

    def test_the_text_report_shows_the_last_outcome_once_a_guard_has_fired(
        self, tmp_path
    ) -> None:
        _fire(tmp_path, "bead-claimed", GuardOutcome.BLOCK, at="2026-01-02T03:04:05+00:00")

        result = CliRunner().invoke(main, ["guard", "--liveness", "--project", str(tmp_path)])

        assert "fired=1" in result.output
        assert "last block at 2026-01-02T03:04:05+00:00" in result.output
        assert "never-fired" not in result.output.splitlines()[0]

    def test_liveness_exits_zero_even_when_every_guard_is_idle(self, tmp_path) -> None:
        """A fresh clone is legitimately idle; failing here would be a false gate."""
        result = CliRunner().invoke(main, ["guard", "--liveness", "--project", str(tmp_path)])

        assert result.exit_code == 0
