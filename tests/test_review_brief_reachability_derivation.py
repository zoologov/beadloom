"""The reachability report's two load-bearing properties, attacked (BDL-068 S2).

`tests/test_review_brief_reachability.py` pins the report `beadloom-0mdo.18`
built. This file attacks the two properties that report stands or falls on, in
the places the first pass left unseeded:

1. **The channels are DERIVED, not listed.** A hand-written list satisfies a
   report test and goes stale the first time a prompt gains a document, which is
   the shape this epic exists to remove. The first pass asserted that *more than
   one* role and *at least one* command are read; measured, `roles/test` and
   `roles/explore` name no shipped document at all, so dropping either from the
   composition survives every assertion written so far. What is asserted here is
   seeded from the POPULATIONS — :data:`ROLE_NAMES` and the command fragments the
   package ships — so a sixth role enters this test by being added to the
   package and by no other act.

2. **The direction of the statement.** `inspected=False` with nothing found must
   never read as `inspected=True` with nothing found: that is `Population`'s rule
   (BDL-068 S1) one layer up, and it is one string away from collapsing. The
   first pass asserted it for one channel and for the bare dataclass. What is
   asserted here is the invariant over the whole report, iterated from the
   report itself, so a fifth channel is covered the day it is added.

The two also meet: a report whose channel NAMES change with what could be
answered is a report that omits a channel nobody could inspect, which is
BDL-UX #204 restored.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.review_brief import (
    Commit,
    bead_comments_channel,
    commit_bodies_channel,
    prompts_naming_documents,
    reachability_of,
    work_item_documents_channel,
)
from beadloom.application.review_brief.models import AuthorNote
from beadloom.onboarding.composer import Composition, LayerFragment, templates_dir
from beadloom.onboarding.flow_config import FlowConfig
from beadloom.onboarding.role_composer import ROLE_NAMES

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.review_brief.models import Reachability

#: Where the shipped planning globs look for a work item's folder.
_PLANNING_ROOT = (".claude", "development", "docs", "features")

#: The suffix a shipped command fragment carries. Read here rather than imported
#: from the module under test on purpose: a test that borrows the derivation it
#: is checking agrees with itself no matter what either says.
_FRAGMENT_SUFFIX = ".md.txt"

#: An author's own words, in a shape nothing this report legitimately prints
#: would ever produce.
_PROSE = "the rounding moved to the boundary because two callers rounded twice"


def _shipped_commands() -> tuple[str, ...]:
    """Every command fragment the package ships, read off the directory."""
    core = templates_dir() / "agentic_flow" / "commands"
    return tuple(
        sorted(path.name[: -len(_FRAGMENT_SUFFIX)] for path in core.glob(f"*{_FRAGMENT_SUFFIX}"))
    )


def _project_fragment(project: Path, kind: str, name: str, text: str) -> None:
    """A project-layer prompt fragment: the team's own layer of one prompt."""
    fragment = project / ".beadloom" / "flow" / kind / f"{name}.md"
    fragment.parent.mkdir(parents=True, exist_ok=True)
    fragment.write_text(text, encoding="utf-8")


def _work_item(project: Path, key: str, *documents: str, body: str = "") -> Path:
    folder = project.joinpath(*_PLANNING_ROOT, key)
    folder.mkdir(parents=True, exist_ok=True)
    for name in documents:
        (folder / name).write_text(f"# {name}\n\n{body}\n", encoding="utf-8")
    return folder


def _seeded(project: Path, prompts: dict[str, tuple[str, str]]) -> dict[str, str]:
    """One novel document per prompt, written into that prompt's project layer.

    ``prompts`` maps a report label to ``(kind, name)``. The returned mapping is
    ``{document: label}`` — what the report must say if every prompt in the
    population is composed, and nothing in it is spelled by hand.
    """
    expected: dict[str, str] = {}
    for index, (label, (kind, name)) in enumerate(sorted(prompts.items())):
        document = f"SEEDED-{index}.md"
        _project_fragment(project, kind, name, f"Read `{document}` before you judge.\n")
        expected[document] = label
    return expected


