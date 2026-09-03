"""The reachability report, and the property it stands or falls on (BDL-068 S2).

`review-brief` reported `0 withheld`. That is true of bead comments and false
about the question its reader asks, which is what the reviewer can reach. Three
measured defeats — `ACTIVE.md` named by a launch prompt (#212), the commit bodies
of the reviewed range (#219), and a prompt this command cannot see at all (#204)
— reached reviewers that had been told nothing was held back.

What this file pins is the DERIVATION rather than the wording. A hand-written
list of documents would satisfy a report test and go stale the first time a role
file gained one, so the assertions here are built to fail against a list: a
document no shipped fragment mentions is named by the report the moment a
project's own role fragment names it, and by nothing else.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.review_brief import (
    CHANNEL_COMMIT_BODIES,
    CHANNEL_WORK_ITEM_DOCUMENTS,
    Channel,
    Commit,
    bead_comments_channel,
    commit_bodies_channel,
    launch_prompt_channel,
    prompts_naming_documents,
    work_item_documents_channel,
)
from beadloom.application.review_brief.models import AuthorNote
from beadloom.onboarding.role_composer import ROLE_NAMES

if TYPE_CHECKING:
    from pathlib import Path

#: A document name no shipped fragment mentions, so its appearance in the report
#: can only have come from the project's own prompt layer.
_NOVEL_DOCUMENT = "DECISIONS.md"

#: Where the shipped planning globs look for a work item's folder.
_PLANNING_ROOT = (".claude", "development", "docs", "features")


def _work_item(project: Path, key: str, *documents: str) -> Path:
    folder = project.joinpath(*_PLANNING_ROOT, key)
    folder.mkdir(parents=True, exist_ok=True)
    for name in documents:
        (folder / name).write_text(f"# {name}\n", encoding="utf-8")
    return folder


def _project_role_fragment(project: Path, role: str, text: str) -> None:
    fragment = project / ".beadloom" / "flow" / "roles" / f"{role}.md"
    fragment.parent.mkdir(parents=True, exist_ok=True)
    fragment.write_text(text, encoding="utf-8")


class TestTheDocumentPopulationIsDerivedFromThePrompts:
    def test_the_shipped_prompts_name_the_documents_the_flow_writes(self) -> None:
        """Anti-vacuity: a derivation that found nothing would pass every other case."""
        naming = prompts_naming_documents()
        assert {"CONTEXT.md", "ACTIVE.md", "PRD.md", "RFC.md", "PLAN.md"} <= set(naming)

    def test_a_document_is_attributed_to_the_prompts_that_name_it(self) -> None:
        """#212's channel, with the answer to "who sent the reviewer there"."""
        naming = prompts_naming_documents()
        role_labels = {
            label for labels in naming.values() for label in labels if label.startswith("roles/")
        }
        assert len(role_labels) > 1, role_labels
        assert role_labels <= {f"roles/{role}" for role in ROLE_NAMES}
        assert any(label.startswith("commands/") for label in naming["ACTIVE.md"])

    def test_a_project_role_fragment_moves_the_report_and_nothing_else_does(
        self, tmp_path: Path
    ) -> None:
        """The property the whole design turns on, asserted in both directions.

        Without the fragment the name is absent from the report; with it, the
        name is present and attributed to the project layer. A hand-written list
        of documents passes the first half and fails the second.
        """
        project = tmp_path / "proj"
        project.mkdir()
        assert _NOVEL_DOCUMENT not in prompts_naming_documents(project)

        _project_role_fragment(
            project, "review", f"Read `{_NOVEL_DOCUMENT}` before you judge.\n"
        )
        naming = prompts_naming_documents(project)
        assert naming[_NOVEL_DOCUMENT] == ("roles/review (project layer)",)

    def test_the_shape_matches_a_document_and_not_a_sentence(self, tmp_path: Path) -> None:
        """Upper-case and `.md`. A lower-cased name or another suffix is not one."""
        project = tmp_path / "proj"
        project.mkdir()
        _project_role_fragment(
            project,
            "review",
            "Read notes.md, CONTEXT.mdx and NOTES.md before you judge.\n",
        )
        naming = prompts_naming_documents(project)
        assert "NOTES.md" in naming
        assert "notes.md" not in naming
        assert "CONTEXT.mdx" not in naming

    def test_the_report_is_the_same_on_two_runs(self, tmp_path: Path) -> None:
        """The order is composed, not a directory listing, so it cannot drift."""
        project = tmp_path / "proj"
        project.mkdir()
        assert prompts_naming_documents(project) == prompts_naming_documents(project)


