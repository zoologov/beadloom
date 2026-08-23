# beadloom:domain=onboarding
"""S3 verification — where the NEW ``config-check`` still cannot see.

``.9`` established that before this slice the ``.claude/CLAUDE.md`` body was
verified by **nothing**: replacing the whole file with ``# gone`` produced zero
drifts and a green Gate. That is fixed, and ``tests/test_flow_composition.py``
owns the proof. This file is the adversarial half — a check that was totally
blind and is now partly sighted is the highest-prior place to look for what is
left, so each case below was MEASURED on a scaffolded temp project at
``7d6221f`` before it was written down.

What the measurements found, in the order they appear:

* the strictness of the whole body check rests on a generated file. ``rm
  .beadloom/flow-manifest.json`` turns a hand edit from ``error`` into ``warn``
  (CLI exit 1 → 0); deleting the one-line ``<!-- beadloom:composed`` stamp as
  well produces **zero** findings.
* ``_agentic_flow_scaffolded`` is an all-or-nothing precondition with no
  ``skip`` verdict: deleting ONE scaffolded file switches off the checks for
  every other one (measured: a hand-edited ``coordinator.md`` went from exit 1
  to exit 0 when ``.claude/agents/dev.md`` was removed), and the deletion itself
  is reported by nothing.
* a suppression reuses ``exit_condition_deadline`` but inherits neither finding
  that function exists to feed: an entry naming a rule that appears nowhere in
  the composed core is accepted in silence (the ``_dead_finding`` case), and an
  expired one is reported by nothing (the ``_expired_finding`` case) while
  silently changing the composition — so an untouched repo turns red on a date,
  under a reason that names a cause which did not happen.
* overlays are append-only in BYTES, which holds and is pinned here, but not in
  EFFECT: a project fragment may contradict a core rule with no reason, no exit
  condition and no notice — the declared channel that demands all three is the
  route nobody has to take.

Findings carry ``xfail(strict=True)``: the gap is an executable statement, and
the day it closes the marker fails the suite rather than letting it be
forgotten. Every class also carries at least one PASSING test on the same
fixtures, so no ``xfail`` here can be an artefact of a broken helper (TESTS MUST
BITE).
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import date, timedelta
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.onboarding import composer, flow_suppression
from beadloom.onboarding.agentic_flow_setup import AGENT_FILES, COMMAND_FILES, scaffold
from beadloom.onboarding.composer import COMPOSED_MARKER, compose, templates_dir
from beadloom.onboarding.config_sync import ConfigDrift, check_config_drift
from beadloom.onboarding.flow_config import load_flow_config
from beadloom.onboarding.flow_manifest import (
    FLOW_MANIFEST_RELPATH,
    ArtifactState,
    classify,
    digest,
    load_manifest,
    record,
    state_of,
)
from beadloom.onboarding.flow_suppression import (
    FlowSuppressionError,
    build_suppression,
    build_suppressions,
)
from beadloom.onboarding.role_adapters import generate_adapters
from beadloom.onboarding.role_composer import compose_all_roles
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_FLOW_YML = "tools: [claude]\narchitecture: ddd\nstack: [python]\n"

_SUPPRESSION_HEADING = "Project rule suppressions"

#: A project-layer fragment: the supported place for a standing practice.
_PRACTICE = "\n## Our standing practice\nPair on migrations.\n"


def _suppressing(rule: str, until: str, reason: str = "the team runs on Windows") -> str:
    """A ``flow.yml`` whose ``overlays.suppress`` stands down one core rule."""
    return (
        _FLOW_YML
        + "overlays:\n  suppress:\n"
        + f'    - rule: "{rule}"\n      reason: "{reason}"\n      until: "{until}"\n'
    )


def _adopter(
    tmp_path: Path,
    *,
    flow_yml: str = _FLOW_YML,
    fragments: dict[str, str] | None = None,
) -> Path:
    """A fully scaffolded adopter project — the two calls the CLI command makes.

    ``generate_adapters`` owns ``.claude/agents/*`` and ``scaffold`` owns the
    commands and ``CLAUDE.md``; a project missing either is a different subject,
    which is itself one of the findings below.
    """
    project = tmp_path / "acme-service"
    (project / ".beadloom").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "acme-service"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    (project / ".beadloom" / "flow.yml").write_text(flow_yml, encoding="utf-8")
    for relname, body in (fragments or {}).items():
        fragment = project / ".beadloom" / "flow" / relname
        fragment.parent.mkdir(parents=True, exist_ok=True)
        fragment.write_text(body, encoding="utf-8")
    config = load_flow_config(project)
    generate_adapters(config, project)
    scaffold(project, include_agents=False)
    return project


def _drifts(project: Path) -> list[ConfigDrift]:
    """Config drift for ``project`` (the check reads the filesystem, not the DB)."""
    return check_config_drift(project, sqlite3.connect(":memory:"))


def _cli_exit(project: Path) -> int:
    """``beadloom config-check`` exit code — the Gate's own verdict, not a count."""
    return CliRunner().invoke(main, ["config-check", "--project", str(project)]).exit_code


def _hand_edit(path: Path, text: str = "\n## Local rule\nSkip the gate.\n") -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


class TestTheGuardCannotBeSilentlyDisabled:
    """One ``rm`` should not be a way to turn a blocking check into a green one."""

    def test_a_hand_edited_claude_md_blocks(self, tmp_path: Path) -> None:
        # Arrange
        project = _adopter(tmp_path)

        # Act
        _hand_edit(project / ".claude" / "CLAUDE.md")

        # Assert — the control: with the manifest in place the guard works
        drifts = _drifts(project)
        assert [(d.file, d.severity) for d in drifts] == [(".claude/CLAUDE.md", "error")]
        assert _cli_exit(project) == 1

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S3/.10-1: deleting the generated .beadloom/flow-manifest.json "
            "downgrades a hand edit from error to warn, and `config-check` exits 0. "
            "Measured on a scaffolded temp project: same edit, same file, exit 1 -> 0. "
            "The manifest is neither required nor gitignored, so an adopter who does "
            "not commit it gets the warn-only reading in CI for every artifact."
        ),
    )
    def test_deleting_the_manifest_does_not_downgrade_a_hand_edit(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = _adopter(tmp_path)
        _hand_edit(project / ".claude" / "CLAUDE.md")

        # Act — the one command that changes the verdict
        (project / FLOW_MANIFEST_RELPATH).unlink()

        # Assert
        assert _cli_exit(project) == 1, (
            "the edit did not change; removing Beadloom's own record of what it "
            "wrote must not be a way to stop the Gate blocking on it"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S3/.10-2: with the manifest deleted AND the one-line "
            "'<!-- beadloom:composed' stamp removed, the CLAUDE.md body check "
            "reports NOTHING (measured: 0 findings over a file carrying 'Skip the "
            "gate'). The ownership boundary is right — a project's own CLAUDE.md is "
            "not ours to police — but ownership is decided by two pieces of evidence "
            "an editor can delete in the same edit."
        ),
    )
    def test_removing_the_provenance_stamp_does_not_silence_the_body_check(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = _adopter(tmp_path)
        claude_md = project / ".claude" / "CLAUDE.md"
        _hand_edit(claude_md)

        # Act — delete both pieces of evidence that the file is Beadloom's
        (project / FLOW_MANIFEST_RELPATH).unlink()
        claude_md.write_text(
            "".join(
                line
                for line in claude_md.read_text(encoding="utf-8").splitlines(keepends=True)
                if COMPOSED_MARKER not in line
            ),
            encoding="utf-8",
        )

        # Assert
        assert _drifts(project), (
            "a file Beadloom composed, still holding its scaffolded body, must not "
            "become unpoliced because two lines were removed"
        )

    def test_a_hand_edited_command_blocks(self, tmp_path: Path) -> None:
        # Arrange
        project = _adopter(tmp_path)

        # Act
        _hand_edit(project / ".claude" / "commands" / "coordinator.md")

        # Assert — the control for the two findings below
        assert [d.file for d in _drifts(project)] == [".claude/commands/coordinator.md"]
        assert _cli_exit(project) == 1

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S3/.10-3: _agentic_flow_scaffolded is an all-or-nothing "
            "precondition with no `skip` verdict, so deleting ONE scaffolded file "
            "switches the flow checks off for every OTHER file. Measured: a "
            "hand-edited coordinator.md reported at exit 1; `rm "
            ".claude/agents/dev.md`; the same edit, exit 0, silent on both streams. "
            "CONTEXT: 'a guard that silently does not apply is indistinguishable "
            "from one that passed'."
        ),
    )
    def test_a_missing_file_does_not_switch_off_the_checks_on_the_others(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = _adopter(tmp_path)
        _hand_edit(project / ".claude" / "commands" / "coordinator.md")

        # Act
        (project / ".claude" / "agents" / "dev.md").unlink()

        # Assert
        assert _cli_exit(project) == 1, (
            "the hand edit to coordinator.md is still there; removing an unrelated "
            "file must not make it disappear from the report"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S3/.10-4: a scaffolded file that has been DELETED is reported "
            "by nothing. _agentic_flow_drifts skips the whole repo and "
            "_composed_adapter_drifts skips absent files one by one, so 'the role "
            "protocol is gone' and 'the role protocol is intact' are the same green."
        ),
    )
    @pytest.mark.parametrize(
        ("subdir", "name"), [("agents", AGENT_FILES[0]), ("commands", COMMAND_FILES[0])]
    )
    def test_a_deleted_scaffolded_file_is_reported(
        self, tmp_path: Path, subdir: str, name: str
    ) -> None:
        # Arrange
        project = _adopter(tmp_path)

        # Act
        (project / ".claude" / subdir / f"{name}.md").unlink()

        # Assert
        assert _drifts(project), f".claude/{subdir}/{name}.md was deleted and nothing said so"


class TestSuppressionMustEarnItsPlace:
    """A suppression is a declaration; the epic's rule is that one which owns nothing says so."""

    def test_a_live_suppression_reaches_every_composed_artifact(
        self, tmp_path: Path
    ) -> None:
        """The declared channel works, on all three kinds — roles included (.9's gap)."""
        # Arrange
        future = (date.today() + timedelta(days=90)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing("Anti-patterns / Shell", future))
        config = load_flow_config(project)

        # Act
        claude_md = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        roles = compose_all_roles(config, project)
        command = compose("commands", "coordinator", config=config, project_root=project)

        # Assert — the notice, the reason and the exit condition, in each kind
        for label, text in (
            ("CLAUDE.md", claude_md),
            ("role:dev", roles["dev"]),
            ("command:coordinator", command.text),
        ):
            assert _SUPPRESSION_HEADING in text, label
            assert "the team runs on Windows" in text, label
            assert future in text, label
        assert "Anti-patterns / Shell" in claude_md
        assert _drifts(project) == [], "a declared suppression is not drift"

    def test_an_expired_suppression_is_marked_in_the_composed_text(
        self, tmp_path: Path
    ) -> None:
        """The control for the two findings below: the expiry IS computed."""
        # Arrange
        past = (date.today() - timedelta(days=1)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing("Anti-patterns / Shell", past))

        # Act
        claude_md = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")

        # Assert
        assert "EXPIRED" in claude_md

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S3/.10-5: a suppression naming a rule that appears NOWHERE in "
            "the composed core is accepted, rendered into every artifact as a "
            "decision, and reported by nothing. graph.rules.exemptions — whose "
            "exit_condition_deadline this module deliberately reuses — reports "
            "exactly this case for an import exemption ('suppresses nothing ... "
            "delete it'). Suppressions inherit the function and not the finding."
        ),
    )
    def test_a_suppression_that_matches_no_core_rule_is_reported(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        future = (date.today() + timedelta(days=90)).isoformat()
        project = _adopter(
            tmp_path, flow_yml=_suppressing("Section 42 / Interpretive dance", future)
        )

        # Act
        composed = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")

        # Assert
        assert "Section 42 / Interpretive dance" not in composed.split(
            _SUPPRESSION_HEADING
        )[0], "precondition: the rule really is absent from the core"
        assert _drifts(project), (
            "a suppression that stands down nothing is a decision nobody can act on"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S3/.10-6: an EXPIRED suppression is reported by nothing. The "
            "composed text gains the word EXPIRED and the Gate says 'agent-config in "
            "sync'. The exemption surface reports the same condition as a finding "
            "('expired on <date> and is still suppressing N crossings', BDL-061 S2b)."
        ),
    )
    def test_an_expired_suppression_is_reported(self, tmp_path: Path) -> None:
        # Arrange
        past = (date.today() - timedelta(days=400)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing("Anti-patterns / Shell", past))

        # Act
        drifts = _drifts(project)

        # Assert
        assert any("expired" in d.reason.lower() for d in drifts), (
            f"the exit condition passed on {past} and the suppression still stands: "
            f"got {[d.reason for d in drifts]}"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S3/.10-7: the composition is a function of the CLOCK, which the "
            "composer's own docstring denies ('the same inputs always yield the same "
            "bytes'). FlowSuppression.describe() appends ' — EXPIRED' on the day the "
            "exit condition passes, so an untouched repo goes from 0 findings to one "
            "ERROR overnight — and the reason it prints, 'composed body is stale vs "
            "CORE + the flow.yml overlays + the project layer', names a cause that "
            "did not happen: nothing moved but the date."
        ),
    )
    def test_the_clock_alone_does_not_turn_an_untouched_repo_red(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — a live suppression, a clean project, nothing edited afterwards
        soon = (date.today() + timedelta(days=2)).isoformat()
        project = _adopter(tmp_path, flow_yml=_suppressing("Anti-patterns / Shell", soon))
        assert _drifts(project) == []

        class _Later(date):
            @classmethod
            def today(cls) -> date:
                return date(2100, 1, 1)

        # Act — only the clock moves
        monkeypatch.setattr(flow_suppression, "date", _Later)
        drifts = _drifts(project)

        # Assert
        blocking = [d for d in drifts if d.severity == "error"]
        assert not blocking or all("expire" in d.reason.lower() for d in blocking), (
            "a repo nobody touched must not go red on a date under a reason that "
            f"blames the composition: got {[(d.severity, d.reason) for d in drifts]}"
        )


class TestOverlaySurvivesAnUpgradeOfTheCoreUnderneathIt:
    """PLAN's two S3 criteria in their awkward form: the SHIPPED core moves."""

    @pytest.fixture()
    def upgradable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Redirect the composer at a writable copy of the shipped templates.

        The upgrade this slice has to survive happens upstream — a new Beadloom
        release changes the CORE under a project layer that is already in place.
        Editing the adopter's own file (which
        ``test_core_drift_still_caught_while_an_overlay_exists`` does) is the
        other direction and cannot show this one.
        """
        vendored = tmp_path / "shipped-templates"
        shutil.copytree(templates_dir(), vendored)
        monkeypatch.setattr(composer, "templates_dir", lambda: vendored)
        return vendored

    @staticmethod
    def _upgrade_core(vendored: Path, line: str) -> None:
        core = vendored / "agentic_flow" / "CLAUDE.md.txt"
        core.write_text(core.read_text(encoding="utf-8") + line, encoding="utf-8")

    def test_a_core_change_underneath_an_overlay_is_reported_as_recomposable(
        self, tmp_path: Path, upgradable: Path
    ) -> None:
        # Arrange — an adopter with a project layer, clean before the upgrade
        project = _adopter(tmp_path, fragments={"claude/CLAUDE.md": _PRACTICE})
        assert _drifts(project) == []

        # Act — the shipped core moves, the project does not
        self._upgrade_core(upgradable, "\n## 10. New core rule\nAlways re-read the graph.\n")
        drifts = _drifts(project)

        # Assert — recomposable, NOT 'hand-edited': the adopter changed nothing
        assert [(d.file, d.severity) for d in drifts] == [(".claude/CLAUDE.md", "error")]
        assert "hand-edited" not in drifts[0].reason
        assert "setup-agentic-flow" in (drifts[0].remediation or "")

    def test_recomposing_adopts_the_new_core_and_keeps_the_overlay(
        self, tmp_path: Path, upgradable: Path
    ) -> None:
        # Arrange
        project = _adopter(tmp_path, fragments={"claude/CLAUDE.md": _PRACTICE})
        self._upgrade_core(upgradable, "\n## 10. New core rule\nAlways re-read the graph.\n")

        # Act — the remediation the finding names
        scaffold(project, include_agents=False)

        # Assert
        composed = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Always re-read the graph." in composed, "the upgrade did not land"
        assert "Pair on migrations." in composed, "the overlay did not survive"
        assert composed.index("Always re-read the graph.") < composed.index(
            "Pair on migrations."
        ), "the project layer composes AFTER the core, or it cannot be append-only"
        assert _drifts(project) == []

    def test_a_hand_edit_made_before_the_upgrade_is_still_not_rewritten(
        self, tmp_path: Path, upgradable: Path
    ) -> None:
        """#151's destructive ``--fix`` must not return by way of an upgrade."""
        # Arrange
        project = _adopter(tmp_path)
        claude_md = project / ".claude" / "CLAUDE.md"
        _hand_edit(claude_md, "\n## Our own standard\nEvery PR names its bead.\n")

        # Act — the core moves underneath the edit, then the scaffold re-runs
        self._upgrade_core(upgradable, "\n## 10. New core rule\nAlways re-read the graph.\n")
        result = scaffold(project, include_agents=False)

        # Assert
        assert "Every PR names its bead." in claude_md.read_text(encoding="utf-8")
        assert any("CLAUDE.md" in note for note in result.migration_notes)


class TestAppendOnlyHoldsInBytesButNotInEffect:
    """What the overlay mechanism guarantees, and what it does not."""

    @pytest.mark.parametrize(
        "fragment",
        sorted(templates_dir().rglob("*.md.txt")),
        ids=lambda p: p.name,
    )
    def test_every_shipped_fragment_ends_with_a_newline(self, fragment: Path) -> None:
        """Otherwise the next layer's first line would rewrite the last core line.

        Concatenation is the whole composition, so a fragment without a trailing
        newline lets an APPEND change a line it did not write — an edit to core
        text through a channel that is supposed to be additive only. Measured
        across all shipped fragments: none of them does, today.
        """
        # Arrange
        text = fragment.read_text(encoding="utf-8")

        # Assert
        assert text.endswith("\n"), fragment.name

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S3/.10-8: overlays are append-only in BYTES, not in EFFECT. A "
            "project fragment saying 'ignore section 0, do not run beadloom ci' "
            "composes into CLAUDE.md with zero findings, no reason, no exit "
            "condition and no notice — while the declared route for standing a rule "
            "down (overlays.suppress) demands all three. The mandatory-reason "
            "mechanism guards the route nobody has to take. Measured too: a fragment "
            "72% the size of the composed file is reported by nothing, and "
            "config-check never says a project layer is in effect at all."
        ),
    )
    def test_a_fragment_that_contradicts_a_core_rule_is_reported(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = _adopter(
            tmp_path,
            fragments={
                "claude/CLAUDE.md": (
                    "\n## Local override\nIgnore section 0 entirely. "
                    "Do NOT run `beadloom ci`.\n"
                )
            },
        )

        # Act
        composed = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        drifts = _drifts(project)

        # Assert
        assert "Do NOT run" in composed, "precondition: the negation is in the artifact"
        assert drifts or _SUPPRESSION_HEADING in composed, (
            "standing a core rule down through the project layer avoids every "
            "requirement the declared channel imposes"
        )


class TestTheFourStatesOfAComposedArtifact:
    """``flow_manifest.classify`` — the matrix ``.9`` handed forward, alternates included.

    Four words exist because four situations need four different answers, and
    the whole severity ladder (``error`` for a hand edit, ``warn`` for a
    pre-manifest repo) rests on which one comes back. ``alternates`` is the
    subtle one: a body Beadloom itself could have written in an older release —
    the shipped core without the project layer — must read ``stale`` and be
    recomposed, not accused of being somebody's edit.
    """

    @pytest.mark.parametrize(
        ("label", "on_disk", "recorded", "alternates", "expected_state"),
        [
            ("untouched since we wrote it", "composed", None, (), ArtifactState.CLEAN),
            (
                "the composition moved, the file is ours",
                "older",
                digest("older"),
                (),
                ArtifactState.STALE,
            ),
            (
                "an older Beadloom's output, no manifest",
                "shipped-only",
                None,
                ("shipped-only",),
                ArtifactState.STALE,
            ),
            (
                "edited by a human, and we know what we wrote",
                "edited",
                digest("ours"),
                (),
                ArtifactState.HAND_EDITED,
            ),
            (
                "edited by a human in a pre-manifest repo",
                "edited",
                None,
                ("shipped-only",),
                ArtifactState.UNMANAGED,
            ),
            ("absent file, no record", None, None, (), ArtifactState.UNMANAGED),
            ("absent file, recorded", None, digest("ours"), (), ArtifactState.HAND_EDITED),
        ],
    )
    def test_the_state_matrix(
        self,
        label: str,
        on_disk: str | None,
        recorded: str | None,
        alternates: tuple[str, ...],
        expected_state: ArtifactState,
    ) -> None:
        # Act
        state = classify(
            on_disk=on_disk,
            expected="composed",
            recorded=recorded,
            alternates=alternates,
        )

        # Assert
        assert state is expected_state, label

    def test_an_alternate_wins_over_a_recorded_digest(self) -> None:
        """A body we could have written is recomposable even if the record disagrees."""
        # Act
        state = classify(
            on_disk="shipped-only",
            expected="composed",
            recorded=digest("something else entirely"),
            alternates=("shipped-only",),
        )

        # Assert
        assert state is ArtifactState.STALE

    @pytest.mark.parametrize(
        ("label", "body"),
        [
            ("not JSON at all", "{{{"),
            ("JSON, but not an object", "[1, 2, 3]"),
            ("an object without `written`", '{"version": 1}'),
            ("`written` of the wrong type", '{"version": 1, "written": []}'),
        ],
    )
    def test_an_unreadable_manifest_reads_as_no_record(
        self, tmp_path: Path, label: str, body: str
    ) -> None:
        """A corrupt manifest must not be read as "we wrote this" — it has no entries.

        The consequence is the honest one and it is the same as a repo that
        never had a manifest: ``unmanaged``, reported, not silently clean.
        """
        # Arrange
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / FLOW_MANIFEST_RELPATH).write_text(body, encoding="utf-8")

        # Act
        entries = load_manifest(tmp_path)

        # Assert
        assert entries == {}, label
        assert (
            state_of(tmp_path, "any.md", expected="composed") is ArtifactState.UNMANAGED
        )

    def test_recording_nothing_does_not_create_a_manifest(self, tmp_path: Path) -> None:
        """An empty write is not a write: a run that composed nothing records nothing."""
        # Act
        record(tmp_path, {})

        # Assert
        assert not (tmp_path / FLOW_MANIFEST_RELPATH).exists()

    def test_recording_merges_rather_than_replaces(self, tmp_path: Path) -> None:
        """Dropping the artifacts this run did not touch would make them unmanaged."""
        # Arrange
        (tmp_path / ".beadloom").mkdir()
        record(tmp_path, {"a.md": digest("a")})

        # Act
        record(tmp_path, {"b.md": digest("b")})

        # Assert
        assert load_manifest(tmp_path) == {"a.md": digest("a"), "b.md": digest("b")}

    def test_a_directory_where_a_file_should_be_is_not_a_crash(self, tmp_path: Path) -> None:
        """``state_of`` answers about the disk, which may hold something unreadable."""
        # Arrange — the artifact path exists but is not a readable file
        (tmp_path / "artifact.md").mkdir()

        # Act
        state = state_of(tmp_path, "artifact.md", expected="composed", manifest={})

        # Assert
        assert state is ArtifactState.UNMANAGED


class TestAMalformedSuppressionIsALoudConfigError:
    """The declared channel's input validation — the half an attacker reaches first.

    ``build_suppressions`` is the only door into a suppression, and everything
    downstream (the notice, the expiry, the composed bytes) trusts what comes
    out of it. A silently-accepted malformed entry is a suppression nobody
    declared.
    """

    @pytest.mark.parametrize(
        ("label", "entry"),
        [
            ("a bare string instead of a mapping", "Anti-patterns / Shell"),
            ("a list instead of a mapping", ["rule", "reason", "until"]),
            ("a misspelt key", {"rule": "R", "reason": "r", "untill": "2099-01-01"}),
            (
                "an extra key that means nothing",
                {"rule": "R", "reason": "r", "until": "x", "force": True},
            ),
            ("no reason", {"rule": "R", "until": "2099-01-01"}),
            ("a whitespace-only reason", {"rule": "R", "reason": "   ", "until": "2099-01-01"}),
            ("no exit condition", {"rule": "R", "reason": "r"}),
            ("an empty exit condition", {"rule": "R", "reason": "r", "until": ""}),
            ("no rule", {"reason": "r", "until": "2099-01-01"}),
            ("nothing at all", {}),
        ],
    )
    def test_a_malformed_entry_is_rejected(self, label: str, entry: object) -> None:
        # Act + Assert
        with pytest.raises(FlowSuppressionError):
            build_suppression(entry)

    def test_a_suppress_key_that_is_not_a_list_is_rejected(self) -> None:
        # Act + Assert
        with pytest.raises(FlowSuppressionError, match="list of mappings"):
            build_suppressions({"rule": "R"})

    def test_an_absent_suppress_key_is_not_an_error(self) -> None:
        """A project that suppresses nothing composes exactly as before the feature."""
        # Act + Assert
        assert build_suppressions(None) == ()

    def test_a_malformed_suppression_surfaces_through_config_check(
        self, tmp_path: Path
    ) -> None:
        """Not as a traceback: the same channel every other flow.yml defect uses."""
        # Arrange — a valid project, then a suppression missing its exit condition
        project = _adopter(tmp_path)
        (project / ".beadloom" / "flow.yml").write_text(
            _FLOW_YML + 'overlays:\n  suppress:\n    - rule: "R"\n      reason: "r"\n',
            encoding="utf-8",
        )

        # Act
        drifts = _drifts(project)

        # Assert
        assert [d.file for d in drifts] == [".beadloom/flow.yml"]
        assert "until" in drifts[0].reason.lower()
        assert _cli_exit(project) == 1

    def test_an_exit_condition_written_as_a_yaml_date_still_expires(
        self, tmp_path: Path
    ) -> None:
        """``until: 2020-01-01`` unquoted parses as a date object, not a string."""
        # Arrange
        project = tmp_path / "acme"
        (project / ".beadloom").mkdir(parents=True)
        (project / ".beadloom" / "flow.yml").write_text(
            _FLOW_YML
            + 'overlays:\n  suppress:\n    - rule: "R"\n      reason: "r"\n'
            + "      until: 2020-01-01\n",
            encoding="utf-8",
        )

        # Act
        config = load_flow_config(project)

        # Assert
        assert config.suppressions[0].until == "2020-01-01"
        assert config.suppressions[0].expired() is True

    def test_an_event_shaped_exit_condition_never_expires(self) -> None:
        """Unparseable is not a verdict either way — it must not read as expired."""
        # Act
        suppression = build_suppression(
            {"rule": "R", "reason": "r", "until": "when BDL-0xx ships a windows overlay"}
        )

        # Assert
        assert suppression.expired() is False
        assert "EXPIRED" not in suppression.describe()
