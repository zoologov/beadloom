"""A gate finding names its owner (BDL-068 S6, offered by beadloom-0mdo.76).

This branch carried a red Gate across two waves of S6 — two stale docs owned by
no bead in the running plan — and every gate owner in those waves had to be told
by the coordinator, by hand, that the red was not theirs. A red everyone learns
to ignore, arriving on the instrument rather than in the suite.

Four properties, and the last three are what keep the first from lying:

1. a finding whose node a claimed bead declares names that bead;
2. ``unowned`` is a VERDICT — a node was derived and no claim covers it — and it
   is a different fact from ``unattributed``, where no node could be derived at
   all;
3. a tracker that cannot answer is a reason on the whole report, never an
   absence of owners, because "nobody owns this" and "nobody was asked" would
   otherwise read alike;
4. none of it touches the verdict or the exit code.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.gate import run_ci_gate
from beadloom.application.gate_ownership import (
    OWNED,
    UNATTRIBUTED,
    UNOWNED,
    derive_gate_ownership,
    gate_ownership_lines,
)
from beadloom.application.guards.contract import ClaimedBead
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

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


def _project(tmp_path: Path) -> Path:
    """A project whose gate fails with one finding, about the node ``beta``."""
    root = tmp_path / "proj"
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(_GRAPH, encoding="utf-8")
    (graph / "rules.yml").write_text(_RULES, encoding="utf-8")
    for domain in ("alpha", "beta"):
        (root / "src" / domain).mkdir(parents=True)
        (root / "src" / domain / f"{domain}.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "alpha" / "inner.py").write_text("y = 2\n", encoding="utf-8")
    from beadloom.application.reindex import reindex

    reindex(root)
    return root


def _document_of_beta(root: Path) -> Path:
    """Give ``beta`` a document, so the doc-path route has something to join on."""
    (root / "docs").mkdir()
    (root / "docs" / "beta.md").write_text("# Beta\n", encoding="utf-8")
    graph = root / ".beadloom" / "_graph" / "graph.yml"
    graph.write_text(
        graph.read_text(encoding="utf-8").replace(
            '    source: src/beta\n', '    source: src/beta\n    docs:\n      - docs/beta.md\n'
        ),
        encoding="utf-8",
    )
    from beadloom.application.reindex import reindex

    reindex(root)
    return root


def _bead(bead_id: str, refs: str) -> ClaimedBead:
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


class TestWhoOwnsAFinding:
    def test_a_claimed_bead_that_declares_the_node_owns_the_finding(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(node="beta")],
            tracker=_Tracker(_bead("bd-1", "beta")),
        )
        assert [owner.verdict for owner in ownership.owners] == [OWNED]
        assert ownership.owners[0].beads == ("bd-1",)
        assert ownership.owners[0].node == "beta"

    def test_a_node_no_claimed_bead_declares_is_unowned(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(node="beta")],
            tracker=_Tracker(_bead("bd-1", "alpha")),
        )
        assert [owner.verdict for owner in ownership.owners] == [UNOWNED]
        assert ownership.owners[0].beads == ()
        assert ownership.none_owned

    def test_unowned_is_reported_as_a_verdict_not_as_a_blank(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(node="beta")],
            tracker=_Tracker(_bead("bd-1", "alpha")),
        )
        text = "\n".join(gate_ownership_lines(ownership))
        assert "unowned" in text
        assert "no bead claimed now declares" in text

    def test_a_finding_with_no_node_and_no_path_is_unattributed(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(rule="reindex")],
            tracker=_Tracker(_bead("bd-1", "alpha")),
        )
        assert [owner.verdict for owner in ownership.owners] == [UNATTRIBUTED]
        assert ownership.owners[0].node is None
        text = "\n".join(gate_ownership_lines(ownership))
        assert "unattributed" in text

    def test_a_path_resolves_to_the_node_that_owns_it(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(locations=[{"file": "src/beta/beta.py"}])],
            tracker=_Tracker(_bead("bd-1", "beta")),
        )
        assert ownership.owners[0].node == "beta"
        assert ownership.owners[0].verdict == OWNED
        assert "src/beta/beta.py" in ownership.owners[0].where

    def test_a_doc_path_resolves_to_the_node_the_document_is_declared_for(
        self, tmp_path: Path
    ) -> None:
        """Half this gate's findings are about documents, which no source owns.

        A doc path is joined through the ``docs`` table, and the documentation
        root is read from the project's own configuration rather than assumed,
        so a project that renames ``docs/`` is still joined correctly.
        """
        root = _document_of_beta(_project(tmp_path))
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(locations=[{"file": "docs/beta.md"}])],
            tracker=_Tracker(_bead("bd-1", "beta")),
        )
        assert ownership.owners[0].node == "beta"
        assert ownership.owners[0].where == "documented node of docs/beta.md"

    def test_a_bead_declaring_a_parent_owns_a_finding_about_its_child(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(node="alpha-inner")],
            tracker=_Tracker(_bead("bd-1", "alpha")),
        )
        assert ownership.owners[0].verdict == OWNED
        assert ownership.owners[0].beads == ("bd-1",)

    def test_a_child_declaration_does_not_own_a_finding_about_its_parent(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(node="alpha")],
            tracker=_Tracker(_bead("bd-1", "alpha-inner")),
        )
        assert ownership.owners[0].verdict == UNOWNED


class TestWhatTheReportWillNotClaim:
    def test_a_tracker_that_cannot_answer_is_a_reason_not_an_empty_claim(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        tracker = _SilentTracker()
        ownership = derive_gate_ownership(
            root, findings=[_finding(node="beta")], tracker=tracker
        )
        assert tracker.asked == 1
        assert ownership.reason is not None
        assert ownership.owners == ()
        assert not ownership.none_owned
        assert "could not" in "\n".join(gate_ownership_lines(ownership))

    def test_a_project_with_no_index_says_so_rather_than_calling_everything_unowned(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "bare"
        root.mkdir()
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(node="beta")],
            tracker=_Tracker(_bead("bd-1", "alpha")),
        )
        assert ownership.owners == ()
        assert ownership.reason is not None
        assert "index" in ownership.reason

    def test_a_claim_whose_own_declaration_cannot_be_read_qualifies_unowned(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(node="beta")],
            tracker=_Tracker(
                _bead("bd-1", "alpha"),
                ClaimedBead(id="bd-2", title="bd-2", declaration="no scope here"),
            ),
        )
        assert ownership.owners[0].verdict == UNOWNED
        assert [claim.bead_id for claim in ownership.unread] == ["bd-2"]
        text = "\n".join(gate_ownership_lines(ownership))
        assert "bd-2" in text
        assert "not a proof" in text

    def test_no_finding_means_the_tracker_is_never_asked(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        tracker = _Tracker(_bead("bd-1", "alpha"))
        ownership = derive_gate_ownership(root, findings=[], tracker=tracker)
        assert tracker.asked == 0
        assert gate_ownership_lines(ownership) == []


class TestThePopulationTheClaimIsReadFrom:
    def test_the_owner_is_a_bead_and_never_the_work_item(self, tmp_path: Path) -> None:
        """The decision, pinned: a claim is a bead, not the branch's approval.

        The work item's axes keep every node of this branch in scope, so an
        owner derived from them would name the work item for every finding —
        the one sentence every agent on the branch already shares, and not the
        sentence the coordinator had to write by hand.
        """
        root = _project(tmp_path)
        ownership = derive_gate_ownership(
            root,
            findings=[_finding(node="beta")],
            tracker=_Tracker(_bead("bd-1", "alpha")),
        )
        assert ownership.claimed == ("bd-1",)
        assert ownership.owners[0].verdict == UNOWNED


class TestTheVerdictIsUnchanged:
    def test_naming_an_owner_changes_neither_ok_nor_the_step_statuses(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        without = run_ci_gate(root, fail_on=None, hub_exports=[], no_reindex=True)
        with_owner = run_ci_gate(
            root,
            fail_on=None,
            hub_exports=[],
            no_reindex=True,
            tracker=_Tracker(_bead("bd-1", "beta")),
        )
        assert without.ok is with_owner.ok
        assert [(s.name, s.status) for s in without.steps] == [
            (s.name, s.status) for s in with_owner.steps
        ]
        assert with_owner.ownership is not None
        assert with_owner.ownership.owners[0].verdict == OWNED

    def test_ownership_is_not_a_step(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        result = run_ci_gate(
            root,
            fail_on=None,
            hub_exports=[],
            no_reindex=True,
            tracker=_Tracker(_bead("bd-1", "beta")),
        )
        assert "ownership" not in {step.name for step in result.steps}

    def test_a_run_given_no_tracker_makes_no_ownership_claim(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        result = run_ci_gate(root, fail_on=None, hub_exports=[], no_reindex=True)
        assert result.ownership is None


class TestASyncFindingNamesItsNode:
    def test_a_stale_pair_carries_the_ref_id_as_a_field(self) -> None:
        from beadloom.application.gate import _sync_finding

        finding = _sync_finding(
            {"doc_path": "docs/x.md", "ref_id": "beta", "status": "stale", "reason": "hash"}
        )
        assert finding["node"] == "beta"

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
    def test_the_json_surface_carries_a_verdict_for_every_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _project(tmp_path)
        _claim_beads(monkeypatch, _bead("bd-1", "alpha"))
        result = CliRunner().invoke(
            main, ["ci", "--project", str(root), "--format", "json"]
        )
        payload = json.loads(result.stdout)
        assert payload["ownership"]["reason"] is None
        verdicts = {row["verdict"] for row in payload["ownership"]["findings"]}
        assert verdicts == {UNOWNED}
        assert payload["ownership"]["claimed"] == ["bd-1"]

    def test_the_human_surface_prints_the_block_under_the_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _project(tmp_path)
        _claim_beads(monkeypatch, _bead("bd-1", "alpha"))
        result = CliRunner().invoke(
            main, ["ci", "--project", str(root), "--format", "rich"]
        )
        assert "Findings by owner" in result.output
        assert result.output.index("FAIL — gate blocked") < result.output.index(
            "Findings by owner"
        )

    def test_the_github_surface_states_that_no_finding_is_owned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _project(tmp_path)
        _claim_beads(monkeypatch, _bead("bd-1", "alpha"))
        result = CliRunner().invoke(
            main, ["ci", "--project", str(root), "--format", "github"]
        )
        assert "::notice::" in result.output
        assert "no finding of this run is owned by a bead claimed now" in result.output


def _claim_beads(monkeypatch: pytest.MonkeyPatch, *beads: ClaimedBead) -> None:
    """Make the real service-layer tracker answer with *beads*, without ``bd``."""
    from beadloom.services import guard_probes

    monkeypatch.setattr(
        guard_probes.BdWorkTracker,
        "claimed_beads",
        lambda _self: beads,
    )
