"""A gate finding names its owner: the bead whose commits changed its files.

BDL-068 S6 (offered by beadloom-0mdo.76) added the report, attributing a finding to
every claimed bead whose ``refs:`` declared the node that covers it. BDL-083 S1c
(``beadloom-b23f``; BDL-UX #329; RFC D3) replaced that rule after the first outside
adopter measured it: a bead was told it owned 36 findings on files it never touched,
because its ``refs:`` named the node that covers the frontend's source whole.

Four properties, and the last three are what keep the first from lying:

1. a finding is owned by a claimed bead whose commits on the branch changed a file
   the finding is about, and by no bead whose node merely covers that file;
2. ``unattributed`` is the answer when no claimed bead's commits changed such a
   file, with the reason on the finding;
3. a tracker that cannot answer, a missing index and a git that cannot list the
   branch's commits are a reason on the whole report, never an absence of owners;
4. none of it touches the verdict or the exit code, and every surface prints the
   rule it attributed by.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.gate import run_ci_gate
from beadloom.application.gate_ownership import (
    ATTRIBUTION_RULE,
    NO_TRACKER,
    OWNED,
    UNATTRIBUTED,
    derive_gate_ownership,
    gate_ownership_lines,
)
from beadloom.application.guards.contract import ClaimedBead
from beadloom.services.cli import main
from tests.support.committed_project import commit_project, git

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.gate import Finding


class _Tracker:
    """A ``WorkTracker`` double that answers with whatever the test claimed."""

    def __init__(self, *beads: ClaimedBead) -> None:
        self._beads: tuple[ClaimedBead, ...] = beads
        self.asked = 0

    def claimed_beads(self) -> tuple[ClaimedBead, ...] | None:
        self.asked += 1
        return self._beads


class _SilentTracker:
    """A tracker that cannot answer — the ``None`` the port defines."""

    def __init__(self) -> None:
        self.asked = 0

    def claimed_beads(self) -> tuple[ClaimedBead, ...] | None:
        self.asked += 1
        return None


_GRAPH = """\
nodes:
  - ref_id: root
    kind: service
    summary: "Root service"
  - ref_id: alpha
    kind: domain
    summary: "Alpha domain"
    source: src/alpha
  - ref_id: beta
    kind: domain
    summary: "Beta domain"
    source: src/beta
    docs:
      - docs/beta.md
  - ref_id: alpha-inner
    kind: component
    summary: "A component of alpha"
    source: src/alpha/inner.py
edges:
  - src: alpha
    dst: root
    kind: part_of
  - src: alpha-inner
    dst: alpha
    kind: part_of
"""

_RULES = """\
version: 3
rules:
  - name: domain-needs-parent
    description: "Every domain must be part_of the root"
    severity: error
    require:
      for: { kind: domain }
      has_edge_to: { ref_id: root }
      edge_kind: part_of