def _worlds(project: Path) -> dict[str, Reachability]:
    """The same report over the two worlds that differ in what could be answered.

    ``knowable``: a work item the branch names, a range git answered for, an
    author who wrote. ``blind``: no branch, no answer from git, nobody wrote.
    Every channel is present in both; only the answers differ.
    """
    _work_item(project, "ALPHA-1", "CONTEXT.md")
    return {
        "knowable": reachability_of(
            notes=[AuthorNote(text=_PROSE, author="dev", created="2026-09-03")],
            project_root=project,
            branch="features/ALPHA-1",
            commits=[Commit(sha="0f1e2d3", subject="the fix", body_lines=4)],
            since="main",
        ),
        "blind": reachability_of(
            notes=(),
            project_root=project,
            branch=None,
            commits=None,
            since="main",
        ),
    }


class TestThePopulationOfPromptsIsDerivedAndNotListed:
    """Assertion 1: adding a document to a composed prompt moves the report.

    Both halves are seeded from the shipped populations. A hand-written list of
    documents passes nothing here, and a hand-written list of PROMPTS — the
    weaker mistake, and the one the first pass could not see — fails the moment
    the package ships a role or a command the list forgot.
    """

    def test_every_role_the_package_ships_is_composed_into_the_report(
        self, tmp_path: Path
    ) -> None:
        """Seeded from `ROLE_NAMES`, so a sixth role needs no edit here.

        `roles/test` and `roles/explore` name no shipped document, so they are
        invisible to any assertion made over the shipped prompts alone. Giving
        each role its own project layer makes every one of them observable.
        """
        project = tmp_path / "proj"
        project.mkdir()
        assert len(ROLE_NAMES) > 1, ROLE_NAMES
        expected = _seeded(
            project, {f"roles/{role} (project layer)": ("roles", role) for role in ROLE_NAMES}
        )

        naming = prompts_naming_documents(project)
        unread = {
            document: label
            for document, label in expected.items()
            if label not in naming.get(document, ())
        }
        assert not unread, f"these prompts were never composed into the report: {unread}"

    def test_every_command_fragment_the_package_ships_is_composed_into_the_report(
        self, tmp_path: Path
    ) -> None:
        """Seeded from the shipped commands directory, for the same reason.

        A coordinator composes every one of these, so a document named in any of
        them can reach a reviewer — and three of the four name no document the
        other prompts do not already name, which is what makes a dropped command
        invisible without this.
        """
        project = tmp_path / "proj"
        project.mkdir()
        commands = _shipped_commands()
        assert len(commands) > 1, commands
        expected = _seeded(
            project,
            {f"commands/{name} (project layer)": ("commands", name) for name in commands},
        )

        naming = prompts_naming_documents(project)
        unread = {
            document: label
            for document, label in expected.items()
            if label not in naming.get(document, ())
        }
        assert not unread, f"these prompts were never composed into the report: {unread}"

    def test_a_document_two_layers_of_one_prompt_name_is_attributed_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The repeat a project cannot construct, and the mutant that survived.

        Every layer of a composition except the project's reports under the same
        label, so a document named by both a CORE fragment and a stack overlay
        would attribute one prompt twice. Measured over every shipped
        composition: no prompt names one document in two layers today, so the
        deduplication cannot be observed through a project's own files and a
        sabotage run that removed it stayed green (FINDING BDL-068.19-2, closed
        here). The composer is stubbed at this module's boundary — the one place
        a stub is honest — rather than the derivation under test.
        """
        fragments = (
            LayerFragment("core", "core.md.txt", "Read TWICE-NAMED.md.\n"),
            LayerFragment("stack:python", "stack.md.txt", "And TWICE-NAMED.md again.\n"),
        )
        monkeypatch.setattr(
            "beadloom.application.review_brief.reachability.compose",
            lambda kind, name, **_: Composition(kind=kind, name=name, fragments=fragments),
        )

        labels = prompts_naming_documents()["TWICE-NAMED.md"]
        assert labels.count(f"roles/{ROLE_NAMES[0]}") == 1, labels

    def test_a_document_two_prompts_name_is_attributed_to_both_exactly_once(
        self, tmp_path: Path
    ) -> None:
        """Who sends the reviewer there is the answer #212 needed, not just that.

        Named twice in one fragment and once in another: the report says both
        prompts and says each of them once.
        """
        project = tmp_path / "proj"
        project.mkdir()
        role, command = ROLE_NAMES[0], _shipped_commands()[0]
        document = "SHARED-NOTE.md"
        _project_fragment(project, "roles", role, f"Read {document}. Then {document} again.\n")
        _project_fragment(project, "commands", command, f"Write {document}.\n")

        labels = prompts_naming_documents(project)[document]
        assert labels.count(f"roles/{role} (project layer)") == 1, labels
        assert labels.count(f"commands/{command} (project layer)") == 1, labels

    def test_the_population_follows_the_project_s_configured_overlays(self) -> None:
        """A stack overlay is a layer of a prompt, so it names documents too.

        Measured: the `tech-writer` role names `README.md` and `SPEC.md` in its
        `stack:python` fragment and nowhere else, so a project configured for
        another stack reaches a different set of documents. The report follows
        the project's own configuration and not this project's, which is the
        derivation asserted against a third input — after `ROLE_NAMES` and the
        commands directory.

        What it costs is asserted too. `compose` drops a configured overlay that
        ships no fragment with NO note and NO error, so the report names fewer
        documents and says nothing about the layer it lost — a count whose
        window is unstated, one layer below the channels (FINDING BDL-068.19-3,
        reported and not repaired from a test bead).
        """
        whole = prompts_naming_documents()
        reduced = prompts_naming_documents(
            config=FlowConfig(
                tools=("claude",), architecture="ddd", stack=("no-such-stack",)
            )
        )

        def labels(naming: dict[str, tuple[str, ...]]) -> set[str]:
            return {label for attribution in naming.values() for label in attribution}

        assert reduced, "every prompt was skipped; the assertion below is vacuous"
        assert labels(reduced) < labels(whole), (
            "no prompt failed to compose, so nothing here observes the guard: "
            f"{labels(whole) - labels(reduced)}"
        )
        assert set(reduced) <= set(whole)

    @pytest.mark.parametrize(
        ("stem", "read"),
        [
            ("A", False),
            ("AB", True),
            ("A" * 21, True),
            ("A" * 22, False),
        ],
    )
    def test_the_document_shape_holds_at_both_ends_of_its_range(
        self, tmp_path: Path, stem: str, read: bool
    ) -> None:
        """The shape is what stands in for a list, so its edges are the list's.

        One letter is a sentence's initial, not a document; twenty-two is past
        anything the flow writes. Both ends are asserted because a shape that
        drifts wider reads prose as documents and one that drifts narrower
        silently stops reading a team's own.
        """
        project = tmp_path / "proj"
        project.mkdir()
        document = f"{stem}.md"
        _project_fragment(project, "roles", ROLE_NAMES[0], f"Read {document} first.\n")

        assert (document in prompts_naming_documents(project)) is read

    def test_a_name_outside_the_latin_alphabet_is_not_read_as_a_document(
        self, tmp_path: Path
    ) -> None:
        """A prompt written in another script names its documents in another
        script, and the shape does not claim to read them. What matters is that
        it says so by finding nothing rather than by raising."""
        project = tmp_path / "proj"
        project.mkdir()
        _project_fragment(
            project, "roles", ROLE_NAMES[0], "設計.md を読む. Read ACTIVE.md.\n"
        )

        naming = prompts_naming_documents(project)
        assert "ACTIVE.md" in naming
        assert "設計.md" not in naming

    def test_the_report_names_documents_and_never_carries_the_prompt_s_prose(
        self, tmp_path: Path
    ) -> None:
        """A report about what can reach a reviewer must not become a channel.

        Pinned for the prompts the way `.18` pinned it for a commit body and a
        bead comment: the text is the thing being reported ON.
        """
        project = tmp_path / "proj"
        project.mkdir()
        _project_fragment(project, "roles", ROLE_NAMES[0], f"Read ACTIVE.md. {_PROSE}\n")

        naming = prompts_naming_documents(project)
        assert "ACTIVE.md" in naming
        assert _PROSE not in repr(naming)


class TestTheWorkItemChannelIsDerivedFromTheProject:
    def test_a_work_item_key_outside_the_latin_alphabet_is_still_read(
        self, tmp_path: Path
    ) -> None:
        """The corpus is the project's, so its own naming is not this repository's.

        A branch segment matches a folder name; nothing in the derivation
        requires that name to be spelled the way this project spells one.
        """
        project = tmp_path / "proj"
        key = "設計-1"
        _work_item(project, key, "CONTEXT.md")

        channel = work_item_documents_channel(project, branch=f"features/{key}")
        assert channel.inspected
        assert channel.carries == 1
        assert key in channel.items[0]

    def test_a_branch_carrying_quoting_characters_is_named_in_one_line(
        self, tmp_path: Path
    ) -> None:
        """The reason quotes the branch, and a reason that broke across lines
        would put half a statement under the next channel's."""
        project = tmp_path / "proj"
        _work_item(project, "ALPHA-1", "CONTEXT.md")
        branch = "features/it's \"quoted\""

        channel = work_item_documents_channel(project, branch=branch)
        assert not channel.inspected
        assert "quoted" in channel.reason
        assert "\n" not in channel.statement()

    def test_the_channel_lists_the_documents_and_never_their_contents(
        self, tmp_path: Path
    ) -> None:
        """BDL-UX #212's channel is `ACTIVE.md`, and `ACTIVE.md` is where the
        author's account sits. Reporting that a reviewer can reach it must not
        be a way of handing it over."""
        project = tmp_path / "proj"
        _work_item(project, "ALPHA-1", "ACTIVE.md", body=_PROSE)

        channel = work_item_documents_channel(project, branch="features/ALPHA-1")
        assert channel.carries == 1
        assert "ACTIVE.md" in channel.items[0]
        assert _PROSE not in repr(channel)


