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
        project = _repo_with_change(tmp_path)
        bd(_record(), [_comment(_AUTHOR_TEXT), _comment("COMPLETED: shipped")])
        human = CliRunner().invoke(
            main, ["review-brief", "a", "--since", "main", "--project", str(project)]
        )
        assert "2 author comment(s) withheld" in human.output
        machine = CliRunner().invoke(
            main,
            ["review-brief", "a", "--since", "main", "--project", str(project), "--json"],
        )
        assert json.loads(machine.output)["withheld"]["count"] == 2

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
        payload = json.loads(result.output)
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
        payload = json.loads(machine.output)
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
        payload = json.loads(result.output)
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
        payload = json.loads(result.output)
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
        payload = json.loads(result.output)
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
        payload = json.loads(result.output)
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
