"""Where two of S4's eight instruments state one fact, they state it once.

BDL-068 S4 applied one technique eight times — derive an instrument's
enforcement surface from its own matcher, compare it against what exists, report
the gap — through eight agents in six waves, none of whom could see the others.
Each bead's own suite covers its own instrument. What no bead's suite could cover
is the JOIN, and this file is only that: four places where two beads landed on
one fact, one protocol or one approval, and nothing held them together.

Every assertion here is a BOUNDARY GUARD written after the behaviour, per the
house standard three dev beads of this slice declared. None of them is red on the
tree today; each is red on a one-sided edit to a pair that currently agrees,
which is the only thing a seam test can be worth.

The four joins, with the beads that made them:

* ``beadloom-0mdo.31`` wrote the tool population TWICE — as the matcher string
  ``guard_hooks.EDIT_MATCHER`` the scaffolder emits, and as the classification
  ``surface.WRITE_TOOLS`` the report measures against. Two hand-written lists of
  one fact in two domains, and ``beadloom-mr2l.82`` is this repository's measured
  precedent for what happens next.
* ``beadloom-en0x`` states that the wave plan and the commit gate read one
  approval through one function. Its own suite constructs ``WorkItemAxes``
  directly, so the sentence is asserted nowhere.
* ``beadloom-0mdo.32`` and ``beadloom-gsal`` each added a leg to the SAME two
  hook templates, agreeing by hand on a verdict marker, on where the verdict
  goes and on the word for a comparison that could not be made. The populations
  below are read out of the template text, so a third leg is covered by being
  added rather than by anyone editing this file.
* ``beadloom-0mdo.27``'s duty report is a claim about the COMPOSITION and
  ``config_sync``'s drift check is a claim about the artifact on disk. Delivery
  to a role that actually reads a file needs both, and the pair is asserted by
  neither bead.

A fifth section was added by ``beadloom-0mdo.41`` after the test bead measured
the join above and found the one place the eight instruments genuinely disagree:
``.31`` answers its question off DISK and ``.27`` answers it off the
COMPOSITION, and neither said which. Both questions are legitimate and this file
does not make them the same — what it binds is that each report NAMES the one it
answered, and that an empty population never prints as a covered one
(BDL-UX #239, #241).
"""

from __future__ import annotations

