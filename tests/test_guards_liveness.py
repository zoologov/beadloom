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
    @pytest.mark.parametrize("pattern", ["'**'", "'**/*'", "'**/**'", "'**/'"])
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

    def test_a_catch_all_spelled_another_way_is_reported_too(
        self, tmp_path, write_flow_yml
    ) -> None:
        """``**/**`` covers everything ``**`` does; the report must agree with the matcher.

        Was a recorded gap (a false negative), and a gap in the one command whose
        product is honesty about which gates are dead. The fix asks the matcher
        instead of comparing the pattern against a list of spellings.
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

        assert exclusion.matches("src/app.py")
        assert exclusion.matches("README.md")
        assert _rows(tmp_path)["bead-claimed"].excluded_everywhere is True

    @pytest.mark.parametrize("pattern", ["'*'", "'*.py'", "'src/*'"])
    def test_a_single_star_is_not_a_catch_all(
        self, tmp_path, write_flow_yml, pattern
    ) -> None:
        """``*`` does not cross directories, so it exempts only the top level.

        A green test used to assert the opposite (review .3, M1): a FALSE
        POSITIVE in the honesty report, and one that contradicted this feature's
        own SPEC, which says ``*`` cannot silently exempt a subtree. Reporting a
        live guard as excluded-everywhere teaches the reader to distrust the
        report, which costs more than the report is worth.
        """
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            f"      - path: {pattern}\n"
            "        reason: 'migrating'\n"
            "        until: 'BDL-999'\n"
        )
        exclusion = load_guards_config(tmp_path).spec_for("bead-claimed").exclusions[0]

        assert not exclusion.matches("src/a/b/deep.py")
        assert _rows(tmp_path)["bead-claimed"].excluded_everywhere is False

    def test_a_dead_exclusion_is_reported(self, tmp_path, write_flow_yml) -> None:
        """An exclusion that protects nothing surfaces, like a guard that never fires.

        The typo direction is safe (the guard stays live), but it is silent: the
        author believes ``scripts/`` is exempt and it is not, and nothing says so
        until someone rereads the file.
        """
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "deploy.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scrpits/**'\n"
            "        reason: 'typo in the pattern'\n"
            "        until: 'BDL-999'\n"
        )

        assert _rows(tmp_path)["bead-claimed"].dead_exclusions == ("scrpits/**",)

    def test_an_exclusion_that_matches_a_real_file_is_not_reported_dead(
        self, tmp_path, write_flow_yml
    ) -> None:
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "deploy.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational scripts'\n"
            "        until: 'BDL-999'\n"
        )

        assert _rows(tmp_path)["bead-claimed"].dead_exclusions == ()

    def test_only_the_dead_pattern_of_several_is_named(
        self, tmp_path, write_flow_yml
    ) -> None:
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "deploy.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational scripts'\n"
            "        until: 'BDL-999'\n"
            "      - path: 'vendor/**'\n"
            "        reason: 'third-party code'\n"
            "        until: 'BDL-999'\n"
        )

        assert _rows(tmp_path)["bead-claimed"].dead_exclusions == ("vendor/**",)

    def test_nothing_is_called_dead_when_no_file_could_be_read(self) -> None:
        """An unreadable tree makes every pattern look dead; silence beats a lie."""
        from beadloom.application.guards.config import GuardExclusion, GuardSpec
        from beadloom.application.guards.liveness import dead_exclusions

        spec = GuardSpec(
            name="bead-claimed",
            exclusions=(GuardExclusion(path="scrpits/**", reason="typo", until="BDL-999"),),
        )

        assert dead_exclusions(spec, ()) == ()
        assert dead_exclusions(spec, ("scripts/deploy.sh",)) == ("scrpits/**",)

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
            "dead_exclusions",
        }

    def test_the_text_report_names_a_dead_exclusion_and_its_pattern(
        self, tmp_path, write_flow_yml
    ) -> None:
        """The pattern itself, because the fix is to correct that string."""
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "deploy.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scrpits/**'\n"
            "        reason: 'typo in the pattern'\n"
            "        until: 'BDL-999'\n"
        )

        result = CliRunner().invoke(main, ["guard", "--liveness", "--project", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "matches no file in the project: 'scrpits/**'" in result.output
        assert "working-branch: " in result.output
        assert result.output.count("matches no file in the project") == 1

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


# ---------------------------------------------------------------------------
# Independent re-verification of the .25 liveness fixes (BDL-061.26).
#
# ``--liveness`` is the one command whose entire product is honesty about which
# gates are dead. The fix corrected two spellings (``*`` and ``**/**``); these
# tests ask whether the corrected predicate is *complete*, and pin the two
# answers where it is not.
# ---------------------------------------------------------------------------


def _one_exclusion(pattern: str) -> str:
    return (
        "guards:\n"
        "  bead-claimed:\n"
        "    exclusions:\n"
        f"      - path: {pattern}\n"
        "        reason: 'migrating'\n"
        "        until: 'BDL-999'\n"
    )


class TestPatternsNobodyHasClassifiedYet:
    """Spellings outside the ``*`` / ``**`` pair the review named."""

    @pytest.mark.parametrize(
        ("pattern", "expected"),
        [
            ("'**/**/**'", True),  # three of them still cross everything
            ("'?*'", False),  # one-or-more non-separator chars: top level only
            ("'*/**'", False),  # everything nested, but nothing at the top level
            ("'**/*.*'", False),  # anything with a dot — a Makefile escapes it
            ("'**/'", True),  # trailing separator is consumed by the ** rule
            ("'*/'", False),  # matches no path at all: a false claim either way
        ],
    )
    def test_the_report_agrees_with_the_matcher(
        self, tmp_path, write_flow_yml, pattern, expected
    ) -> None:
        """Whatever the answer is, it must be the matcher's answer, not a guess.

        Each row was measured against :meth:`GuardExclusion.matches` first and
        the row asserts both halves, so a future rewrite of either the predicate
        or the glob translator cannot drift them apart silently.
        """
        write_flow_yml(_one_exclusion(pattern))
        exclusion = load_guards_config(tmp_path).spec_for("bead-claimed").exclusions[0]
        probe_paths = ("README.md", "Makefile", ".gitignore", "src/a/b/c/deep.txt")

        covers_all = all(exclusion.matches(path) for path in probe_paths)

        assert covers_all is expected
        assert _rows(tmp_path)["bead-claimed"].excluded_everywhere is expected


class TestTwoExclusionsThatTogetherCoverEverything:
    """The catch-all question is asked of the exclusion LIST, not of one pattern.

    ``*`` covers the top level and ``*/**`` covers every subtree. Declared
    together they exempt every path in the project — the guard cannot fire on
    anything — while neither is a catch-all on its own. Asking "does one pattern
    cover everything" therefore called a dead gate healthy (F4); asking "does
    anything escape the patterns" is the same cost and does not.
    """

    _UNION = (
        "guards:\n"
        "  bead-claimed:\n"
        "    exclusions:\n"
        "      - path: '*'\n"
        "        reason: 'top level is scratch space'\n"
        "        until: 'BDL-999'\n"
        "      - path: '*/**'\n"
        "        reason: 'everything else is vendored'\n"
        "        until: 'BDL-999'\n"
    )

    def test_no_path_at_all_escapes_the_pair(self, tmp_path, write_flow_yml) -> None:
        write_flow_yml(self._UNION)
        spec = load_guards_config(tmp_path).spec_for("bead-claimed")

        for path in ("README.md", ".gitignore", "src/app.py", "a/b/c/d/e.txt"):
            assert spec.exclusion_for(path) is not None, path

    def test_the_guard_is_dead_and_the_report_says_so(
        self, tmp_path, write_flow_yml, make_guard_probes
    ) -> None:
        from beadloom.application.guards.evaluation import evaluate_guard

        write_flow_yml(self._UNION)
        (tmp_path / "README.md").write_text("# project\n", encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=tmp_path,
            context={"path": "src/app.py"},
            probes=make_guard_probes(beads=()),
        )
        row = _rows(tmp_path)["bead-claimed"]

        assert verdict.outcome is GuardOutcome.SKIP, verdict.why
        assert row.dead_exclusions == (), "both patterns match real files"
        # Nothing can make this guard fire, and now the row says exactly that.
        assert row.excluded_everywhere is True
        assert row.idle is True


