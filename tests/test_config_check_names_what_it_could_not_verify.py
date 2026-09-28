# beadloom:domain=onboarding
"""BDL-061 `.57` — closing the measured blind spots `.10` pinned as strict xfails.

``.10`` left nine ``xfail(strict=True)`` statements in
``tests/test_s3_config_check_residual.py``; those are the acceptance criteria and
they live there. This file is the *supporting* half: the properties each fix has
to establish, stated once and directly, so a later reader meets the rule rather
than only the absence of a finding.

Four properties, in the order the bead gives them:

* **the composition is a function of its inputs, and of nothing else.**
  ``composer.py`` asserts it in its own docstring; ``describe()`` denied it by
  calling ``date.today()``. The assertion is the one that was kept, so expiry
  is now computed at CHECK time and reported as a finding — which is also what
  CONTEXT already promised ("a named reason, an exit condition, and it is itself
  reported").
* **the gate is not satisfied by having less to check** — a deleted manifest, a
  deleted provenance stamp and a deleted scaffolded file are each findings, and
  a missing manifest reads ``unverified`` (``.46``/``.47``'s word for "there was
  nothing to compare against"), never absent-and-therefore-fine.
* **a suppression that suppresses nothing says so** — ``.48``'s rule-liveness
  question one layer up, sharing ``exit_condition_deadline`` with the lint
  exemptions (``.49``) rather than restating it.
* **skip is a first-class outcome** — a partially scaffolded repo checks what is
  there and names what is not.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.onboarding import flow_suppression
from beadloom.onboarding.agentic_flow_setup import AGENT_FILES, COMMAND_FILES, scaffold
from beadloom.onboarding.composer import compose
from beadloom.onboarding.config_sync import ConfigDrift, check_config_drift
from beadloom.onboarding.flow_config import load_flow_config
from beadloom.onboarding.flow_manifest import (
    FLOW_MANIFEST_RELPATH,
    ArtifactState,
    classify,
    digest,
)
from beadloom.onboarding.flow_suppression import FlowSuppression
from beadloom.onboarding.role_adapters import generate_adapters
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_FLOW_YML = "tools: [claude]\narchitecture: ddd\nstack: [python]\n"


def _suppressing(rule: str, until: str, reason: str = "the team runs on Windows") -> str:
    return (
        _FLOW_YML
        + "overlays:\n  suppress:\n"
        + f'    - rule: "{rule}"\n      reason: "{reason}"\n      until: "{until}"\n'
    )


def _adopter(tmp_path: Path, *, flow_yml: str = _FLOW_YML) -> Path:
    """A fully scaffolded adopter project — the two calls the CLI command makes."""
    project = tmp_path / "acme-service"
    (project / ".beadloom").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "acme-service"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    (project / ".beadloom" / "flow.yml").write_text(flow_yml, encoding="utf-8")
    config = load_flow_config(project)
    generate_adapters(config, project)
    scaffold(project, include_agents=False)
    return project


def _drifts(project: Path) -> list[ConfigDrift]:
    return check_config_drift(project, sqlite3.connect(":memory:"))


def _cli_exit(project: Path) -> int:
    """``beadloom config-check`` exit code — the Gate's own verdict, not a count."""
    return CliRunner().invoke(main, ["config-check", "--project", str(project)]).exit_code


class _Later(date):
    """A clock three years on. Nothing on disk moves with it."""

    @classmethod
    def today(cls) -> date:
        return date(2100, 1, 1)