"""

_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")


def _project(tmp_path: Path) -> Path:
    """A committed project on a working branch; its gate fails with one finding, about ``beta``."""
    root = tmp_path / "proj"
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(_GRAPH, encoding="utf-8")
    (graph / "rules.yml").write_text(_RULES, encoding="utf-8")
    (root / ".gitignore").write_text(".beadloom/*.db*\n", encoding="utf-8")
    for domain in ("alpha", "beta"):
        (root / "src" / domain).mkdir(parents=True)
        (root / "src" / domain / f"{domain}.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "alpha" / "inner.py").write_text("y = 2\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "beta.md").write_text("# Beta\n", encoding="utf-8")
    commit_project(root)
    git(root, "branch", "-M", "main")
    git(root, "switch", "-q", "-c", "features/X")
    from beadloom.application.reindex import reindex

    reindex(root)
    return root


def _commit(root: Path, path: str, message: str, *, bead: str | None = None) -> None:
    """Change *path* and commit it with *message*, bound to *bead* by its ``Bead:`` trailer."""
    target = root / path
    target.write_text(target.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    git(root, "add", path)
    trailer = () if bead is None else ("-m", f"Bead: {bead}")
    git(root, *_IDENTITY, "commit", "-q", "-m", message, *trailer)


def _bead(bead_id: str, refs: str = "beta") -> ClaimedBead:
    return ClaimedBead(id=bead_id, title=bead_id, declaration=f"refs: {refs}")


def _finding(**fields: object) -> Finding:
    base: Finding = {
        "kind": "lint",
        "rule": "a-rule",
        "severity": "error",
        "locations": [],
        "why": "something",
        "remediation": None,
    }
    base.update(fields)
    return base


def _on(path: str) -> Finding:
    return _finding(locations=[{"file": path}])


class TestWhoOwnsAFinding:
    def test_the_bead_whose_commit_changed_the_file_owns_the_finding(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", "beta moves", bead="bd-1")
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-1"))
        )
        assert [owner.verdict for owner in ownership.owners] == [OWNED]
        assert ownership.owners[0].beads == ("bd-1",)
        assert ownership.owners[0].where == "src/beta/beta.py, changed by its commits"

    def test_a_bead_whose_node_covers_the_file_owns_nothing_it_did_not_commit_to(
        self, tmp_path: Path
    ) -> None:
        """The #329 shape: the node covers the directory, the commits are elsewhere."""
        root = _project(tmp_path)
        _commit(root, "src/alpha/alpha.py", "alpha moves", bead="bd-1")
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-1", "beta"))
        )
        assert [owner.verdict for owner in ownership.owners] == [UNATTRIBUTED]
        assert ownership.owners[0].beads == ()
        assert ownership.none_owned

    def test_of_two_beads_in_flight_only_the_one_that_changed_the_file_owns_it(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", "beta moves", bead="bd-a")
        ownership = derive_gate_ownership(
            root,
            findings=[_on("src/beta/beta.py")],
            tracker=_Tracker(_bead("bd-a"), _bead("bd-b", "root")),
        )
        assert ownership.owners[0].beads == ("bd-a",)
        assert [claim.bead_id for claim in ownership.owning_nothing()] == ["bd-b"]

    def test_a_finding_about_a_node_is_owned_by_the_bead_that_changed_a_file_it_owns(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _commit(root, "src/alpha/alpha.py", "alpha moves", bead="bd-1")
        ownership = derive_gate_ownership(
            root, findings=[_finding(node="alpha")], tracker=_Tracker(_bead("bd-1", "root"))
        )
        assert ownership.owners[0].verdict == OWNED

    def test_a_nested_nodes_file_does_not_make_its_parent_s_finding_owned(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _commit(root, "src/alpha/inner.py", "inner moves", bead="bd-1")
        ownership = derive_gate_ownership(
            root, findings=[_finding(node="alpha")], tracker=_Tracker(_bead("bd-1", "alpha"))
        )
        assert ownership.owners[0].verdict == UNATTRIBUTED
        assert (
            ownership.owners[0].where == "no claimed bead's commits changed the files alpha owns"
        )

    def test_a_document_located_in_the_documentation_root_s_frame_is_matched(
        self, tmp_path: Path
    ) -> None:
        """The sync steps locate a document as the ``docs`` table stores it."""
        root = _project(tmp_path)
        _commit(root, "docs/beta.md", "the beta document", bead="bd-1")
        ownership = derive_gate_ownership(
            root, findings=[_on("beta.md")], tracker=_Tracker(_bead("bd-1"))
        )
        assert ownership.owners[0].verdict == OWNED
        assert ownership.owners[0].files == ("docs/beta.md",)

    def test_a_stale_pair_is_owned_by_the_bead_that_changed_its_code_file(
        self, tmp_path: Path
    ) -> None:
        from beadloom.application.gate import _sync_finding

        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", "beta moves", bead="bd-1")
        stale = _sync_finding(
            {
                "doc_path": "beta.md",
                "code_path": "src/beta/beta.py",
                "ref_id": "beta",
                "status": "stale",
                "reason": "hash",
            }
        )
        ownership = derive_gate_ownership(root, findings=[stale], tracker=_Tracker(_bead("bd-1")))
        assert ownership.owners[0].verdict == OWNED

    def test_a_trailer_names_a_bead_only_by_its_whole_id(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", "the neighbours\n\nBead: bd-10\nBead: bd-1.2")
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-1"))
        )
        assert ownership.owners[0].verdict == UNATTRIBUTED
        assert ownership.claims[0].commits == 0

    def test_a_commit_naming_no_claimed_bead_attributes_nothing(self, tmp_path: Path) -> None:
        """An older commit of the branch, made under a bead that is closed now."""
        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", "the first work item", bead="bd-0")
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-1"))
        )
        assert ownership.owners[0].verdict == UNATTRIBUTED

    def test_a_file_the_bead_s_refs_name_is_unattributed_without_a_commit(
        self, tmp_path: Path
    ) -> None:
        """RFC D3 as amended on 2026-10-19: a path named in ``refs:`` attributes nothing."""
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_on("src/beta/beta.py")],
            tracker=_Tracker(_bead("bd-1", "src/beta/beta.py")),
        )
        assert [owner.verdict for owner in ownership.owners] == [UNATTRIBUTED]
        assert ownership.claims[0].commits == 0

    def test_a_commit_already_on_the_trunk_is_nobody_s_work_in_flight(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        git(root, "switch", "-q", "main")
        _commit(root, "src/beta/beta.py", "landed", bead="bd-1")
        git(root, "switch", "-q", "-c", "features/Y")
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-1"))
        )
        assert ownership.owners[0].verdict == UNATTRIBUTED

    def test_a_finding_with_no_file_and_no_node_is_unattributed_and_says_why(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root, findings=[_finding(rule="reindex")], tracker=_Tracker(_bead("bd-1"))
        )
        assert [owner.verdict for owner in ownership.owners] == [UNATTRIBUTED]
        assert ownership.owners[0].where == "it locates no file and names no node"
        text = "\n".join(gate_ownership_lines(ownership))
        assert "1 about no file a commit could have changed" in text

    def test_an_uncommitted_change_is_unattributed_and_counted_as_uncommitted(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        (root / "src" / "beta" / "beta.py").write_text("x = 2\n", encoding="utf-8")
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-1"))
        )
        assert ownership.owners[0].verdict == UNATTRIBUTED
        assert ownership.owners[0].uncommitted
        text = "\n".join(gate_ownership_lines(ownership))
        assert "1 on files the working tree changes and no commit holds yet" in text