import json
import re
import shlex
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.declared_scope import (
    VERDICT_MARKER,
    scope_check,
    work_item_axes,
)
from beadloom.application.guards.surface import WRITE_TOOLS, build_surface
from beadloom.application.typed_surface import SurfaceRoot, TypedSurface
from beadloom.application.waves.media import ROOM_PREFIX
from beadloom.onboarding.guard_hooks import (
    EDIT_MATCHER,
    HOOK_EVENT,
    SETTINGS_RELPATH,
    hook_command,
)
from beadloom.onboarding.role_adapters import TOOL_AGENT_DIRS
from beadloom.onboarding.role_duties import CARRIES_MARKER, duty_report
from beadloom.services.cli import main
from beadloom.services.commands.docsync import (
    _HOOK_TEMPLATE_BLOCK,
    _HOOK_TEMPLATE_PRE_PUSH,
    _HOOK_TEMPLATE_WARN,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: This repository's own branch, and the work item it names. Used only where the
#: assertion needs a project that HAS an index: resolving a work item's axes
#: needs one, which a bare `tmp_path` cannot supply.
_OWN_BRANCH = "features/BDL-068"
_OWN_WORK_ITEM = "BDL-068"

#: The one duty this project declares, named so the room assertion below cannot
#: quietly pass over a corpus that declares something else.
_CLEAN_ROOM = "clean-room"

#: The word three of this slice's instruments use for a population that was read
#: and holds nothing. Asserted rather than agreed on by hand: `beadloom-gsal`
#: introduced it for the typed leg, and `.31` and `.27` needed it three waves
#: later for exactly the same distinction.
_NOTHING_TO_CHECK = "NOTHING TO CHECK"


# ---------------------------------------------------------------------------
# One fact, one home
# ---------------------------------------------------------------------------


class TestOneFactHasOneHome:
    """The write-tool population is written twice, in two domains."""

    def test_the_shipped_matcher_names_exactly_the_tools_classified_as_writing(
        self,
    ) -> None:
        """`EDIT_MATCHER` and `WRITE_TOOLS` are one fact with two spellings.

        `onboarding.guard_hooks.EDIT_MATCHER` decides which tool invocations the
        harness routes to a guard. `application.guards.surface.WRITE_TOOLS`
        decides which granted tools the surface report calls a write path. A
        sixth write tool added to either alone ships a binding that is narrower
        than its own report says, or a report that measures against a population
        the scaffolder does not bind — and nothing before this line compared
        them.

        The precedent is measured, not hypothetical: `beadloom-mr2l.82` wrote a
        surface into the commit-hook template, the declaration that decided it
        then moved, and the template did not (BDL-UX #231).
        """
        assert set(EDIT_MATCHER.split("|")) == set(WRITE_TOOLS)


# ---------------------------------------------------------------------------
# One approval, read once
# ---------------------------------------------------------------------------


class TestOneApprovalIsReadOnce:
    """`waves` and `scope-check` judge one work item through one read.

    `declared_scope.work_item_axes` states in its own docstring that it is "a
    second RENDERING of the read `scope_of_branch` already makes, never a second
    read", because a commit gate and a wave plan disagreeing about one approval
    is the two-homes class BDL-068 exists to remove. `beadloom-en0x`'s unit
    suite builds `WorkItemAxes` literals and never calls the function, so the
    sentence was carried by the docstring alone.

    The three reasons below are the whole population of ways the read can fail —
    `scope_of_branch` returns `(None, reason)` on each — and a rendering that
    dropped or reworded any of them would let the plan and the gate print
    different accounts of the same absent approval.
    """

    @pytest.fixture()
    def documents(self, tmp_path: Path) -> Path:
        """A project whose planning documents name exactly one work item."""
        folder = tmp_path / ".claude" / "development" / "docs" / "features" / "KEY-1"
        folder.mkdir(parents=True)
        (folder / "RFC.md").write_text("# RFC\n", encoding="utf-8")
        return tmp_path

    def test_no_branch_gives_both_the_same_reason(self, documents: Path) -> None:
        assert scope_check(documents, branch=None).reason == (
            work_item_axes(documents, branch=None).reason
        )

    def test_a_branch_naming_no_work_item_gives_both_the_same_reason(
        self, documents: Path
    ) -> None:
        run = scope_check(documents, branch="features/NOPE")
        axes = work_item_axes(documents, branch="features/NOPE")
        assert run.reason == axes.reason
        assert run.reason is not None, "the fixture must not resolve a work item"

    def test_no_index_gives_both_the_same_reason(self, documents: Path) -> None:
        """A resolvable work item and no index: the read fails after the branch."""
        run = scope_check(documents, branch="features/KEY-1")
        axes = work_item_axes(documents, branch="features/KEY-1")
        assert run.reason == axes.reason
        assert run.reason is not None, "the fixture must not carry an index"

    def test_a_resolved_approval_is_named_identically_by_both(
        self, live_repo_reindexed: Path
    ) -> None:
        """The positive case, on the one project that has an index.

        Measured against this repository rather than a synthetic tree: resolving
        a work item needs a built index, and a fixture reindexed inside the test
        would be measuring the fixture's own graph.

        It takes `live_repo_reindexed` rather than reading the ambient
        `.beadloom/beadloom.db`, and it asserts over the APPROVAL rather than
        over the run's verdict. Both are corrections a clean room made to this
        test, in that order. Reading the ambient index, it passed on the tree
        and failed in a room, because `git archive` carries no gitignored index
        and the read stopped at `NO_INDEX`. Requiring `run.reason is None`, it
        then failed again, because `scope_check` goes on to ask git which paths
        the commit changes and a room has no `.git` — `GIT_SILENT`.

        The second failure is the sharper statement of what these two functions
        share. They read the approval once and diverge immediately afterwards:
        only `scope_check` needs a working tree, and `work_item_axes` answers a
        plan-time question that has none. So the shared half is the work item and
        the document it was read from, and `run.reason` is deliberately not
        asserted here — it is a fact about the tree the run was taken in, and
        pinning it is what made this assertion room-dependent twice (BDL-UX
        #236's class, inside a test about instruments that must not be).
        """
        run = scope_check(live_repo_reindexed, branch=_OWN_BRANCH)
        axes = work_item_axes(live_repo_reindexed, branch=_OWN_BRANCH)
        assert axes.reason is None, axes.reason
        assert run.work_item == axes.work_item == _OWN_WORK_ITEM
        assert run.document == axes.document
        assert axes.document, "the fixture must resolve a document to compare"


# ---------------------------------------------------------------------------
# One porcelain protocol between two hook legs
# ---------------------------------------------------------------------------

#: A leg of a hook template that captures a Beadloom command's porcelain output.
#: Read out of the template text so that a leg added after this file is covered
#: by existing, not by an edit here.
_PRODUCER = re.compile(
    r"(\w+)_report=\$\((?:[^)]*?\|\s*)?beadloom "
    r"((?:[a-z][a-z-]*)(?:\s+--[a-z-]+)*)"
)

#: How a leg splits the verdict line off the payload, and how it drops it again.
_VERDICT_PARSE = re.compile(r"sed -n 's/\^(.+?)//p'")
_PAYLOAD_FILTER = re.compile(r"grep -v '\^(.+?)'")

#: The branch a leg takes when its command produced no verdict at all.
_NO_VERDICT_BRANCH = re.compile(r'if \[ -z "\$(\w+)_verdict" \]')

_TEMPLATES = {
    "warn": _HOOK_TEMPLATE_WARN,
    "block": _HOOK_TEMPLATE_BLOCK,
    "pre-push": _HOOK_TEMPLATE_PRE_PUSH,
}


def _producers() -> Iterator[tuple[str, str, str]]:
    """Every (template, variable, invocation) the shipped hooks parse."""
    for name, body in _TEMPLATES.items():
        for variable, invocation in _PRODUCER.findall(body):
            yield name, variable, invocation


class TestTheTwoGateLegsShareOnePorcelainProtocol:
    """`beadloom-0mdo.32` and `beadloom-gsal` edited the same two templates.

    Wave 2 added the declared-axes leg and wave 5 added the typed-surface leg,
    three waves apart and without either agent seeing the other's code. They
    agreed on three things by writing them the same way: the marker that leads a
    verdict, the shape that drops the verdict from the payload, and the word for
    a comparison that could not be made. Nothing enforced any of the three.

    Each population below is derived from the template text and asserted
    non-empty, because a regex that silently matched nothing would make every
    assertion in this class pass over an empty set — the phantom this epic is
    named for, in a test about it.
    """

    def test_the_templates_carry_at_least_two_parsed_legs(self) -> None:
        """The population these assertions run over, stated before they run."""
        found = list(_producers())
        assert len(found) >= 2, found

    def test_every_verdict_parse_strips_the_declared_marker(self) -> None:
        """No leg spells the marker for itself.

        `declared_scope.VERDICT_MARKER` says in its own comment that "a marker
        the producer and the consumer each spell for themselves is two things
        that can disagree". Both consumers live in shell, where the constant
        cannot be imported, so the agreement is checkable only from here.
        """
        for name, body in _TEMPLATES.items():
            for stripped in _VERDICT_PARSE.findall(body):
                assert stripped == VERDICT_MARKER, (name, stripped)

    def test_every_payload_filter_excludes_the_declared_marker(self) -> None:
        """The other half of the split: what the verdict parse takes, this drops."""
        for name, body in _TEMPLATES.items():
            for excluded in _PAYLOAD_FILTER.findall(body):
                assert excluded == VERDICT_MARKER, (name, excluded)

    def test_the_two_halves_of_the_split_are_paired_in_every_template(self) -> None:
        """A leg that took a verdict and did not drop it would print it twice."""
        for name, body in _TEMPLATES.items():
            legs = len(_PRODUCER.findall(body))
            assert len(_VERDICT_PARSE.findall(body)) == legs, name
            assert len(_PAYLOAD_FILTER.findall(body)) == legs, name

    def test_every_parsed_leg_has_a_word_for_having_compared_nothing(self) -> None:
        """A leg whose command returns no verdict must not print silence.

        This is the epic's own rule applied to the gate a committer reads: a run
        that could not compare must say a different word from a run that
        compared and found nothing. Both existing legs assign a `NOT CHECKED`
        sentence in that branch; a third leg added without one would be red here
        rather than quietly clean at the moment it could say least.
        """
        for name, body in _TEMPLATES.items():
            producers = {variable for variable, _ in _PRODUCER.findall(body)}
            fallbacks = set(_NO_VERDICT_BRANCH.findall(body))
            assert producers == fallbacks, (name, producers, fallbacks)
            for variable in producers:
                assignment = re.search(
                    rf'{variable}_verdict="([^"]+)"',
                    body,
                )
                assert assignment is not None, (name, variable)
                assert "NOT CHECKED" in assignment.group(1), (name, variable)

    @pytest.mark.parametrize(
        ("template", "variable", "invocation"),
        list(_producers()),
        ids=lambda value: str(value).replace(" ", "_"),
    )
    def test_the_command_a_leg_parses_leads_its_output_with_the_marker(
        self,
        template: str,
        variable: str,
        invocation: str,
        tmp_path: Path,
    ) -> None:
        """Run each producer the templates name, in the state that says least.

        A bare directory is deliberately the fixture: it is the state in which a
        producer has the least to say, and therefore the one where a producer
        that dropped the marker would still look plausible to a reader of its
        output. The consumer's `sed` takes line one or nothing, so leading the
        stream is the contract, not merely emitting the marker somewhere.
        """
        result = CliRunner().invoke(
            main, [*shlex.split(invocation), "--project", str(tmp_path)], input=""
        )
        first = (result.stdout.splitlines() or [""])[0]
        assert first.startswith(VERDICT_MARKER), (template, variable, result.stdout)


# ---------------------------------------------------------------------------
# A duty, and the file the role actually opens
# ---------------------------------------------------------------------------


@pytest.fixture()
def scaffolded(tmp_path: Path) -> Path:
    """A project with the flow written to disk, as an adopter has it."""
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(
        "tools:\n- claude\narchitecture:\n- ddd\nstack:\n- python\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(main, ["setup-agentic-flow", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    return tmp_path


class TestADutyReachesTheFileTheRoleReads:
    """`beadloom-0mdo.27`'s check and `config_sync`'s drift check are one pair.

    `duty_report` composes every flow artifact in memory and asks whether the
    duty declared for a role reaches that role's COMPOSED core. It never opens
    `.claude/agents/dev.md`, which is the file the role is actually handed. So
    the sentence "the duty is delivered" is true of the composition and says
    nothing on its own about disk, and the second half of the answer lives in a
    different module written by a different bead.

    Both halves are asserted here, in the order a reader needs them: the limit
    first, so nobody reads the duty report as a claim it does not make, then the
    check that covers it.
    """

    def test_the_duty_report_is_a_claim_about_the_composition(self, scaffolded: Path) -> None:
        """Stripping the carriage marker from disk leaves the report unchanged.

        Not a defect and not an accident — `duty_report` is deliberately about
        what the composer produces. It is asserted so that the next reader of a
        clean duty line knows which of the two questions it answered, and so
        that a later change making the report read disk breaks here rather than
        silently overlapping the drift check.
        """
        before = duty_report(scaffolded)
        assert before.declarations, "the shipped flow must declare a duty"
        assert before.findings == (), before.findings

        adapter = scaffolded / ".claude" / "agents" / "dev.md"
        assert CARRIES_MARKER in adapter.read_text(encoding="utf-8")
        adapter.write_text(
            adapter.read_text(encoding="utf-8").replace(CARRIES_MARKER, ""),
            encoding="utf-8",
        )

        assert duty_report(scaffolded).findings == ()

    def test_the_artifact_on_disk_is_covered_by_the_drift_check_instead(
        self, scaffolded: Path
    ) -> None:
        """The other half: a role core that stopped carrying the duty blocks.

        `config-check` byte-compares each scaffolded adapter against its
        composition, so a core the composer says carries the duty and the disk
        says does not is a blocking drift finding. The two checks are one
        answer, and this is the assertion that says so.
        """
        clean = CliRunner().invoke(main, ["config-check", "--project", str(scaffolded)])
        assert clean.exit_code == 0, clean.output

        adapter = scaffolded / ".claude" / "agents" / "dev.md"
        adapter.write_text(
            adapter.read_text(encoding="utf-8").replace(CARRIES_MARKER, ""),
            encoding="utf-8",
        )

        drifted = CliRunner().invoke(main, ["config-check", "--project", str(scaffolded)])
        assert drifted.exit_code == 1, drifted.output
        # The finding must NAME the adapter. Asserting only that some drift was
        # reported passed a mutation that removed the agents from the vendored
        # byte-compare entirely — a survivor that was a finding about this test,
        # not about the code (`beadloom-nn4c`'s lesson, met here).
        assert ".claude/agents/dev.md" in drifted.output, drifted.output


# ---------------------------------------------------------------------------
# One spelling of the room a bead measures in
# ---------------------------------------------------------------------------


class TestOneSpellingOfTheRoom:
    """The planner's room path and the role core's room path are one spelling.

    `beadloom-67t1` shipped the `room-<bead-id>` rule in two places, because
    that is where it has to be: `waves.media.ROOM_PREFIX` for the plan a
    coordinator reads, and English prose in the composed role core for the agent
    that has to build the directory. Its own comment says the three homes are
    "all three on one spelling bound by a test"; two of them are —
    `test_bead22_wave_guarantee` binds `room_for` to the working-tree statement,
    `test_wave_plan` binds it to itself — and the role core is the one that was
    not.

    That gap is the class `beadloom-67t1` was filed against, one level up: a rule
    the machine and the performer each spell for themselves is two things that
    can disagree, and the performer's copy is prose, which no compiler reads.

    The role population is DERIVED from the duty declaration rather than listed,
    so a sixth role named in a `roles=` list enters this assertion by being
    named.
    """

    def test_every_role_the_duty_names_is_told_the_path_the_planner_prints(
        self, scaffolded: Path
    ) -> None:
        report = duty_report(scaffolded)
        declarations = [d for d in report.declarations if d.duty == _CLEAN_ROOM]
        assert declarations, [d.duty for d in report.declarations]

        roles = sorted({role for d in declarations for role in d.roles})
        assert roles, declarations

        spelling = f"`{ROOM_PREFIX}<bead-id>`"
        for role in roles:
            adapter = scaffolded / ".claude" / "agents" / f"{role}.md"
            assert adapter.is_file(), adapter
            body = adapter.read_text(encoding="utf-8")
            assert spelling in body, (role, spelling)


# ---------------------------------------------------------------------------
# One question, and the sentence that says which one was answered
# ---------------------------------------------------------------------------


def _emit_binding(root: Path, *, matcher: str, front_matter: str) -> None:
    """Write the two artifacts the binding surface is derived from.

    Local to this file on purpose: `test_guard_surface.py` has a helper of its
    own that takes the `tools:` grant as a comma string, and the case below is
    precisely the grant that helper cannot express.
    """
    settings = root / SETTINGS_RELPATH
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    HOOK_EVENT: [
                        {
                            "matcher": matcher,
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": hook_command("bead-claimed"),
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    agents = root / TOOL_AGENT_DIRS["claude"]
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "dev.md").write_text(front_matter, encoding="utf-8")


@pytest.fixture()
def declared_but_unscaffolded(tmp_path: Path) -> Path:
    """A project that declares the flow and has written none of it to disk.

    `setup-agentic-flow` never run: `.beadloom/flow.yml` and nothing else. This
    is the state BDL-UX #241 was reproduced in, and it is reached by running
    `beadloom init` and stopping there.
    """
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(
        "tools:\n- claude\narchitecture:\n- ddd\nstack:\n- python\n",
        encoding="utf-8",
    )
    return tmp_path


class TestEachInstrumentSaysWhichQuestionItAnswered:
    """The one place S4's eight instruments disagree, made visible instead of same.

    `beadloom-0mdo.31` and `beadloom-0mdo.27` landed in the SAME WAVE and
    answered "does a declared thing reach the role that must carry it?" in
    opposite ways. `.31` reads the artifacts ON DISK and reports `unresolved`
    when it cannot read one, with its reasoning recorded: the scaffolder merges
    hook entries on the command string, so a project scaffolded before this
    release keeps its narrower matcher across an upgrade, and only disk can say
    so. `.27` judges the COMPOSITION, which is equally defensible — `--fix`
    writes compositions and the drift check covers the artifact — but said
    nowhere that it had made a choice.

    Both questions are legitimate and this file does not make them the same. What
    is asserted is that each instrument NAMES the question it answered in the
    sentence it prints, so the divergence reads as a design decision rather than
    as two commands that appear to agree and do not (BDL-UX #239, #241).
    """

    def test_the_binding_surface_names_the_artifacts_it_was_read_from(
        self, scaffolded: Path
    ) -> None:
        """`.31`'s report says: disk, not the composition."""
        result = CliRunner().invoke(
            main, ["guard", "--liveness", "--project", str(scaffolded)]
        )
        assert result.exit_code == 0, result.output
        assert SETTINGS_RELPATH.as_posix() in result.output, result.output
        assert TOOL_AGENT_DIRS["claude"].as_posix() in result.output, result.output
        assert "ON DISK" in result.output, result.output

    def test_the_duty_line_names_the_corpus_it_was_read_from(
        self, scaffolded: Path
    ) -> None:
        """`.27`'s report says: the composition, not the files on disk.

        The disk half is asserted in BOTH directions. A first version of this
        test checked only that the empty case says so, and a mutant returning an
        empty file list unconditionally survived it — the scaffolded project
        would then have been told its composition reached no reader, which is
        the same false sentence pointed the other way.
        """
        result = CliRunner().invoke(
            main, ["config-check", "--project", str(scaffolded)]
        )
        assert result.exit_code == 0, result.output
        assert "COMPOSITION" in result.output, result.output
        assert "not the role files on disk" in result.output, result.output

        on_disk = sorted((scaffolded / ".claude" / "agents").glob("*.md"))
        assert on_disk, scaffolded
        assert f"On disk: {len(on_disk)} role file(s)" in result.output, result.output
        assert _NOTHING_TO_CHECK not in result.output, result.output

    def test_an_empty_write_path_population_is_not_a_bound_one(
        self, tmp_path: Path
    ) -> None:
        """BDL-UX #239, in the sharpest of its three reproductions.

        The adapter is present, correct and grants `Bash` and `Edit` — as a YAML
        block sequence, which `_declared_tools` reads only in the comma form. So
        the population is empty while nothing is wrong on disk, and `0 of 0`
        read as every write path bound. The parser is deliberately NOT widened
        here: what the finding is about is the sentence, and a report whose
        population is empty for ANY reason must not print a fraction.
        """
        _emit_binding(
            tmp_path,
            matcher=EDIT_MATCHER,
            front_matter="---\nname: dev\ntools:\n  - Bash\n  - Edit\n---\n\nbody\n",
        )
        surface = build_surface(tmp_path)

        assert surface.unresolved == (), surface.to_dict()
        assert surface.write_paths == (), surface.to_dict()
        assert surface.covered is None, surface.to_dict()
        assert surface.nothing_to_check is True, surface.to_dict()
        assert "0 of 0" not in surface.describe(), surface.describe()

    def test_a_readable_empty_population_is_not_an_unreadable_one(
        self, tmp_path: Path
    ) -> None:
        """The distinction the fix must not lose: two states, not one.

        `.31` got the UNREADABLE case exactly right and its docstring states the
        rule outright. Collapsing the empty case into `unresolved` would answer
        #239 by making the report claim a source could not be read when every
        source was read, which is a false statement in the other direction.
        """
        _emit_binding(
            tmp_path,
            matcher=EDIT_MATCHER,
            front_matter="---\nname: dev\ntools: Read, Grep\n---\n\nbody\n",
        )
        readable = build_surface(tmp_path)
        assert readable.nothing_to_check is True, readable.to_dict()
        assert readable.unresolved == (), readable.to_dict()

        (tmp_path / SETTINGS_RELPATH).unlink()
        unreadable = build_surface(tmp_path)
        assert unreadable.nothing_to_check is False, unreadable.to_dict()
        assert unreadable.unresolved != (), unreadable.to_dict()
        assert unreadable.covered is None, unreadable.to_dict()

    def test_a_composition_no_role_file_can_receive_is_reported_as_such(
        self, declared_but_unscaffolded: Path
    ) -> None:
        """BDL-UX #241: the reassuring line is printed by the unprotected state.

        The exit code deliberately does not change. A project that has not
        scaffolded the flow is not in drift, and turning that into a blocking
        verdict would fail a repository for a state `config-check` has always
        held to be legitimate. What changes is that the run says the composition
        it checked reaches no file yet.
        """
        result = CliRunner().invoke(
            main, ["config-check", "--project", str(declared_but_unscaffolded)]
        )
        assert result.exit_code == 0, result.output
        assert "no role adapter" in result.output, result.output

    def test_the_three_instruments_spell_an_empty_population_one_way(
        self, tmp_path: Path, declared_but_unscaffolded: Path
    ) -> None:
        """`gsal`'s typed leg, `.31`'s surface and `.27`'s duty line, one word.

        `beadloom-gsal` shipped `NOTHING TO CHECK` as a third sentence beside a
        verdict and `NOT CHECKED` three waves before either of the other two
        needed it. Three modules spelling one distinction three ways is the class
        this file exists to bind, so the word is asserted across all three rather
        than left to agree by hand.
        """
        empty_typed = TypedSurface(
            roots=(SurfaceRoot(path="src/demo", source="declared"),),
        ).partition(("other/alpha.py",))
        assert _NOTHING_TO_CHECK in empty_typed.describe(), empty_typed.describe()

        # A directory of its own: `declared_but_unscaffolded` is built on the
        # same `tmp_path`, and writing a role adapter into it would scaffold the
        # very project whose emptiness the third assertion is about.
        binding = tmp_path / "binding"
        binding.mkdir()
        _emit_binding(
            binding,
            matcher=EDIT_MATCHER,
            front_matter="---\nname: dev\ntools: Read, Grep\n---\n\nbody\n",
        )
        assert _NOTHING_TO_CHECK in build_surface(binding).describe()

        result = CliRunner().invoke(
            main, ["config-check", "--project", str(declared_but_unscaffolded)]
        )
        assert _NOTHING_TO_CHECK in result.output, result.output