class TestAnExclusionThatSwallowsThisProject:
    """The limit the fix declared — verified, and measured against the report.

    The fix's own note: ``excluded_everywhere`` reads the pattern only, so
    ``src/**`` in a project whose code is entirely under ``src/`` is not
    reported. That is TRUE, and defensible for a predicate on
    :class:`GuardSpec`: an answer computed from today's files would flip under an
    unrelated commit.

    What the note does not say is that the *report* has the tree in hand —
    :func:`project_files` is already walked for ``dead_exclusions`` — so the
    liveness row answers "this pattern matches nothing that exists" and never
    "this pattern matches everything that exists", though both are one pass over
    the same list.

    JUDGED AND LEFT AS IS (BDL-061.27), with the measurement that decides it:
    the second test below has to filter ``.beadloom/`` out of the walk to make
    its point, and that filter is the whole answer. Declaring an exclusion
    requires a ``.beadloom/flow.yml``, which no realistic exclusion covers, so a
    whole-tree flag would read ``False`` in every project that could set it — a
    flag that cannot fire teaches a reader to stop reading flags. The reachable
    half of the same gap was a genuine defect and IS fixed: two narrow patterns
    that together exempt everything are now reported (F4, the class above).
    """

    def test_a_project_entirely_under_the_excluded_directory_is_not_reported(
        self, tmp_path, write_flow_yml
    ) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "src" / "util.py").write_text("y = 2\n", encoding="utf-8")
        write_flow_yml(_one_exclusion("'src/**'"))

        row = _rows(tmp_path)["bead-claimed"]

        assert row.excluded_everywhere is False
        assert row.dead_exclusions == ()

    def test_every_file_the_report_can_see_is_in_fact_excluded(
        self, tmp_path, write_flow_yml
    ) -> None:
        """The fact the row would need — computed here, not reported anywhere."""
        from beadloom.application.guards.liveness import project_files

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
        write_flow_yml(_one_exclusion("'src/**'"))
        spec = load_guards_config(tmp_path).spec_for("bead-claimed")

        files = [f for f in project_files(tmp_path) if not f.startswith(".beadloom/")]

        assert files, "the walk must see something for this to mean anything"
        assert all(spec.exclusion_for(path) is not None for path in files), files