class TestACommitIsABeadsByItsTrailer:
    """RFC D10 (the owner's ruling of 2026-10-19; S1R Minor 3; ``beadloom-7kas``)."""

    def test_the_bead_trailer_binds_the_commit(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", "[X-1] fix: beta moves", bead="bd-1")
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-1"))
        )
        assert ownership.owners[0].beads == ("bd-1",)
        assert ownership.claims[0].commits == 1

    @pytest.mark.parametrize(
        "message",
        [
            "beta moves (bd-1)",
            "[X-1] chore: the merge slot released from bd-1",
            "[X-1] test: the entries re-measured\n\nMeasured for bd-1 and bd-2.",
            "subject\n\nBead: bd-1\n\na trailer-shaped line above a closing paragraph",
            "subject\n\nRefs: bd-1",
        ],
        ids=["subject", "landing-note", "body", "not-the-last-paragraph", "another-key"],
    )
    def test_a_mention_anywhere_else_binds_nothing(self, tmp_path: Path, message: str) -> None:
        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", message)
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-1"))
        )
        assert [owner.verdict for owner in ownership.owners] == [UNATTRIBUTED]
        assert ownership.claims[0].commits == 0

    def test_the_trailer_key_is_read_as_git_reads_it_whatever_its_case(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", "beta moves\n\nbead: bd-1")
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-1"))
        )
        assert ownership.owners[0].verdict == OWNED

    def test_the_printed_rule_names_the_trailer(self) -> None:
        assert ATTRIBUTION_RULE == "by the files the commits carrying `Bead: <id>` changed"


