"""Guard configuration validation — the ways a gate is switched off quietly (BDL-061 S1).

``tests/test_guards.py`` proves a missing ``reason`` and a missing ``until`` are
rejected one at a time. This module covers the rest of the surface: both missing,
a missing ``path``, values that are present but empty, entries of the wrong shape,
and every malformed-``flow.yml`` corner — because each of them is a way to end up
with a guard that looks configured and checks nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from beadloom.application.guards.config import (
    DEFAULT_STRICTNESS,
    STRICTNESS_VALUES,
    GuardConfigError,
    build_guards_config,
    load_guards_config,
)

_EXCLUSION_HEAD = "guards:\n  bead-claimed:\n    exclusions:\n"


def _exclusion(**fields: str) -> str:
    """Render a ``guards:`` block with one exclusion declaring exactly *fields*."""
    if not fields:
        return _EXCLUSION_HEAD + "      - {}\n"
    items = list(fields.items())
    lines = [f"      - {items[0][0]}: {items[0][1]}"]
    lines += [f"        {key}: {value}" for key, value in items[1:]]
    return _EXCLUSION_HEAD + "\n".join(lines) + "\n"


class TestExclusionRequiredFields:
    """``path`` + ``reason`` + ``until`` — all three, all non-empty."""

    @pytest.mark.parametrize(
        ("fields", "expected_missing"),
        [
            ({"path": "'scripts/**'"}, ["reason", "until"]),
            ({"reason": "'why'", "until": "'BDL-1'"}, ["path"]),
            ({"path": "'scripts/**'", "until": "'BDL-1'"}, ["reason"]),
            ({"path": "'scripts/**'", "reason": "'why'"}, ["until"]),
            ({}, ["path", "reason", "until"]),
        ],
    )
    def test_a_missing_field_is_a_config_error_that_names_it(
        self, tmp_path, write_flow_yml, fields, expected_missing
    ) -> None:
        write_flow_yml(_exclusion(**fields))

        with pytest.raises(GuardConfigError) as exc:
            load_guards_config(tmp_path)

        message = str(exc.value)
        assert "bead-claimed" in message
        for name in expected_missing:
            assert name in message

    @pytest.mark.parametrize("empty", ["''", "'   '", "null"])
    @pytest.mark.parametrize("field_name", ["path", "reason", "until"])
    def test_a_present_but_empty_field_counts_as_missing(
        self, tmp_path, write_flow_yml, field_name, empty
    ) -> None:
        """``reason: ""`` is how an unnamed exclusion sneaks past a presence check."""
        fields = {"path": "'scripts/**'", "reason": "'why'", "until": "'BDL-1'"}
        fields[field_name] = empty
        write_flow_yml(_exclusion(**fields))

        with pytest.raises(GuardConfigError, match=field_name):
            load_guards_config(tmp_path)

    def test_surrounding_whitespace_is_stripped_from_every_field(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml(
            _exclusion(path="'  scripts/**  '", reason="'  why  '", until="'  BDL-1  '")
        )

        spec = load_guards_config(tmp_path).spec_for("bead-claimed")

        exclusion = spec.exclusions[0]
        assert (exclusion.path, exclusion.reason, exclusion.until) == (
            "scripts/**",
            "why",
            "BDL-1",
        )
        assert spec.exclusion_for("scripts/deploy.sh") is not None

    def test_an_unquoted_date_is_accepted_as_an_expiry(self, tmp_path, write_flow_yml) -> None:
        """PyYAML hands back a ``date``; an expiry a human would type must still load."""
        write_flow_yml(_exclusion(path="'scripts/**'", reason="'why'", until="2026-12-31"))

        exclusion = load_guards_config(tmp_path).spec_for("bead-claimed").exclusions[0]

        assert exclusion.until == "2026-12-31"
        assert "2026-12-31" in exclusion.describe()

    def test_an_exclusion_entry_that_is_not_a_mapping_is_rejected(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml(_EXCLUSION_HEAD + "      - 'scripts/**'\n")

        with pytest.raises(GuardConfigError, match="mappings"):
            load_guards_config(tmp_path)

    def test_exclusions_that_are_not_a_list_are_rejected(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  bead-claimed:\n    exclusions: 'scripts/**'\n")

        with pytest.raises(GuardConfigError, match="list"):
            load_guards_config(tmp_path)

    def test_an_empty_exclusion_list_is_valid_and_excludes_nothing(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  bead-claimed:\n    exclusions: []\n")

        spec = load_guards_config(tmp_path).spec_for("bead-claimed")

        assert spec.exclusions == ()
        assert spec.exclusion_for("anything/at/all.py") is None
        assert spec.excluded_everywhere() is False


class TestStrictnessValidation:
    def test_an_unquoted_off_is_honoured_as_the_strictness_word(
        self, tmp_path, write_flow_yml
    ) -> None:
        """YAML 1.1 turns bare ``off`` into ``False``; the shipped example uses it."""
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: off, epic: on}\n")

        with pytest.raises(GuardConfigError) as exc:
            load_guards_config(tmp_path)
        assert "on" in str(exc.value)

        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: off}\n")
        assert load_guards_config(tmp_path).spec_for("bead-claimed").strictness_for(None) == "off"

    def test_the_error_names_every_allowed_strictness(self, tmp_path, write_flow_yml) -> None:
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {default: strict}\n")

        with pytest.raises(GuardConfigError) as exc:
            load_guards_config(tmp_path)

        message = str(exc.value)
        assert "strict" in message
        for allowed in STRICTNESS_VALUES:
            assert allowed in message

    def test_strictness_that_is_not_a_mapping_is_rejected(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: warn\n")

        with pytest.raises(GuardConfigError, match="mapping"):
            load_guards_config(tmp_path)

    @pytest.mark.parametrize("value", ["[warn]", "{a: b}", "7", "1.5"])
    def test_a_non_string_strictness_value_is_rejected(
        self, tmp_path, write_flow_yml, value
    ) -> None:
        """Regression (BDL-061.2): an unhashable value crashed with TypeError.

        The crash escaped ``GuardConfigError``, so the CLI never reached its
        exit-3 path and Click exited 1 — the *warn* code. A malformed
        configuration was therefore indistinguishable from a warning verdict for
        any adapter that reads only the exit code, which is every adapter.
        """
        write_flow_yml(f"guards:\n  bead-claimed:\n    strictness: {{default: {value}}}\n")

        with pytest.raises(GuardConfigError, match="strings"):
            load_guards_config(tmp_path)

    @pytest.mark.parametrize("value", ["0", "1"])
    def test_an_integer_strictness_is_rejected_rather_than_read_as_on_or_off(
        self, tmp_path, write_flow_yml, value
    ) -> None:
        """Regression (BDL-061.2): ``0 == False`` in a dict lookup switched a guard off.

        The bool coercion was a lookup keyed by the value, so ``default: 0``
        resolved to ``"off"`` — an integer silently disabling a gate, which is
        precisely what the reason/until rule exists to prevent.
        """
        write_flow_yml(f"guards:\n  bead-claimed:\n    strictness: {{default: {value}}}\n")

        with pytest.raises(GuardConfigError, match="strings"):
            load_guards_config(tmp_path)

    def test_an_empty_strictness_mapping_leaves_the_shipped_default(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  bead-claimed:\n    strictness: {}\n")

        spec = load_guards_config(tmp_path).spec_for("bead-claimed")

        assert spec.strictness_for("epic") == DEFAULT_STRICTNESS == "warn"


class TestOptionsValidation:
    def test_options_that_are_not_a_mapping_are_rejected(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  working-branch:\n    options: [trunk]\n")

        with pytest.raises(GuardConfigError, match="mapping"):
            load_guards_config(tmp_path)

    def test_a_non_string_option_value_is_rejected(self, tmp_path, write_flow_yml) -> None:
        write_flow_yml("guards:\n  working-branch:\n    options: {trunk: 7}\n")

        with pytest.raises(GuardConfigError, match="strings"):
            load_guards_config(tmp_path)

    def test_options_default_to_empty(self, tmp_path, write_flow_yml) -> None:
        write_flow_yml("guards:\n  working-branch: {}\n")

        assert dict(load_guards_config(tmp_path).spec_for("working-branch").options) == {}


class TestFileLevelShape:
    def test_an_absent_file_yields_the_shipped_defaults(self, tmp_path) -> None:
        config = load_guards_config(tmp_path)

        assert config.declared_names() == ()
        assert config.spec_for("bead-claimed").declared is False

    def test_an_empty_file_yields_the_shipped_defaults(self, tmp_path, write_flow_yml) -> None:
        write_flow_yml("")

        assert load_guards_config(tmp_path).declared_names() == ()

    def test_a_file_with_no_guards_block_yields_the_shipped_defaults(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("architecture: ddd\nstack: python\n")

        assert load_guards_config(tmp_path).declared_names() == ()

    def test_a_null_guards_block_yields_the_shipped_defaults(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n")

        assert load_guards_config(tmp_path).declared_names() == ()

    def test_invalid_yaml_is_reported_as_a_guard_config_error(
        self, tmp_path, write_flow_yml
    ) -> None:
        """A YAMLError escaping here would reach the CLI as a crash, not exit 3."""
        write_flow_yml("guards:\n  bead-claimed: [unclosed\n")

        with pytest.raises(GuardConfigError, match="invalid YAML"):
            load_guards_config(tmp_path)

    def test_a_top_level_list_is_rejected(self, tmp_path, write_flow_yml) -> None:
        write_flow_yml("- guards\n- more\n")

        with pytest.raises(GuardConfigError, match="top-level"):
            load_guards_config(tmp_path)

    def test_a_guards_block_that_is_not_a_mapping_is_rejected(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards: [bead-claimed]\n")

        with pytest.raises(GuardConfigError, match="guards"):
            load_guards_config(tmp_path)

    def test_a_guard_body_that_is_not_a_mapping_is_rejected(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  bead-claimed: warn\n")

        with pytest.raises(GuardConfigError, match="mapping"):
            load_guards_config(tmp_path)

    def test_an_empty_guard_body_still_counts_as_declared(
        self, tmp_path, write_flow_yml
    ) -> None:
        """``declared`` drives the liveness report's source column — it must not lie."""
        write_flow_yml("guards:\n  bead-claimed:\n")

        config = load_guards_config(tmp_path)

        assert config.spec_for("bead-claimed").declared is True
        assert config.spec_for("working-branch").declared is False
        assert config.declared_names() == ("bead-claimed",)

    def test_an_unknown_guard_name_error_lists_the_registered_guards(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  bead-clamied: {}\n")

        with pytest.raises(GuardConfigError) as exc:
            load_guards_config(tmp_path)

        message = str(exc.value)
        assert "bead-clamied" in message
        assert "bead-claimed" in message
        assert "working-branch" in message

    def test_declared_names_are_sorted_regardless_of_file_order(
        self, tmp_path, write_flow_yml
    ) -> None:
        write_flow_yml("guards:\n  working-branch: {}\n  bead-claimed: {}\n")

        assert load_guards_config(tmp_path).declared_names() == (
            "bead-claimed",
            "working-branch",
        )

    def test_a_spec_for_a_name_nobody_registered_falls_back_rather_than_crashing(
        self,
    ) -> None:
        spec = build_guards_config({}).spec_for("not-a-guard")

        assert spec.declared is False
        assert spec.strictness_for(None) == DEFAULT_STRICTNESS


class TestEventRoutingIsNotDeclaredHere:
    """``on:`` is gone from the schema — deleted, not quoted (owner decision, 2026-08-22).

    It was a documented capability wired to nothing: ``GuardSpec.events`` was
    written by the loader and read by no code path, while which tool calls count
    as an edit lives in the harness matcher. Standing rule 8 — a permission
    without a caller is not a capability — makes that a defect in the product,
    not only in the docs, so the key is removed rather than spelled correctly.
    Quoting it would have kept the promise and added nothing behind it.

    It returns, wired to a consumer, in S3 where composition and adapters are
    reworked.
    """

    def test_the_effective_spec_carries_no_event_list(self, tmp_path, write_flow_yml) -> None:
        write_flow_yml("guards:\n  bead-claimed: {}\n")

        spec = load_guards_config(tmp_path).spec_for("bead-claimed")

        assert not hasattr(spec, "events")

    def test_a_registered_guard_declares_no_default_events(self) -> None:
        from beadloom.application.guards.checks import BUILTIN_GUARDS

        for guard in BUILTIN_GUARDS.values():
            assert not hasattr(guard, "default_events")

    def test_the_shipped_dogfood_config_declares_no_events(self) -> None:
        """Our own flow.yml must not teach an incantation that does nothing."""
        repo_root = Path(__file__).resolve().parent.parent
        body = yaml.safe_load((repo_root / ".beadloom" / "flow.yml").read_text(encoding="utf-8"))

        for name, declared in (body.get("guards") or {}).items():
            keys = set(declared or {})
            assert "on" not in keys, name
            # YAML 1.1 reads a bare `on` as the boolean True — the spelling that
            # made the dead key invisible in the first place.
            assert True not in keys, name