class TestTheCompositionIsAFunctionOfItsInputs:
    """``composer.py``'s docstring is the claim that was kept; the clock is gone."""

    def test_the_composed_bytes_do_not_move_with_the_clock(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The same inputs yield the same bytes — on any day, expired or not."""
        # Arrange — an exit condition that passes between the two compositions
        soon = (date.today() + timedelta(days=2)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing("Anti-patterns / Shell", soon))
        config = load_flow_config(project)
        before = compose("claude", "CLAUDE", config=config, project_root=project).text

        # Act — only the clock moves
        monkeypatch.setattr(flow_suppression, "date", _Later)
        after = compose("claude", "CLAUDE", config=config, project_root=project).text

        # Assert
        assert digest(after) == digest(before)

    def test_the_notice_still_carries_the_reason_and_the_exit_condition(self) -> None:
        """Dropping the verdict must not drop what CONTEXT requires be said."""
        # Arrange
        suppression = FlowSuppression(rule="R", reason="why", until="2020-01-01")

        # Act
        described = suppression.describe()

        # Assert — the reason and the exit condition, and no verdict about today
        assert "why" in described
        assert "2020-01-01" in described
        assert "EXPIRED" not in described

    def test_expiry_is_still_computable_it_is_just_not_bytes(self) -> None:
        """The deadline logic is ``.49``'s, shared rather than restated."""
        # Arrange
        suppression = FlowSuppression(rule="R", reason="why", until="2020-01-01")

        # Assert
        assert suppression.expired() is True
        assert suppression.expired(today=date(2019, 1, 1)) is False


class TestASuppressionThatSuppressesNothingSaysSo:
    """``.48``'s rule-liveness question, one layer up from the lint exemptions."""

    def test_an_expired_suppression_is_a_warning_not_a_block(
        self, tmp_path: Path
    ) -> None:
        """It is a real finding; it is not a reason to turn a green repo red."""
        # Arrange
        past = (date.today() - timedelta(days=400)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing("Anti-patterns / Shell", past))

        # Act
        expiry = [d for d in _drifts(project) if "expired" in d.reason.lower()]

        # Assert
        assert [d.severity for d in expiry] == ["warn"]
        assert past in expiry[0].reason

    def test_an_event_shaped_exit_condition_is_never_reported_as_expired(
        self, tmp_path: Path
    ) -> None:
        """Unparseable is not a verdict either way (``.49``'s rule, inherited)."""
        # Arrange
        project = _adopter(
            tmp_path,
            flow_yml=_suppressing("Anti-patterns / Shell", "a windows overlay ships"),
        )

        # Act + Assert
        assert not [d for d in _drifts(project) if "expired" in d.reason.lower()]

    def test_a_suppression_of_a_live_core_rule_is_not_reported(
        self, tmp_path: Path
    ) -> None:
        """The control: the declared channel must stay usable without noise."""
        # Arrange
        future = (date.today() + timedelta(days=90)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing("Anti-patterns / Shell", future))

        # Act + Assert
        assert _drifts(project) == []

    @pytest.mark.parametrize(
        ("label", "rule"),
        [
            ("a rule that lives only in the role protocols", "Cohesion-driven design"),
            ("a rule that lives only in a slash command", "Acceptance criteria"),
        ],
    )
    def test_the_corpus_is_the_whole_composition_not_one_artifact(
        self, tmp_path: Path, label: str, rule: str
    ) -> None:
        """A core rule may live in any composed artifact, so all of them are matched.

        Without this the "suppresses nothing" finding is a false positive for
        every rule stated outside ``CLAUDE.md`` — the shape that teaches people
        to ignore a finding. Measured: dropping the commands and roles from the
        corpus reddens nothing without these two cases.
        """
        # Arrange
        future = (date.today() + timedelta(days=90)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing(rule, future))

        # Act + Assert
        assert not [d for d in _drifts(project) if "stands nothing down" in d.reason], label

    def test_a_rule_name_with_no_words_in_it_owns_nothing(self, tmp_path: Path) -> None:
        """``rule: "///"`` passes the non-empty check and still names no rule."""
        # Arrange
        future = (date.today() + timedelta(days=90)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing("///", future))

        # Act + Assert
        assert [d for d in _drifts(project) if "stands nothing down" in d.reason]

    def test_the_dead_suppression_finding_names_the_rule_and_what_to_do(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        future = (date.today() + timedelta(days=90)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing("Section 42 / Tap dance", future))

        # Act
        dead = [d for d in _drifts(project) if "Section 42" in d.reason]

        # Assert
        assert [d.severity for d in dead] == ["warn"]
        assert dead[0].file == ".beadloom/flow.yml"
        assert "delete" in (dead[0].remediation or "").lower()


class TestAMissingManifestIsUnverifiedNotAbsent:
    """``.46``/``.47``'s word, not a second vocabulary for the same idea."""

    def test_deleting_the_manifest_is_itself_a_finding(self, tmp_path: Path) -> None:
        # Arrange
        project = _adopter(tmp_path)
        assert _drifts(project) == []

        # Act
        (project / FLOW_MANIFEST_RELPATH).unlink()

        # Assert — reported by name, and not blocking on its own
        unverified = [d for d in _drifts(project) if "unverified" in d.reason.lower()]
        assert [d.file for d in unverified] == [str(FLOW_MANIFEST_RELPATH)]
        assert unverified[0].severity == "warn"

    def test_a_repo_that_never_adopted_the_flow_is_not_asked_for_a_manifest(
        self, tmp_path: Path
    ) -> None:
        """The boundary that keeps the #73 false-positive class closed."""
        # Arrange — a project with a CLAUDE.md it wrote itself, nothing scaffolded
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "CLAUDE.md").write_text("# Ours\n", encoding="utf-8")

        # Act + Assert
        assert _drifts(tmp_path) == []

    @pytest.mark.parametrize(
        ("label", "on_disk", "recorded", "accounted", "expected"),
        [
            (
                "no manifest file at all — nothing to compare against",
                "edited",
                None,
                False,
                ArtifactState.UNVERIFIED,
            ),
            (
                "the project keeps a manifest and this body is not in it",
                "edited",
                None,
                True,
                ArtifactState.HAND_EDITED,
            ),
            (
                "we wrote it and it is gone",
                None,
                digest("ours"),
                True,
                ArtifactState.MISSING,
            ),
            (
                "gone, and no manifest to say whether it was ever ours",
                None,
                None,
                False,
                ArtifactState.UNVERIFIED,
            ),
        ],
    )
    def test_provenance_separates_pre_manifest_from_unaccounted_for(
        self,
        label: str,
        on_disk: str | None,
        recorded: str | None,
        accounted: bool,
        expected: ArtifactState,
    ) -> None:
        # Act
        state = classify(
            on_disk=on_disk,
            expected="composed",
            recorded=recorded,
            accounted=accounted,
        )

        # Assert
        assert state is expected, label


class TestSkipIsAFirstClassOutcome:
    """A guard that silently does not apply is indistinguishable from one that passed."""

    @pytest.mark.parametrize(
        "relpath",
        [
            f".claude/agents/{AGENT_FILES[0]}.md",
            f".claude/commands/{COMMAND_FILES[0]}.md",
            ".claude/CLAUDE.md",
        ],
    )
    def test_a_deleted_composed_artifact_names_itself(
        self, tmp_path: Path, relpath: str
    ) -> None:
        """All THREE kinds, because `CLAUDE.md` was the one this missed.

        The agents and commands leg closed with `.10-4`. `CLAUDE.md` did not:
        with the manifest fully intact, deleting it was reported by nothing at
        all — measured, and the same equation one artifact over.
        """
        # Arrange
        project = _adopter(tmp_path)

        # Act
        (project / relpath).unlink()
        gone = [d for d in _drifts(project) if d.file == relpath]

        # Assert — we wrote it, so its disappearance blocks
        assert [d.severity for d in gone] == ["error"]
        assert "missing" in gone[0].reason.lower()

    def test_the_other_files_are_still_checked(self, tmp_path: Path) -> None:
        """One unrelated deletion must not switch the checks off for everything else."""
        # Arrange
        project = _adopter(tmp_path)
        coordinator = project / ".claude" / "commands" / "coordinator.md"
        coordinator.write_text(
            coordinator.read_text(encoding="utf-8") + "\n## Local\nSkip the gate.\n",
            encoding="utf-8",
        )

        # Act
        (project / ".claude" / "agents" / "dev.md").unlink()
        files = {d.file for d in _drifts(project) if d.severity == "error"}

        # Assert
        assert ".claude/commands/coordinator.md" in files
        assert ".claude/agents/dev.md" in files


class TestTheDegradedPathIsNamedNotSilent:
    """When ownership cannot be proved, say so — do not fall back to permissive.

    `.claude/CLAUDE.md` is the one composed artifact with an ownership
    pre-filter, and it exists for a real reason: a project's own hand-written
    `CLAUDE.md` is not ours to police (BDL-UX #73). But the filter returned
    SILENCE where the agents and commands return a verdict, so a project that
    demonstrably adopted the flow could hold a gutted `CLAUDE.md` and the check
    would name it nowhere and exit 0 — measured two ways below.

    The fix is not to accuse: `scaffold()` deliberately refuses to overwrite a
    pre-existing `CLAUDE.md` it did not write (it emits a migration note), so an
    adopter can genuinely have adopted the flow while owning that file, and
    calling it hand-edited would be the false red on upgrade this slice exists to
    prevent. The fix is to NAME it, at `unverified` — `sync-check`'s word for
    "there was nothing to compare against", reported and never blocking.
    """

    @staticmethod
    def _drop_manifest_entry(project: Path, relpath: str) -> None:
        """Leave a present, usable manifest that simply does not mention ``relpath``."""
        path = project / FLOW_MANIFEST_RELPATH
        data = json.loads(path.read_text(encoding="utf-8"))
        data["written"].pop(relpath, None)
        path.write_text(json.dumps(data), encoding="utf-8")

    @pytest.mark.parametrize("degrade", ["manifest_absent", "entry_absent"])
    def test_an_unverifiable_claude_md_is_named(
        self, tmp_path: Path, degrade: str
    ) -> None:
        """Both degraded states, and the second is the worse one.

        With the manifest merely ABSENT there is at least a manifest warning
        pointing somewhere. With the manifest PRESENT and only this entry gone,
        nothing in the output went anywhere near the file.
        """
        # Arrange
        project = _adopter(tmp_path)
        if degrade == "manifest_absent":
            (project / FLOW_MANIFEST_RELPATH).unlink()
        else:
            self._drop_manifest_entry(project, ".claude/CLAUDE.md")

        # Act — a body with no provenance stamp left in it
        (project / ".claude" / "CLAUDE.md").write_text("# gone\n", encoding="utf-8")
        named = [d for d in _drifts(project) if d.file == ".claude/CLAUDE.md"]

        # Assert — named, said in `sync-check`'s word, and NOT blocking
        assert [d.severity for d in named] == ["warn"], degrade
        assert "unverified" in named[0].reason.lower()
        assert _cli_exit(project) == 0

    def test_the_three_composed_kinds_answer_alike(self, tmp_path: Path) -> None:
        """Same deletion, same state, three artifacts — none of them may go quiet.

        This is the measurement that decided the residual: with the manifest
        deleted and all three gutted, `agents/dev.md` and `commands/coordinator.md`
        were named at `unverified` and `CLAUDE.md` was silent. A future change
        that makes any one of them quiet again reddens here.
        """
        # Arrange
        project = _adopter(tmp_path)
        (project / FLOW_MANIFEST_RELPATH).unlink()
        relpaths = [
            ".claude/CLAUDE.md",
            f".claude/agents/{AGENT_FILES[0]}.md",
            f".claude/commands/{COMMAND_FILES[0]}.md",
        ]

        # Act
        for relpath in relpaths:
            (project / relpath).write_text("# gone\n", encoding="utf-8")
        answers = {
            d.file: (d.severity, "unverified" in d.reason.lower())
            for d in _drifts(project)
        }

        # Assert
        assert {r: answers.get(r) for r in relpaths} == {
            r: ("warn", True) for r in relpaths
        }

    def test_a_project_that_never_adopted_the_flow_is_still_not_policed(
        self, tmp_path: Path
    ) -> None:
        """The #73 control, and the reason the fix gates on adoption rather than on nothing."""
        # Arrange — a CLAUDE.md this project wrote, no flow anywhere
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "CLAUDE.md").write_text(
            "# Our house rules\n\nDo whatever you like.\n", encoding="utf-8"
        )

        # Act + Assert
        assert _drifts(tmp_path) == []

    def test_the_stamped_hand_edit_still_blocks(self, tmp_path: Path) -> None:
        """The control that the degraded path did not become the ONLY path."""
        # Arrange
        project = _adopter(tmp_path)
        claude_md = project / ".claude" / "CLAUDE.md"

        # Act — the stamp survives, so ownership is proved and the verdict is a verdict
        claude_md.write_text(
            claude_md.read_text(encoding="utf-8") + "\n## Local\nSkip the gate.\n",
            encoding="utf-8",
        )
        named = [d for d in _drifts(project) if d.file == ".claude/CLAUDE.md"]

        # Assert
        assert [d.severity for d in named] == ["error"]
        assert "hand-edited" in named[0].reason
        assert _cli_exit(project) == 1