class TestTheLinesNameTheRule:
    def test_the_block_names_the_rule_the_base_and_each_owner_s_clause(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", "beta moves", bead="bd-a")
        ownership = derive_gate_ownership(
            root,
            findings=[_on("src/beta/beta.py")],
            tracker=_Tracker(_bead("bd-a"), _bead("bd-b")),
        )
        lines = gate_ownership_lines(ownership)
        assert lines[0] == "Findings by owner:"
        assert lines[1] == f"  attributed {ATTRIBUTION_RULE}, over main..HEAD"
        assert "  owned by bd-a: 1 finding(s), by the files its commits changed" in lines
        assert "  bd-b owns no finding: no commit on main..HEAD carries `Bead: bd-b`" in lines

    def test_a_bead_whose_commits_explain_nothing_is_told_so_in_its_own_words(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _commit(root, "src/alpha/alpha.py", "alpha moves", bead="bd-b")
        ownership = derive_gate_ownership(
            root, findings=[_on("src/beta/beta.py")], tracker=_Tracker(_bead("bd-b"))
        )
        assert (
            "  bd-b owns no finding: its 1 commit(s) changed none of the files these "
            "findings are about"
        ) in gate_ownership_lines(ownership)


class TestWhatTheReportWillNotClaim:
    def test_a_tracker_that_cannot_answer_is_a_reason_not_an_empty_claim(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        tracker = _SilentTracker()
        ownership = derive_gate_ownership(root, findings=[_finding(node="beta")], tracker=tracker)
        assert tracker.asked == 1
        assert ownership.reason == NO_TRACKER
        assert ownership.owners == ()
        assert not ownership.none_owned

    def test_a_project_with_no_index_says_so_rather_than_calling_everything_unattributed(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "bare"
        root.mkdir()
        ownership = derive_gate_ownership(
            root, findings=[_finding(node="beta")], tracker=_Tracker(_bead("bd-1")), base="main"
        )
        assert ownership.owners == ()
        assert ownership.reason is not None
        assert "index" in ownership.reason

    def test_a_git_that_cannot_list_the_branch_s_commits_is_a_reason(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_on("src/beta/beta.py")],
            tracker=_Tracker(_bead("bd-1")),
            base="no-such-ref",
        )
        assert ownership.owners == ()
        assert ownership.reason is not None
        assert "no-such-ref" in ownership.reason

    def test_no_finding_means_the_tracker_is_never_asked(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        tracker = _Tracker(_bead("bd-1"))
        ownership = derive_gate_ownership(root, findings=[], tracker=tracker)
        assert tracker.asked == 0
        assert gate_ownership_lines(ownership) == []


class TestTheVerdictIsUnchanged:
    def test_naming_an_owner_changes_neither_ok_nor_the_step_statuses(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _commit(root, "src/beta/beta.py", "beta moves", bead="bd-1")
        without = run_ci_gate(root, fail_on=None, hub_exports=[], no_reindex=True)
        with_owner = run_ci_gate(
            root,
            fail_on=None,
            hub_exports=[],
            no_reindex=True,
            tracker=_Tracker(_bead("bd-1")),
        )
        assert without.ok is with_owner.ok
        assert [(s.name, s.status) for s in without.steps] == [
            (s.name, s.status) for s in with_owner.steps
        ]
        assert with_owner.ownership is not None
        assert with_owner.ownership.owned

    def test_ownership_is_not_a_step(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        result = run_ci_gate(
            root, fail_on=None, hub_exports=[], no_reindex=True, tracker=_Tracker(_bead("bd-1"))
        )
        assert "ownership" not in {step.name for step in result.steps}

    def test_a_run_given_no_tracker_makes_no_ownership_claim(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        result = run_ci_gate(root, fail_on=None, hub_exports=[], no_reindex=True)
        assert result.ownership is None


class TestASyncFindingNamesItsNodeAndItsFiles:
    def test_a_stale_pair_carries_the_ref_id_and_both_files(self) -> None:
        from beadloom.application.gate import _sync_finding

        finding = _sync_finding(
            {
                "doc_path": "x.md",
                "code_path": "src/x.py",
                "ref_id": "beta",
                "status": "stale",
                "reason": "hash",
            }
        )
        assert finding["node"] == "beta"
        assert finding["locations"] == [{"file": "x.md"}, {"file": "src/x.py"}]

    def test_a_missing_pair_carries_the_ref_id_as_a_field(self) -> None:
        from beadloom.application.gate import _sync_finding

        finding = _sync_finding(
            {"doc_path": "docs/x.md", "ref_id": "beta", "status": "missing", "reason": "doc"}
        )
        assert finding["node"] == "beta"

    def test_a_document_missing_sections_carries_the_ref_id_as_a_field(self) -> None:
        from beadloom.application.gate import _sync_shape_finding
        from beadloom.doc_sync.doc_shape import REASON_MISSING_SECTIONS

        finding = _sync_shape_finding(
            {
                "doc_path": "docs/x.md",
                "ref_id": "beta",
                "details": "Purpose",
                "reason": REASON_MISSING_SECTIONS,
            }
        )
        assert finding["node"] == "beta"


class TestTheSurfacesSayTheSameThing:
    def test_the_json_surface_carries_the_rule_the_base_and_a_verdict_per_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _project(tmp_path)
        _claim_beads(monkeypatch, _bead("bd-1", "alpha"))
        result = CliRunner().invoke(main, ["ci", "--project", str(root), "--format", "json"])
        payload = json.loads(result.stdout)
        ownership = payload["ownership"]
        assert ownership["reason"] is None
        assert ownership["rule"] == ATTRIBUTION_RULE
        assert ownership["base"] == "main"
        assert {row["verdict"] for row in ownership["findings"]} == {UNATTRIBUTED}
        assert ownership["claimed"] == ["bd-1"]
        assert ownership["claims"] == [{"bead": "bd-1", "commits": 0}]

    def test_the_human_surface_prints_the_block_under_the_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _project(tmp_path)
        _claim_beads(monkeypatch, _bead("bd-1", "alpha"))
        result = CliRunner().invoke(main, ["ci", "--project", str(root), "--format", "rich"])
        assert ATTRIBUTION_RULE in result.output
        assert result.output.index("FAIL — gate blocked") < result.output.index(
            "Findings by owner"
        )

    def test_the_github_surface_names_the_rule_and_that_no_finding_is_owned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _project(tmp_path)
        _claim_beads(monkeypatch, _bead("bd-1", "alpha"))
        result = CliRunner().invoke(main, ["ci", "--project", str(root), "--format", "github"])
        assert f"::notice::attributed {ATTRIBUTION_RULE}, over main..HEAD" in result.output
        assert "no finding of this run is owned by a bead claimed now" in result.output

    def test_the_mcp_payload_is_the_json_report_s(self, tmp_path: Path) -> None:
        from beadloom.application.gate_ownership import ownership_payload
        from beadloom.services.mcp_server import _finding_owners

        root = _project(tmp_path)
        result = run_ci_gate(
            root, fail_on=None, hub_exports=[], no_reindex=True, tracker=_Tracker(_bead("bd-1"))
        )
        assert result.ownership is not None
        assert _finding_owners(result) == ownership_payload(result.ownership)
        assert _finding_owners(result)["rule"] == ATTRIBUTION_RULE


def _claim_beads(monkeypatch: pytest.MonkeyPatch, *beads: ClaimedBead) -> None:
    """Make the real service-layer tracker answer with *beads*, without ``bd``."""
    from beadloom.services import guard_probes

    monkeypatch.setattr(
        guard_probes.BdWorkTracker,
        "claimed_beads",
        lambda _self: beads,
    )