class TestTheWorkItemDocumentsChannel:
    def test_a_document_of_the_work_item_is_reported_with_its_prompts(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "proj"
        _work_item(project, "ALPHA-1", "CONTEXT.md", "ACTIVE.md")
        channel = work_item_documents_channel(project, branch="features/ALPHA-1")
        assert channel.inspected
        assert channel.carries == 2
        entry = next(item for item in channel.items if "ACTIVE.md" in item)
        assert "named by roles/" in entry, entry

    def test_a_document_no_prompt_names_is_reported_as_reachable_anyway(
        self, tmp_path: Path
    ) -> None:
        """Reachability is about what a reviewer CAN open, not what it is sent to.

        A document the prompts never mention still sits in the folder the
        reviewer is told to read, so omitting it would understate the channel in
        exactly the direction this report exists to correct.
        """
        project = tmp_path / "proj"
        _work_item(project, "ALPHA-1", _NOVEL_DOCUMENT)
        channel = work_item_documents_channel(project, branch="features/ALPHA-1")
        assert channel.items == (
            f".claude/development/docs/features/ALPHA-1/{_NOVEL_DOCUMENT} "
            "— named by no composed prompt",
        )

    def test_each_way_of_not_knowing_is_reported_as_itself(self, tmp_path: Path) -> None:
        """Four absences, four reasons, none of them an empty folder."""
        project = tmp_path / "proj"
        _work_item(project, "ALPHA-1", "CONTEXT.md")
        reasons = {
            "no root": work_item_documents_channel(None, branch="features/ALPHA-1").reason,
            "no branch": work_item_documents_channel(project, branch=None).reason,
            "no work item": work_item_documents_channel(project, branch="features/x").reason,
        }
        for label, reason in reasons.items():
            assert reason.strip(), label
        assert len(set(reasons.values())) == len(reasons)
        assert not work_item_documents_channel(project, branch="features/x").inspected

    def test_a_folder_with_no_documents_is_no_longer_a_work_item_and_says_so(
        self, tmp_path: Path
    ) -> None:
        """The work-item population is the planning corpus, not the directory tree.

        An empty folder matches no planning document, so `work_item_of_branch`
        finds none — and the channel reports the branch naming no work item
        rather than reporting a work item with nothing in it. Stated here
        because the two readings are one `glob` apart.
        """
        project = tmp_path / "proj"
        _work_item(project, "ALPHA-1", "CONTEXT.md")
        (project / ".claude/development/docs/features/ALPHA-1/CONTEXT.md").unlink()
        channel = work_item_documents_channel(project, branch="features/ALPHA-1")
        assert channel.inspected is False, (
            "with its only document gone the folder is no longer a work item in "
            "the planning corpus, and the report must say so rather than report "
            "an empty folder"
        )


class TestInspectedAndEmptyIsNotUninspected:
    """`Population`'s rule one layer up (BDL-068 S1), stated over channels."""

    def test_the_two_statements_are_never_the_same_text(self) -> None:
        looked = commit_bodies_channel([], since="main")
        blind = commit_bodies_channel(None, since="main")
        assert looked.inspected and looked.carries == 0
        assert not blind.inspected
        assert looked.statement() != blind.statement()

    def test_an_uninspected_channel_still_names_its_reason_and_its_window(self) -> None:
        blind = commit_bodies_channel(None, since="origin/main")
        assert "origin/main" in blind.reason
        assert blind.name == CHANNEL_COMMIT_BODIES

    def test_the_report_lists_the_channels_nobody_could_inspect(self, tmp_path: Path) -> None:
        from beadloom.application.review_brief import reachability_of

        report = reachability_of(
            notes=(),
            project_root=tmp_path,
            branch=None,
            commits=None,
            since="main",
        )
        uninspected = {channel.name for channel in report.uninspected}
        assert CHANNEL_WORK_ITEM_DOCUMENTS in uninspected
        assert CHANNEL_COMMIT_BODIES in uninspected
        assert report.named("the launch prompt") in report.uninspected


class TestNothingCarriesTheAccountItCounts:
    def test_the_commit_channel_carries_a_length_and_never_a_body(self) -> None:
        """`Commit` has no field a body could be put in — a structural guarantee."""
        assert set(Commit.__dataclass_fields__) == {"sha", "subject", "body_lines"}
        channel = commit_bodies_channel(
            [Commit(sha="0f1e2d3", subject="the fix", body_lines=12)], since="main"
        )
        assert "12 body line(s)" in channel.items[0]

    def test_the_bead_comment_channel_carries_no_comment_text(self) -> None:
        account = "CHECKPOINT: the clause is a constant tuple"
        channel = bead_comments_channel(
            [AuthorNote(text=account, author="dev", created="2026-09-03")]
        )
        assert channel.carries == 1
        assert account not in repr(channel)
        assert "dev 2026-09-03" in channel.items[0]

    def test_the_launch_prompt_channel_says_who_can_see_it(self) -> None:
        channel = launch_prompt_channel()
        assert not channel.inspected
        assert "you are the only party that can see it" in channel.reason


class TestTheStatementShape:
    def test_a_channel_with_no_reason_still_states_its_count(self) -> None:
        assert Channel(name="c", inspected=True, items=("x",)).statement() == "c: 1 item(s)"

    def test_an_uninspected_channel_leads_with_the_absence(self) -> None:
        statement = Channel(name="c", inspected=False, reason="nobody looked").statement()
        assert statement.startswith("c: NOT INSPECTED")
