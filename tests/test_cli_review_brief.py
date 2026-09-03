"""`beadloom review-brief` — what a reviewer is handed, and what it is not.

The command is presentation and wiring; the decision is
`beadloom.application.review_brief`. What this file pins is the property the
whole feature exists for and which only the COMMAND can get wrong: the author's
comments are read out of the tracker (so the count is real) and none of their
text reaches either output shape until a verdict is on the record.

The two shapes carry the same facts and neither depends on whether stdout is a
terminal (BDL-UX #148), and nothing here counts lines.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_EXIT_CLEAN = 0
_EXIT_FINDINGS = 1
_EXIT_UNDECIDABLE = 2
_EXIT_WITHHELD = 3

#: The author's own words. No assertion in this file may relax to a substring of
#: something the brief legitimately prints, so the sentinel says nothing a spec,
#: a path or a finding would ever say.
_AUTHOR_TEXT = "CHECKPOINT: sabotage table run, clause two is a constant tuple"


#: A commit body's own words. The channel counts bodies; a report that printed
#: one would be the very leak BDL-UX #219 measured.
_BODY_TEXT = "the rounding moved to the boundary because two callers rounded twice"


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / ".beadloom").mkdir(parents=True)
    conn = open_db(project / ".beadloom" / "beadloom.db")
    create_schema(conn)
    for ref in ("billing", "shipping"):
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref, "feature", ref, f"src/{ref}/"),
        )
        conn.execute(
            "INSERT INTO docs (ref_id, path, kind, hash) VALUES (?, ?, ?, ?)",
            (ref, f"docs/{ref}/SPEC.md", "feature", f"h-{ref}"),
        )
    conn.commit()
    conn.close()
    return project


def _git(project: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=project,
        check=True,
        capture_output=True,
    )


def _repo_with_change(tmp_path: Path, changed: str = "src/billing/core.py") -> Path:
    """A real repository whose working tree differs from the base ref by one file.

    A real repository rather than a double, because what the command must get
    right here is the git question itself — which paths differ from a named ref —
    and a fake would prove the fake (FAKES PROVE FAKES).
    """
    project = _project(tmp_path)
    (project / ".gitignore").write_text(".beadloom/\n", encoding="utf-8")
    _git(project, "init")
    _git(project, "config", "user.email", "t@example.com")
    _git(project, "config", "user.name", "t")
    _git(project, "add", ".gitignore")
    _git(project, "commit", "-m", "base", "--no-verify")
    _git(project, "branch", "-M", "main")
    _git(project, "switch", "-c", "features/x")
    path = project / changed
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("value = 1\n", encoding="utf-8")
    _git(project, "add", changed)
    _git(project, "commit", "-m", "change", "--no-verify")
    return project


def _commit_with_a_body(project: Path, body: str, path: str = "src/billing/rate.py") -> None:
    """One more commit on the branch, whose message carries a body."""
    target = project / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("rate = 2\n", encoding="utf-8")
    _git(project, "add", path)
    message = f"the second change\n\n{body}\n\nand a second line"
    _git(project, "commit", "-m", message, "--no-verify")


class _FakeBd:
    """A stand-in for the `bd` binary: `show` and `comments` for one bead.

    Scoped deliberately: it proves the COMMAND's wiring and rendering, not the
    seam. The real seam is covered by `tests/test_bd_seam.py`, and the shape of a
    real `bd comments --json` record is pinned by the shape test below.
    """

    def __init__(self, record: dict[str, Any], comments: list[dict[str, Any]]) -> None:
        self.record = record
        self.comments = comments

    def __call__(self, args: list[str], *, cwd: str | None = None) -> Any:
        from beadloom.services.bd_seam import BdResult

        if args[0] == "comments":
            return BdResult(returncode=0, stdout=json.dumps(self.comments), stderr="")
        if args[1] != self.record["id"]:
            return BdResult(returncode=1, stdout="", stderr="no such issue")
        return BdResult(returncode=0, stdout=json.dumps([self.record]), stderr="")


def _record(
    bead: str = "a",
    refs: str = "billing",
    notes: str = "",
    assignee: str = "dev",
    description: str | None = None,
) -> dict[str, Any]:
    """A bead as `bd show --json` gives it.

    ``assignee`` is not decoration: it is the party whose account the brief
    withholds, and `--release` compares it with the author of the verdict comment.
    """
    return {
        "id": bead,
        "title": f"[{bead}] make the billing total round once",
        "description": (
            description
            if description is not None
            else f"Round the total once, at the boundary.\nrefs: {refs}"
        ),
        "notes": notes,
        "assignee": assignee,
    }


def _comment(text: str, author: str = "v.zoologov") -> dict[str, Any]:
    return {
        "id": "01a0",
        "issue_id": "a",
        "author": author,
        "text": text,
        "created_at": "2026-08-24T17:00:00Z",
    }


def _channel(stdout: str, name: str) -> dict[str, Any]:
    """One channel of the `--json` reachability statement, by name."""
    found = [c for c in json.loads(stdout)["reachability"] if c["channel"] == name]
    assert found, f"the JSON names no channel {name!r}"
    return dict(found[0])


@pytest.fixture()
def bd(monkeypatch: pytest.MonkeyPatch) -> Any:
    def _install(record: dict[str, Any], comments: list[dict[str, Any]]) -> None:
        monkeypatch.setattr(
            "beadloom.services.bd_seam.run_bd", _FakeBd(record, comments), raising=True
        )

    return _install


class TestWhatIsHandedOver:
    def test_the_change_and_the_specification_reach_the_reviewer(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _repo_with_change(tmp_path)
        bd(_record(), [_comment(_AUTHOR_TEXT)])
        result = CliRunner().invoke(
            main, ["review-brief", "a", "--since", "main", "--project", str(project)]
        )
        assert "src/billing/core.py" in result.output
        assert "docs/billing/SPEC.md" in result.output
        assert "Round the total once" in result.output

    def test_the_authors_comments_reach_neither_output_shape(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The property the whole feature exists for, asserted on both shapes."""
        project = _repo_with_change(tmp_path)
        bd(_record(), [_comment(_AUTHOR_TEXT), _comment("COMPLETED: shipped")])
        for extra in ([], ["--json"]):
            result = CliRunner().invoke(
                main,
                ["review-brief", "a", "--since", "main", "--project", str(project), *extra],
            )
            assert _AUTHOR_TEXT not in result.output
            assert "COMPLETED: shipped" not in result.output

    def test_the_withheld_comments_are_counted_in_both_shapes(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The count survives the change from a withheld count to a reachability
        statement — it is stated as what the bead-comments CHANNEL carries."""
        project = _repo_with_change(tmp_path)
        bd(_record(), [_comment(_AUTHOR_TEXT), _comment("COMPLETED: shipped")])
        human = CliRunner().invoke(
            main, ["review-brief", "a", "--since", "main", "--project", str(project)]
        )
        assert "bead comments: 2 item(s)" in human.output
        machine = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
        )
        assert _channel(machine.stdout, "bead comments")["carries"] == 2

    def test_the_notes_field_gives_the_scope_without_giving_its_prose(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """`refs:` is a token; the paragraph it sits in is the author's account.

        This epic's own beads declare their scope in `notes` as often as in the
        description, so the token must be read from there — and `notes` is also
        where a dev appends progress, so the prose must not come with it.
        """
        project = _repo_with_change(tmp_path)
        bd(
            _record(refs="", notes=f"refs: billing\n{_AUTHOR_TEXT}"),
            [],
        )
        result = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
        )
        payload = json.loads(result.stdout)
        assert payload["refs"] == ["billing"]
        assert _AUTHOR_TEXT not in result.output


class TestRelease:
    def test_release_is_refused_while_no_verdict_is_recorded(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _repo_with_change(tmp_path)
        bd(_record(), [_comment(_AUTHOR_TEXT)])
        result = CliRunner().invoke(
            main,
            ["review-brief", "a", "--release", "--since", "main", "--project", str(project)],
        )
        assert result.exit_code == _EXIT_WITHHELD
        assert _AUTHOR_TEXT not in result.output
        assert "no verdict is recorded" in result.output

    def test_a_recorded_verdict_releases_the_account(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _repo_with_change(tmp_path)
        bd(
            _record(),
            [_comment(_AUTHOR_TEXT), _comment("REVIEW ISSUES: 1 major", author="review")],
        )
        result = CliRunner().invoke(
            main,
            ["review-brief", "a", "--release", "--since", "main", "--project", str(project)],
        )
        assert result.exit_code == _EXIT_CLEAN
        assert _AUTHOR_TEXT in result.output

    @pytest.mark.parametrize(
        "comment",
        [
            f"{_AUTHOR_TEXT} — the REVIEW PASSED comment is still to come",
            "REVIEW ISSUES are still open, will fix",
            f"COMPLETED: shipped it\nREVIEW PASSED: I checked my own work\n{_AUTHOR_TEXT}",
        ],
        ids=["mid-line", "line-start-without-a-colon", "buried-in-a-checkpoint"],
    )
    def test_a_comment_that_merely_mentions_a_review_does_not_release(
        self, tmp_path: Path, bd: Any, comment: str
    ) -> None:
        """A verdict OPENS a comment and carries its colon; anything else is prose.

        The middle case is the one `.79`'s honesty note listed under ENFORCED and
        the code did not have: the marker was anchored to a line start and the
        colon was never required (BDL-061.23 M1).
        """
        project = _repo_with_change(tmp_path)
        bd(_record(), [_comment(comment)])
        result = CliRunner().invoke(
            main,
            ["review-brief", "a", "--release", "--since", "main", "--project", str(project)],
        )
        assert result.exit_code == _EXIT_WITHHELD
        assert _AUTHOR_TEXT not in result.output

    def test_a_verdict_by_the_beads_own_author_releases_and_costs_the_exit_code(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """`AuthorNote.author` was read from the tracker and never compared.

        The account is still released — this repository's roles share one tracker
        identity, so refusing would refuse every release — but the run says what
        it could not establish, and its exit code is no longer 0.
        """
        project = _repo_with_change(tmp_path)
        bd(
            _record(assignee="dev"),
            [_comment(_AUTHOR_TEXT), _comment("REVIEW PASSED: my own work", author="dev")],
        )
        result = CliRunner().invoke(
            main,
            ["review-brief", "a", "--release", "--since", "main", "--project", str(project)],
        )
        assert result.exit_code == _EXIT_FINDINGS
        assert _AUTHOR_TEXT in result.output
        assert "same tracker identity" in result.output

    def test_both_shapes_carry_the_same_release_verdict(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """BDL-UX #148 — the machine shape must not be quieter than the human one."""
        project = _repo_with_change(tmp_path)
        bd(
            _record(assignee="dev"),
            [_comment(_AUTHOR_TEXT), _comment("REVIEW PASSED: my own work", author="dev")],
        )
        machine = CliRunner().invoke(
            main,
            [
                "review-brief", "a", "--release", "--since", "main",
                "--project", str(project), "--json",
            ],
        )
        payload = json.loads(machine.stdout)
        assert payload["exit_code"] == _EXIT_FINDINGS
        assert payload["verdict_author"] == "dev"
        assert "same tracker identity" in payload["independence_note"]


class TestOneDeclarationForEveryCaller:
    """`.23` M5, at the caller a reviewer meets."""

    def test_a_dangling_refs_header_at_a_field_boundary_declares_nothing(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The fields are joined with newlines, so a field boundary is a boundary.

        Joined with spaces — which the MCP caller did — `billing` would sit
        directly behind the dangling header and the bead would be handed a scope
        it never declared.
        """
        project = _repo_with_change(tmp_path)
        bd(_record(description="Scope\nrefs:", notes="billing is the one we mean"), [])
        result = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
        )
        payload = json.loads(result.stdout)
        assert payload["refs"] == []
        assert "no-declared-scope" in payload["findings"]


class TestFindingsAndCodes:
    def test_a_change_outside_the_declared_scope_is_named_and_costs_exit_zero(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _repo_with_change(tmp_path, changed="src/shipping/core.py")
        bd(_record(), [])
        result = CliRunner().invoke(
            main, ["review-brief", "a", "--since", "main", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_FINDINGS
        assert "changed-outside-scope" in result.output
        assert "measured over the branch since main" in result.output
        assert "src/shipping/core.py" in result.output

    def test_a_file_that_was_written_but_never_added_is_still_in_the_change(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The most-reviewed file of all is the one the author just created.

        `git diff` does not list an untracked path, so a brief built from diffs
        alone showed a reviewer every file the change TOUCHED and none of the
        files it ADDED — which is the half of a change most worth reading.
        """
        project = _repo_with_change(tmp_path)
        new_file = project / "src/billing/rounding.py"
        new_file.write_text("def round_once() -> int:\n    return 1\n", encoding="utf-8")
        bd(_record(), [])
        result = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
        )
        payload = json.loads(result.stdout)
        assert "src/billing/rounding.py" in {c["path"] for c in payload["changed"]}

    def test_an_ignored_file_is_not_offered_as_part_of_the_change(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """`.beadloom/` and the like are not the author's work and are not shown."""
        project = _repo_with_change(tmp_path)
        (project / ".beadloom" / "beadloom.db-wal").write_text("x", encoding="utf-8")
        bd(_record(), [])
        result = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
        )
        payload = json.loads(result.stdout)
        assert not [c for c in payload["changed"] if c["path"].startswith(".beadloom/")]

    def test_a_base_ref_that_does_not_resolve_is_unmeasured_not_empty(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _repo_with_change(tmp_path)
        bd(_record(), [])
        result = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "no-such-ref", "--project", str(project), "--json"],
        )
        payload = json.loads(result.stdout)
        assert payload["change_measured"] is False
        assert payload["changed"] == []
        assert "unmeasured-change" in payload["findings"]
        assert result.exit_code == _EXIT_FINDINGS

    def test_a_bead_the_tracker_does_not_have_is_exit_two(
        self, tmp_path: Path, bd: Any
    ) -> None:
        project = _repo_with_change(tmp_path)
        bd(_record(), [])
        result = CliRunner().invoke(
            main, ["review-brief", "zz", "--since", "main", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_UNDECIDABLE

    def test_no_index_is_exit_two(self, tmp_path: Path, bd: Any) -> None:
        project = tmp_path / "bare"
        project.mkdir()
        bd(_record(), [])
        result = CliRunner().invoke(
            main, ["review-brief", "a", "--project", str(project)]
        )
        assert result.exit_code == _EXIT_UNDECIDABLE


class TestWhatCanReachTheReviewer:
    """The reachability statement, which only the COMMAND can get wrong.

    What is asserted here is the wiring the application layer cannot do for
    itself: the commit bodies of the reviewed range are read out of a real
    repository, the branch is read off it, and both output shapes carry the same
    channels. The derivation of the channels is the application's, and is pinned
    beside it in `tests/test_review_brief_reachability.py`.
    """

    def test_the_commit_bodies_of_the_range_are_counted_without_being_quoted(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """BDL-UX #219: the reviewer's own protocol sends it to this diff.

        The channel says how much prose is waiting there; quoting it would be
        the leak the report exists to make visible.
        """
        project = _repo_with_change(tmp_path)
        _commit_with_a_body(project, _BODY_TEXT)
        bd(_record(), [])
        human = CliRunner().invoke(
            main, ["review-brief", "a", "--since", "main", "--project", str(project)]
        )
        machine = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
        )
        channel = _channel(machine.stdout, "the commit bodies of the reviewed range")
        assert channel["inspected"] is True
        assert channel["carries"] == 2, channel["items"]
        assert "2 body line(s)" in " ".join(channel["items"])
        assert "the commit bodies of the reviewed range: 2 item(s)" in human.output
        assert _BODY_TEXT not in human.output
        assert _BODY_TEXT not in machine.output

    def test_the_launch_prompt_is_named_in_both_shapes_as_one_nobody_here_can_see(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """BDL-UX #204: the channel the count could not be about is not omitted."""
        project = _repo_with_change(tmp_path)
        bd(_record(), [_comment(_AUTHOR_TEXT)])
        human = CliRunner().invoke(
            main, ["review-brief", "a", "--since", "main", "--project", str(project)]
        )
        machine = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
        )
        assert "the launch prompt: NOT INSPECTED" in human.output
        channel = _channel(machine.stdout, "the launch prompt")
        assert channel["inspected"] is False
        assert channel["reason"].strip()

    def test_a_channel_found_empty_does_not_read_like_one_nobody_could_inspect(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The Population rule one layer up, asserted on the rendered text.

        The branch `features/x` names no work item in this project's planning
        corpus, so the documents channel could not be inspected; the range holds
        one commit, so the bodies channel was. Neither statement may be readable
        as the other.
        """
        project = _repo_with_change(tmp_path)
        bd(_record(), [])
        human = CliRunner().invoke(
            main, ["review-brief", "a", "--since", "main", "--project", str(project)]
        )
        assert "the work item's documents: NOT INSPECTED" in human.output
        assert "the commit bodies of the reviewed range: 1 item(s)" in human.output

    def test_a_document_of_the_branch_s_work_item_is_reported_with_the_prompt_naming_it(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """BDL-UX #212: `ACTIVE.md` reached a reviewer through a launch prompt.

        The branch names the work item, the work item's folder holds the
        document, and the composed role prompts are what say a role is sent to
        it. Nothing in this test names `ACTIVE.md` to the report.
        """
        project = _repo_with_change(tmp_path)
        _git(project, "switch", "-c", "features/ALPHA-1")
        folder = project / ".claude" / "development" / "docs" / "features" / "ALPHA-1"
        folder.mkdir(parents=True)
        (folder / "ACTIVE.md").write_text(
            "# ACTIVE\n\nthe author's own account\n", encoding="utf-8"
        )
        bd(_record(), [])
        machine = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
        )
        channel = _channel(machine.stdout, "the work item's documents")
        assert channel["inspected"] is True
        entry = next(item for item in channel["items"] if "ACTIVE.md" in item)
        assert "named by roles/" in entry, entry


class TestSeamShape:
    def test_the_comment_shape_this_command_reads_is_the_one_bd_emits(self) -> None:
        """`bd comments --json` answers a list of objects carrying `text`.

        Pinned against the real binary when it is installed, and skipped with the
        reason when it is not — a double alone would leave the command's only
        assumption about the tracker unverified.
        """
        pytest.importorskip("shutil")
        import shutil

        if shutil.which("bd") is None:
            pytest.skip("bd is not installed; the seam's shape cannot be observed")
        proc = subprocess.run(
            ["bd", "comments", "beadloom-mr2l.21", "--json"],  # noqa: S607
            cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            pytest.skip("this tracker has no answer for the pinned bead")
        payload = json.loads(proc.stdout)
        assert isinstance(payload, list)
        assert {"text", "author"} <= set(payload[0])


def _reachability_statements(human: str) -> list[str]:
    """The one line per channel the human shape prints, in report order.

    Read off the block rather than matched by name: the point of the assertions
    below is that neither shape may drop a channel the report carries, and a
    reader that looked for known names could not notice a missing one.
    """
    lines = human.splitlines()
    heading = next(i for i, line in enumerate(lines) if line.startswith("REACHABLE —"))
    statements: list[str] = []
    for line in lines[heading + 1 :]:
        if not line.strip():
            break
        if line.startswith("  ") and not line.startswith("    "):
            statements.append(line.strip())
    return statements


class TestBothShapesCarryTheWholeStatement:
    """BDL-068 S2, the rendering half: what `.18` pinned by two substrings.

    Every assertion here is seeded from the report the command produced, so a
    fifth channel — or a channel dropped from one shape only — is covered
    without an edit. A `--json` consumer and a human reader must be able to
    reach the same conclusion, which was the whole finding of BDL-UX #148.
    """

    def _both(self, project: Path) -> tuple[str, list[dict[str, Any]]]:
        argv = ["review-brief", "a", "--since", "main", "--project", str(project)]
        human = CliRunner().invoke(main, argv)
        machine = CliRunner().invoke(main, [*argv, "--json"])
        assert machine.exit_code in (_EXIT_CLEAN, _EXIT_FINDINGS), machine.output
        return human.output, list(json.loads(machine.stdout)["reachability"])

    def test_every_channel_the_report_carries_is_stated_in_both_shapes(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """A channel that reaches only one shape is a channel half the readers
        never learn about, which is the omission #204 was."""
        project = _repo_with_change(tmp_path)
        bd(_record(), [_comment(_AUTHOR_TEXT)])
        human, channels = self._both(project)

        statements = _reachability_statements(human)
        assert len(channels) > 1, channels
        assert len(statements) == len(channels), statements
        for channel in channels:
            assert any(
                statement.startswith(f"{channel['channel']}:") for statement in statements
            ), f"{channel['channel']} reaches the JSON and not the reader: {statements}"

    def test_the_line_for_a_channel_nobody_could_inspect_carries_no_count(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """The Population rule on the rendered line, for every channel that is
        in that state rather than for the one the test author remembered."""
        project = _repo_with_change(tmp_path)
        bd(_record(), [])
        human, channels = self._both(project)

        statements = {line.split(":", 1)[0]: line for line in _reachability_statements(human)}
        unseen = [c for c in channels if not c["inspected"]]
        assert len(unseen) >= 2, channels
        for channel in unseen:
            line = statements[channel["channel"]]
            assert "NOT INSPECTED" in line, line
            assert "item(s)" not in line, line
            assert channel["items"] == [], channel

    def test_nothing_withheld_is_no_longer_a_sentence_either_shape_can_print(
        self, tmp_path: Path, bd: Any
    ) -> None:
        """BDL-UX #204 was a true count read as a false claim. With no comments
        at all the brief must still state what a reviewer can reach — a bare
        zero beside no other channel is the sentence that was misread."""
        project = _repo_with_change(tmp_path)
        bd(_record(), [])
        human, channels = self._both(project)

        assert "WITHHELD" not in human
        assert "withheld" not in json.loads(
            CliRunner()
            .invoke(
                main,
                ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
            )
            .stdout
        )
        assert next(c for c in channels if c["channel"] == "bead comments")["carries"] == 0
        assert len(_reachability_statements(human)) == len(channels)