class TestWalkingTheProjectTree:
    """The tree walk behind ``dead_exclusions`` — its silent-failure corners."""

    def test_an_unreadable_directory_does_not_lose_the_readable_ones(
        self, tmp_path
    ) -> None:
        """A permission error must narrow the answer, never abort the report.

        Direction matters: a walk that returned nothing would make every pattern
        look dead (the report crying wolf), and one that raised would take the
        whole liveness command down with it.
        """
        import os
        import stat

        from beadloom.application.guards.liveness import project_files

        (tmp_path / "open").mkdir()
        (tmp_path / "open" / "a.py").write_text("x = 1\n", encoding="utf-8")
        shut = tmp_path / "shut"
        shut.mkdir()
        (shut / "b.py").write_text("y = 2\n", encoding="utf-8")
        shut.chmod(0o000)
        try:
            if os.access(shut, os.R_OK):  # running as root — the case cannot arise
                pytest.skip("directory permissions are not enforced for this user")

            files = project_files(tmp_path)
        finally:
            shut.chmod(stat.S_IRWXU)

        assert "open/a.py" in files
        assert "shut/b.py" not in files

    def test_a_vendor_directory_is_not_walked(self, tmp_path) -> None:
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "dep.js").write_text("x\n", encoding="utf-8")
        (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

        from beadloom.application.guards.liveness import project_files

        assert project_files(tmp_path) == ("app.py",)

    def test_a_symlinked_file_is_not_a_file_the_walk_counts(self, tmp_path) -> None:
        """Links are skipped, so an exclusion written about one reads as dead.

        The other half of ``tests/test_guards_paths.py``'s symlinked-directory
        case: resolution follows the link (so the exclusion no longer applies to
        it), and the walk does not (so the report cannot see it either).
        """
        from beadloom.application.guards.liveness import project_files

        (tmp_path / "real.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "link.py").symlink_to(tmp_path / "real.py")

        assert project_files(tmp_path) == ("real.py",)

    def test_a_pattern_matching_only_vendored_files_reads_as_dead(
        self, tmp_path, write_flow_yml
    ) -> None:
        """Consequence of the pruning, stated so it is a decision not a surprise.

        ``node_modules/**`` matches real files, but none the walk can see, so the
        report calls it dead. The wording ("matches no file in the project")
        carries that: a pruned tree is not part of what an exclusion is written
        about. It is the quiet direction — an over-report on a pattern nobody
        needed — but it is a false statement about the disk.
        """
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "dep.js").write_text("x\n", encoding="utf-8")
        (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
        write_flow_yml(_one_exclusion("'node_modules/**'"))

        assert _rows(tmp_path)["bead-claimed"].dead_exclusions == ("node_modules/**",)

    def test_the_walk_stops_at_the_configured_cap(self, tmp_path, monkeypatch) -> None:
        """The cap only ever makes the report quieter — asserted, not assumed."""
        from beadloom.application.guards import liveness

        for n in range(6):
            (tmp_path / f"f{n}.py").write_text("x = 1\n", encoding="utf-8")
        monkeypatch.setattr(liveness, "_MAX_FILES", 3)

        assert len(liveness.project_files(tmp_path)) == 3


class TestAGuardThatOnlyEverFailedToAnswer:
    """An ``error`` is evidence the guard RAN, and evidence it did not ANSWER.

    Both halves are load-bearing. Recording it is what closes F2 — a crash that
    wrote nothing left ``--liveness`` showing an older ``skip``, so the event did
    not exist in the report whose whole product is honesty about dead gates.
    Counting it as a firing that clears ``never-fired`` would replace one lie
    with a quieter one: a gate that has never once answered would read as alive.
    """

    def test_an_error_is_counted_and_named_as_the_last_outcome(self, tmp_path) -> None:
        _fire(tmp_path, "bead-claimed", GuardOutcome.ERROR)

        row = _rows(tmp_path)["bead-claimed"]

        assert row.fired_count == 1
        assert row.last_outcome == "error"
        assert row.last_fired_at

    def test_a_guard_that_only_errored_is_not_reported_as_having_fired(
        self, tmp_path
    ) -> None:
        _fire(tmp_path, "bead-claimed", GuardOutcome.ERROR)
        _fire(tmp_path, "bead-claimed", GuardOutcome.ERROR)

        row = _rows(tmp_path)["bead-claimed"]

        assert row.never_fired is True, "it ran twice and answered neither time"
        assert row.idle is True

    def test_one_real_answer_clears_it(self, tmp_path) -> None:
        _fire(tmp_path, "bead-claimed", GuardOutcome.ERROR)
        _fire(tmp_path, "bead-claimed", GuardOutcome.WARN)

        row = _rows(tmp_path)["bead-claimed"]

        assert row.never_fired is False
        assert row.fired_count == 2

    def test_the_text_report_shows_both_the_count_and_the_flag(self, tmp_path) -> None:
        _fire(tmp_path, "bead-claimed", GuardOutcome.ERROR)

        result = CliRunner().invoke(
            main, ["guard", "--liveness", "--project", str(tmp_path)]
        )

        assert result.exit_code == 0, result.output
        assert "fired=1" in result.output
        assert "last error" in result.output
        assert "never-fired" in result.output


class TestOnePatternIsStillJudgedOnItsOwn:
    """Widening the question must not widen the answer.

    Two exclusions that leave anything reachable are not a catch-all, and saying
    they were would train a reader to ignore the flag — the failure mode a
    liveness report cannot afford twice.
    """

    def test_two_narrow_exclusions_are_not_reported_as_a_catch_all(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml(
            "guards:\n"
            "  bead-claimed:\n"
            "    exclusions:\n"
            "      - path: 'scripts/**'\n"
            "        reason: 'operational'\n"
            "        until: 'BDL-999'\n"
            "      - path: '*.md'\n"
            "        reason: 'prose'\n"
            "        until: 'BDL-999'\n"
        )

        spec = load_guards_config(tmp_path).spec_for("bead-claimed")

        assert spec.excluded_everywhere() is False
        assert spec.exclusion_for("src/app.py") is None

    def test_a_guard_with_no_exclusions_is_not_a_catch_all(self, tmp_path) -> None:
        spec = load_guards_config(tmp_path).spec_for("bead-claimed")

        assert spec.excluded_everywhere() is False