class TestTheDirectionOfTheStatement:
    """Assertion 2: `could not look` and `looked and found nothing`, over the
    whole report rather than over the one channel that happens to do both."""

    def test_no_channel_the_report_could_not_inspect_states_a_count(
        self, tmp_path: Path
    ) -> None:
        """Iterated from the report, so a fifth channel is covered on arrival."""
        project = tmp_path / "proj"
        project.mkdir()
        worlds = _worlds(project)
        seen = 0
        for world, report in worlds.items():
            for channel in report.uninspected:
                seen += 1
                statement = channel.statement()
                assert "NOT INSPECTED" in statement, f"{world}: {statement}"
                assert "item(s)" not in statement, f"{world}: {statement}"
                assert channel.reason.strip(), f"{world}: {channel.name} gives no reason"
        assert seen >= 2, "no uninspected channel was exercised; the assertion is vacuous"

    def test_every_channel_the_report_inspected_states_its_count_and_its_window(
        self, tmp_path: Path
    ) -> None:
        """The other half, and the one #204 is about: a count whose window is
        unstated is what `0 withheld` was."""
        project = tmp_path / "proj"
        project.mkdir()
        worlds = _worlds(project)
        seen = 0
        for world, report in worlds.items():
            for channel in report.channels:
                if not channel.inspected:
                    continue
                seen += 1
                statement = channel.statement()
                assert f"{channel.carries} item(s)" in statement, f"{world}: {statement}"
                assert channel.reason.strip(), f"{world}: {channel.name} states no window"
                assert channel.reason in statement, f"{world}: {statement}"
        assert seen >= 2, "no inspected channel was exercised; the assertion is vacuous"

    def test_the_report_names_the_same_channels_whatever_could_be_answered(
        self, tmp_path: Path
    ) -> None:
        """A channel is never dropped for want of an answer — which is exactly
        what #204 was: the channel the count could not be about was absent."""
        project = tmp_path / "proj"
        project.mkdir()
        worlds = _worlds(project)
        names = {
            world: tuple(channel.name for channel in report.channels)
            for world, report in worlds.items()
        }
        assert len(set(names.values())) == 1, names
        assert len(names["blind"]) > 1, names

    def test_a_channel_found_empty_never_reads_as_one_nobody_could_inspect(
        self, tmp_path: Path
    ) -> None:
        """Paired by channel NAME across the two worlds, so the comparison is
        made for every channel that can be in both states rather than for the
        one a test author remembered."""
        project = tmp_path / "proj"
        project.mkdir()
        empty = reachability_of(
            notes=(), project_root=project, branch=None, commits=(), since="main"
        )
        blind = reachability_of(
            notes=(), project_root=project, branch=None, commits=None, since="main"
        )
        compared = 0
        for looked in empty.channels:
            unseen = blind.named(looked.name)
            assert unseen is not None, looked.name
            if not (looked.inspected and looked.carries == 0 and not unseen.inspected):
                continue
            compared += 1
            assert looked.statement() != unseen.statement(), looked.name
            assert "NOT INSPECTED" not in looked.statement(), looked.name
        assert compared >= 1, "no channel gave both states; the comparison is vacuous"

    def test_no_channel_carries_an_item_it_could_not_inspect(self, tmp_path: Path) -> None:
        """The invariant behind the rendering: items are printed under the
        statement, so an uninspected channel holding items would print a list
        under the line that says nothing was read."""
        project = tmp_path / "proj"
        project.mkdir()
        for world, report in _worlds(project).items():
            for channel in report.uninspected:
                assert channel.items == (), f"{world}: {channel.name} carries {channel.items}"
                assert channel.carries == 0, f"{world}: {channel.name}"

    def test_an_inspected_channel_that_found_nothing_still_names_its_window(self) -> None:
        """The counterpart the first pass asserted only for the blind case."""
        looked = commit_bodies_channel([], since="origin/main")
        assert looked.inspected
        assert looked.carries == 0
        assert "origin/main" in looked.reason

    @pytest.mark.parametrize("commits", [None, ()])
    def test_an_unnamed_base_ref_is_stated_as_one_rather_than_left_dangling(
        self, commits: tuple[Commit, ...] | None
    ) -> None:
        """`--since ''` is a window nobody named. The report says so in both
        directions; a reason ending in `since ` is a sentence that lost its
        subject and reads as a truncated one."""
        channel = commit_bodies_channel(commits, since="")
        assert "since the base ref" in channel.reason
        assert not channel.reason.endswith("since ")

    def test_an_unattributed_comment_is_counted_without_being_invented(self) -> None:
        """The tracker does not always record an author. The channel says so
        rather than dropping the comment out of the count or naming somebody."""
        channel = bead_comments_channel(
            [AuthorNote(text=_PROSE), AuthorNote(text=_PROSE, author="dev", created="")]
        )
        assert channel.carries == 2
        assert "unattributed" in channel.items[0]
        assert channel.items[1] == "dev"
        assert _PROSE not in repr(channel)


class TestWhatTheReportCannotSurvive:
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.19-1: prompts_naming_documents reads the project's "
            "flow.yml through doc_flow_config OUTSIDE the FlowConfigError guard "
            "that _composed_prompts puts around compose(), so a malformed "
            "flow.yml raises out of reachability_of and `review-brief` produces "
            "no brief at all. The module's own rule is that a prompt which will "
            "not compose contributes nothing and is not an error here, because "
            "reporting a malformed config is config-check's job."
        ),
    )
    def test_a_malformed_flow_config_costs_the_channel_and_not_the_brief(
        self, tmp_path: Path
    ) -> None:
        """A report about what a reviewer can reach is worth nothing if a broken
        configuration file removes the report."""
        project = tmp_path / "proj"
        _work_item(project, "ALPHA-1", "CONTEXT.md")
        (project / ".beadloom").mkdir(parents=True, exist_ok=True)
        (project / ".beadloom" / "flow.yml").write_text(
            "architecture: [unclosed\n", encoding="utf-8"
        )

        report = reachability_of(
            notes=(),
            project_root=project,
            branch="features/ALPHA-1",
            commits=(),
            since="main",
        )
        assert len(report.channels) > 1
