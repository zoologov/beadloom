"""Tests for the MCP process-tools (BDL-048 BEAD-03).

Four deterministic, tool-agnostic process steps callable from any MCP client:

- ``task_init``     — scaffold docs folder + role DAG (asserts the `bd` calls).
- ``bead_context``  — one payload: ctx + why + CONTEXT/ACTIVE excerpt + rules.
- ``complete_bead`` — refusing gate: run_ci_gate (+ tests); PASS closes, FAIL refuses.
- ``checkpoint``    — `bd comments add` + timestamped ACTIVE.md note.

Every ``bd`` invocation and ``run_ci_gate`` is MOCKED — no real ``bd``, no network.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import yaml

from beadloom.services.bd_seam import BdResult, BdUnavailableError

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A reindexed project with a graph + rules for ctx/why/rule tests."""
    proj = tmp_path / "proj"
    proj.mkdir()
    graph_dir = proj / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {
                        "ref_id": "FEAT-1",
                        "kind": "feature",
                        "summary": "Track filtering",
                        "docs": ["docs/spec.md"],
                    },
                    {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
                ],
                "edges": [{"src": "FEAT-1", "dst": "routing", "kind": "part_of"}],
            }
        )
    )
    (graph_dir / "rules.yml").write_text(
        yaml.dump(
            {
                "version": 3,
                "rules": [
                    {
                        "name": "feature-needs-domain",
                        "description": "Every feature must be part_of a domain",
                        "require": {
                            "for": {"kind": "feature"},
                            "has_edge_to": {"kind": "domain"},
                            "edge_kind": "part_of",
                        },
                    }
                ],
            }
        )
    )
    docs = proj / "docs"
    docs.mkdir()
    (docs / "spec.md").write_text("## Spec\n\nFiltering.\n")
    src = proj / "src"
    src.mkdir()
    (src / "api.py").write_text("# beadloom:feature=FEAT-1\ndef f():\n    pass\n")

    from beadloom.application.reindex import reindex

    reindex(proj)
    return proj


def _bd_show_json(ref_id: str, *, area: str = "FEAT-1") -> str:
    """Minimal `bd show --json` payload referencing a graph ref via design."""
    import json

    return json.dumps(
        [
            {
                "id": ref_id,
                "title": f"[dev] work on {area}",
                "status": "in_progress",
                "design": f"ref: {area}",
                "description": f"Touches {area}.",
            }
        ]
    )


# ---------------------------------------------------------------------------
# task_init
# ---------------------------------------------------------------------------


class TestTaskInit:
    def test_creates_docs_folder_full_flow(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_task_init

        created_ids = ["bd-1", "bd-2", "bd-3", "bd-4"]
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = _fake_bd_create_factory(created_ids)
            result = handle_task_init(project, type_="feature", key="ABC-1")

        feature_dir = project / ".claude" / "development" / "docs" / "features" / "ABC-1"
        for name in ("PRD.md", "RFC.md", "CONTEXT.md", "PLAN.md", "ACTIVE.md"):
            assert (feature_dir / name).is_file(), name
        assert result["doc_paths"]
        assert result["bead_ids"] == created_ids

    def test_simplified_flow_for_task(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_task_init

        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = _fake_bd_create_factory(["bd-1", "bd-2", "bd-3", "bd-4"])
            handle_task_init(project, type_="task", key="T-9")

        d = project / ".claude" / "development" / "docs" / "features" / "T-9"
        assert (d / "BRIEF.md").is_file()
        assert (d / "ACTIVE.md").is_file()
        assert not (d / "PRD.md").exists()

    def test_builds_four_role_dag(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_task_init

        calls: list[list[str]] = []

        def _record(args: list[str], **_: object) -> BdResult:
            calls.append(args)
            if args[0] == "create":
                idx = sum(1 for c in calls if c[0] == "create")
                return BdResult(0, f"bd-{idx}\n", "")
            return BdResult(0, "", "")

        with patch("beadloom.services.mcp_server.run_bd", side_effect=_record):
            handle_task_init(project, type_="feature", key="ABC-2")

        roles = [c for c in calls if c[0] == "create"]
        # 4 mandatory roles: dev, test, review, tech-writer.
        assert len(roles) == 4
        joined = " ".join(" ".join(c) for c in roles)
        for role in ("dev", "test", "review", "tech-writer"):
            assert role in joined
        # Dependencies are wired (test←dev, review←test, tech-writer←review).
        dep_calls = [c for c in calls if c[0] == "dep"]
        assert len(dep_calls) == 3

    def test_bd_unavailable_returns_structured_error(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_task_init

        with patch(
            "beadloom.services.mcp_server.run_bd",
            side_effect=BdUnavailableError("no bd"),
        ):
            result = handle_task_init(project, type_="feature", key="ABC-3")
        assert result["status"] == "ERROR"
        assert "bd" in result["error"]


def _fake_bd_create_factory(ids: list[str]) -> object:
    counter = {"n": 0}

    def _fake(args: list[str], **_: object) -> BdResult:
        if args[0] == "create":
            i = counter["n"]
            counter["n"] += 1
            out = ids[i] if i < len(ids) else f"bd-{i + 1}"
            return BdResult(0, out + "\n", "")
        return BdResult(0, "", "")

    return _fake


# ---------------------------------------------------------------------------
# bead_context
# ---------------------------------------------------------------------------


class TestBeadContext:
    def test_assembles_ctx_why_and_rules(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_bead_context

        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, _bd_show_json("bd-1", area="FEAT-1"), "")
            result = handle_bead_context(project, bead="bd-1")

        assert result["bead"] == "bd-1"
        assert result["ref_id"] == "FEAT-1"
        assert "context" in result
        assert "impact" in result
        assert any(r["name"] == "feature-needs-domain" for r in result["active_rules"])

    def test_includes_doc_excerpt_when_present(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_bead_context

        feat = project / ".claude" / "development" / "docs" / "features" / "EPIC-1"
        feat.mkdir(parents=True)
        (feat / "CONTEXT.md").write_text("# CONTEXT\n\nImportant constraint.\n")
        (feat / "ACTIVE.md").write_text("# ACTIVE\n\nDoing the thing.\n")

        import json

        show = json.dumps(
            [{"id": "bd-1", "title": "t", "design": "ref: FEAT-1, epic: EPIC-1"}]
        )
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, show, "")
            result = handle_bead_context(project, bead="bd-1")

        assert "Important constraint" in (result["doc_excerpt"] or "")

    def test_bd_unavailable_returns_structured_error(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_bead_context

        with patch(
            "beadloom.services.mcp_server.run_bd",
            side_effect=BdUnavailableError("no bd"),
        ):
            result = handle_bead_context(project, bead="bd-1")
        assert result["status"] == "ERROR"


# ---------------------------------------------------------------------------
# complete_bead
# ---------------------------------------------------------------------------


class TestCompleteBead:
    def test_red_gate_refuses_and_does_not_close(self, project: Path) -> None:
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        red = GateResult(
            steps=[
                GateStep(
                    "lint",
                    passed=False,
                    findings=[{"rule": "x", "why": "boom"}],
                    summary="1 error",
                )
            ]
        )
        with patch("beadloom.services.mcp_server.run_ci_gate", return_value=red), patch(
            "beadloom.services.mcp_server.run_bd"
        ) as run_bd:
            result = handle_complete_bead(project, bead="bd-1", run_tests=False)

        assert result["status"] == "FAIL"
        assert result["findings"]
        # MUST NOT close the bead on a red gate.
        close_calls = [c for c in run_bd.call_args_list if c.args[0][0] == "close"]
        assert close_calls == []

    def test_green_gate_passes_and_closes(self, project: Path) -> None:
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        green = GateResult(steps=[GateStep("lint", passed=True, summary="clean")])
        with patch("beadloom.services.mcp_server.run_ci_gate", return_value=green), patch(
            "beadloom.services.mcp_server.run_bd"
        ) as run_bd:
            run_bd.return_value = BdResult(0, "next: bd-2\n", "")
            result = handle_complete_bead(project, bead="bd-1", run_tests=False)

        assert result["status"] == "PASS"
        close_calls = [c for c in run_bd.call_args_list if c.args[0][0] == "close"]
        assert len(close_calls) == 1
        assert "bd-1" in close_calls[0].args[0]

    def test_red_test_suite_refuses(self, project: Path) -> None:
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        green = GateResult(steps=[GateStep("lint", passed=True, summary="clean")])
        with patch("beadloom.services.mcp_server.run_ci_gate", return_value=green), patch(
            "beadloom.services.mcp_server._run_test_suite",
            return_value=(False, "2 failed"),
        ), patch("beadloom.services.mcp_server.run_bd") as run_bd:
            result = handle_complete_bead(project, bead="bd-1", run_tests=True)

        assert result["status"] == "FAIL"
        assert any("test" in str(f.get("kind", "")) for f in result["findings"])
        close_calls = [c for c in run_bd.call_args_list if c.args[0][0] == "close"]
        assert close_calls == []

    def test_bd_unavailable_returns_structured_error(self, project: Path) -> None:
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        green = GateResult(steps=[GateStep("lint", passed=True)])
        with patch("beadloom.services.mcp_server.run_ci_gate", return_value=green), patch(
            "beadloom.services.mcp_server.run_bd",
            side_effect=BdUnavailableError("no bd"),
        ):
            result = handle_complete_bead(project, bead="bd-1", run_tests=False)
        assert result["status"] == "ERROR"


# ---------------------------------------------------------------------------
# checkpoint
# ---------------------------------------------------------------------------


class TestCheckpoint:
    def test_adds_comment_and_active_note(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_checkpoint

        feat = project / ".claude" / "development" / "docs" / "features" / "EPIC-1"
        feat.mkdir(parents=True)
        active = feat / "ACTIVE.md"
        active.write_text("# ACTIVE\n\n## Progress\n")

        import json

        show = json.dumps([{"id": "bd-1", "design": "epic: EPIC-1"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [
                BdResult(0, show, ""),  # bd show
                BdResult(0, "", ""),  # bd comments add
            ]
            result = handle_checkpoint(project, bead="bd-1", text="did a thing")

        assert result["status"] == "OK"
        assert result["comment_added"] is True
        text = active.read_text()
        assert "did a thing" in text
        comment_calls = [c for c in run_bd.call_args_list if c.args[0][0] == "comments"]
        assert len(comment_calls) == 1

    def test_active_not_found_is_best_effort(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_checkpoint

        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [
                BdResult(0, "[]", ""),  # bd show — no epic
                BdResult(0, "", ""),  # comments add
            ]
            result = handle_checkpoint(project, bead="bd-1", text="note")

        assert result["status"] == "OK"
        assert result["comment_added"] is True
        assert result["active_updated"] is False

    def test_bd_unavailable_returns_structured_error(self, project: Path) -> None:
        from beadloom.services.mcp_server import handle_checkpoint

        with patch(
            "beadloom.services.mcp_server.run_bd",
            side_effect=BdUnavailableError("no bd"),
        ):
            result = handle_checkpoint(project, bead="bd-1", text="note")
        assert result["status"] == "ERROR"


# ---------------------------------------------------------------------------
# Tool registration + dispatch
# ---------------------------------------------------------------------------


def test_new_tools_registered() -> None:
    from beadloom.services.mcp_server import _TOOLS

    names = {t.name for t in _TOOLS}
    assert {"task_init", "bead_context", "complete_bead", "checkpoint"} <= names


def test_dispatch_routes_checkpoint(project: Path) -> None:
    from beadloom.infrastructure.db import open_db
    from beadloom.services.mcp_server import _dispatch_tool

    db_path = project / ".beadloom" / "beadloom.db"
    conn = open_db(db_path)
    try:
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [BdResult(0, "[]", ""), BdResult(0, "", "")]
            result = _dispatch_tool(
                conn,
                "checkpoint",
                {"bead": "bd-1", "text": "hi"},
                project_root=project,
            )
        assert result["status"] == "OK"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Hardening: task_init error/edge paths
# ---------------------------------------------------------------------------


class TestTaskInitHardening:
    def test_bd_create_failure_returns_structured_error(self, project: Path) -> None:
        """A non-zero `bd create` surfaces as a structured ERROR (not a crash),
        and the already-scaffolded docs are still reported."""
        from beadloom.services.mcp_server import handle_task_init

        def _fail_create(args: list[str], **_: object) -> BdResult:
            if args[0] == "create":
                return BdResult(1, "", "boom: db locked")
            return BdResult(0, "", "")

        with patch("beadloom.services.mcp_server.run_bd", side_effect=_fail_create):
            result = handle_task_init(project, type_="feature", key="ABC-9")

        assert result["status"] == "ERROR"
        assert "boom" in result["error"]
        assert result["doc_paths"]

    def test_dependency_edges_wire_chain(self, project: Path) -> None:
        """The 3 dep edges chain the roles dev<-test<-review<-tech-writer, each
        pointing at the previous role's created id."""
        from beadloom.services.mcp_server import handle_task_init

        calls: list[list[str]] = []

        def _record(args: list[str], **_: object) -> BdResult:
            calls.append(args)
            if args[0] == "create":
                idx = sum(1 for c in calls if c[0] == "create")
                return BdResult(0, f"id-{idx}\n", "")
            return BdResult(0, "", "")

        with patch("beadloom.services.mcp_server.run_bd", side_effect=_record):
            handle_task_init(project, type_="feature", key="ABC-10")

        deps = [c for c in calls if c[0] == "dep"]
        # ["dep", "add", <role_id>, <dep_id>] — each later role depends on prior.
        assert deps == [
            ["dep", "add", "id-2", "id-1"],
            ["dep", "add", "id-3", "id-2"],
            ["dep", "add", "id-4", "id-3"],
        ]

    def test_bug_type_uses_simple_docs_and_task_bead(self, project: Path) -> None:
        """A `bug` work item gets BRIEF/ACTIVE (not the full PRD set) and `task`
        beads (the bead type for non epic/feature)."""
        from beadloom.services.mcp_server import handle_task_init

        calls: list[list[str]] = []

        def _record(args: list[str], **_: object) -> BdResult:
            calls.append(args)
            if args[0] == "create":
                idx = sum(1 for c in calls if c[0] == "create")
                return BdResult(0, f"bd-{idx}\n", "")
            return BdResult(0, "", "")

        with patch("beadloom.services.mcp_server.run_bd", side_effect=_record):
            handle_task_init(project, type_="bug", key="BUG-1")

        d = project / ".claude" / "development" / "docs" / "features" / "BUG-1"
        assert (d / "BRIEF.md").is_file()
        assert not (d / "PRD.md").exists()
        creates = [c for c in calls if c[0] == "create"]
        assert all("--type" in c and "task" in c for c in creates)

    def test_idempotent_docs_not_overwritten(self, project: Path) -> None:
        """Re-running task_init does not clobber an existing doc's content."""
        from beadloom.services.mcp_server import handle_task_init

        d = project / ".claude" / "development" / "docs" / "features" / "ABC-11"
        d.mkdir(parents=True)
        (d / "PRD.md").write_text("MY DRAFT", encoding="utf-8")

        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = _fake_bd_create_factory(["a", "b", "c", "d"])
            handle_task_init(project, type_="feature", key="ABC-11")

        assert (d / "PRD.md").read_text(encoding="utf-8") == "MY DRAFT"


# ---------------------------------------------------------------------------
# Hardening: bead_context error/edge paths
# ---------------------------------------------------------------------------


class TestBeadContextHardening:
    def test_unresolvable_ref_returns_structured_error(self, project: Path) -> None:
        """A bead with no `ref:`/`area:` token cannot resolve a graph node -> a
        clean structured ERROR telling the agent to add the token."""
        import json

        from beadloom.services.mcp_server import handle_bead_context

        show = json.dumps([{"id": "bd-1", "title": "no ref here", "design": ""}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, show, "")
            result = handle_bead_context(project, bead="bd-1")

        assert result["status"] == "ERROR"
        assert "ref" in result["error"]

    def test_resolved_but_absent_ref_returns_structured_error(
        self, project: Path
    ) -> None:
        """A bead that resolves to a ref which is NOT a graph node degrades to a
        clean structured ERROR (no raised LookupError). The context builder would
        raise LookupError for an absent node; `handle_bead_context` now catches it
        and returns the {status: ERROR, ...} contract for direct callers too."""
        import json

        from beadloom.services.mcp_server import handle_bead_context

        show = json.dumps([{"id": "bd-1", "design": "ref: NOPE-404"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, show, "")
            result = handle_bead_context(project, bead="bd-1")

        assert result["status"] == "ERROR"
        assert "NOPE-404" in result["error"]
        assert "graph" in result["error"]

    def test_missing_context_active_docs_degrades(self, project: Path) -> None:
        """When the bead names an epic with NO CONTEXT/ACTIVE docs, doc_excerpt
        is None (best-effort, not an error)."""
        import json

        from beadloom.services.mcp_server import handle_bead_context

        show = json.dumps([{"id": "bd-1", "design": "ref: FEAT-1, epic: GHOST-1"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, show, "")
            result = handle_bead_context(project, bead="bd-1")

        assert result["status"] == "OK"
        assert result["doc_excerpt"] is None

    def test_bd_show_nonzero_yields_unresolvable(self, project: Path) -> None:
        """A failed `bd show` (non-zero) yields an empty record -> unresolvable
        ref error, not a crash."""
        from beadloom.services.mcp_server import handle_bead_context

        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(1, "", "no such bead")
            result = handle_bead_context(project, bead="bd-404")

        assert result["status"] == "ERROR"

    def test_bd_show_invalid_json_yields_unresolvable(self, project: Path) -> None:
        """Malformed `bd show` JSON is swallowed into an empty record."""
        from beadloom.services.mcp_server import handle_bead_context

        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, "{not json", "")
            result = handle_bead_context(project, bead="bd-1")

        assert result["status"] == "ERROR"

    def test_bd_show_dict_payload_resolves(self, project: Path) -> None:
        """`bd show --json` may return a bare object (not a list); the resolver
        handles both shapes."""
        import json

        from beadloom.services.mcp_server import handle_bead_context

        show = json.dumps({"id": "bd-1", "design": "ref: FEAT-1"})
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, show, "")
            result = handle_bead_context(project, bead="bd-1")

        assert result["status"] == "OK"
        assert result["ref_id"] == "FEAT-1"

    def test_active_rules_includes_deny_and_global_rules(self, tmp_path: Path) -> None:
        """`_active_rules_for_node` walks Deny/ForbidEdge/Cardinality + global
        rules, returning those whose matcher applies to the node."""
        import yaml

        proj = tmp_path / "proj"
        gdir = proj / ".beadloom" / "_graph"
        gdir.mkdir(parents=True)
        (gdir / "graph.yml").write_text(
            yaml.dump(
                {
                    "nodes": [
                        {"ref_id": "svcA", "kind": "service", "summary": "A"},
                        {"ref_id": "domB", "kind": "domain", "summary": "B"},
                    ],
                    "edges": [],
                }
            )
        )
        (gdir / "rules.yml").write_text(
            yaml.dump(
                {
                    "version": 3,
                    "rules": [
                        {
                            "name": "no-domain-depends-on-service",
                            "description": "domains must not depend on services",
                            "deny": {
                                "from": {"kind": "domain"},
                                "to": {"kind": "service"},
                                "edge_kind": "depends_on",
                            },
                        },
                        {
                            "name": "no-cycles",
                            "description": "no dependency cycles",
                            "forbid_cycles": {"edge_kind": "depends_on"},
                        },
                    ],
                }
            )
        )
        (proj / "docs").mkdir()
        from beadloom.application.reindex import reindex

        reindex(proj)

        import json

        show = json.dumps([{"id": "bd-1", "design": "ref: domB"}])
        from beadloom.services.mcp_server import handle_bead_context

        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, show, "")
            result = handle_bead_context(proj, bead="bd-1")

        names = {r["name"] for r in result["active_rules"]}
        # Deny rule applies (domB is a domain = from-matcher); global cycle rule
        # has no matcher so it is always active.
        assert "no-domain-depends-on-service" in names
        assert "no-cycles" in names

    def test_active_rules_empty_when_no_rules_file(self, tmp_path: Path) -> None:
        """No rules.yml -> empty active-rules list (not a crash)."""
        import yaml

        proj = tmp_path / "p2"
        gdir = proj / ".beadloom" / "_graph"
        gdir.mkdir(parents=True)
        (gdir / "graph.yml").write_text(
            yaml.dump(
                {"nodes": [{"ref_id": "n1", "kind": "domain", "summary": "x"}], "edges": []}
            )
        )
        (proj / "docs").mkdir()
        from beadloom.application.reindex import reindex

        reindex(proj)
        # Remove rules.yml if reindex created one.
        rules = gdir / "rules.yml"
        if rules.exists():
            rules.unlink()

        import json

        show = json.dumps([{"id": "bd-1", "design": "ref: n1"}])
        from beadloom.services.mcp_server import handle_bead_context

        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, show, "")
            result = handle_bead_context(proj, bead="bd-1")

        assert result["active_rules"] == []

    def test_active_rules_for_domain_node(self, project: Path) -> None:
        """A domain node still resolves its active rules (the require rule's
        for-matcher only matches features, so it does NOT apply to a domain)."""
        import json

        from beadloom.services.mcp_server import handle_bead_context

        show = json.dumps([{"id": "bd-1", "design": "ref: routing"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, show, "")
            result = handle_bead_context(project, bead="bd-1")

        assert result["status"] == "OK"
        rule_names = {r["name"] for r in result["active_rules"]}
        assert "feature-needs-domain" not in rule_names


# ---------------------------------------------------------------------------
# Hardening: complete_bead + _run_test_suite
# ---------------------------------------------------------------------------


class TestCompleteBeadHardening:
    def test_green_gate_but_close_fails_returns_error(self, project: Path) -> None:
        """Gate + tests pass but `bd close` fails -> ERROR (not a false PASS)."""
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        green = GateResult(steps=[GateStep("lint", passed=True, summary="clean")])
        with patch(
            "beadloom.services.mcp_server.run_ci_gate", return_value=green
        ), patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(1, "", "close exploded")
            result = handle_complete_bead(project, bead="bd-1", run_tests=False)

        assert result["status"] == "ERROR"
        assert "close" in result["error"]

    def test_close_bd_unavailable_after_green_gate(self, project: Path) -> None:
        """Gate passes, then `bd close` hits a missing binary -> structured ERROR."""
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        green = GateResult(steps=[GateStep("lint", passed=True)])
        with patch(
            "beadloom.services.mcp_server.run_ci_gate", return_value=green
        ), patch(
            "beadloom.services.mcp_server.run_bd",
            side_effect=BdUnavailableError("no bd"),
        ):
            result = handle_complete_bead(project, bead="bd-1", run_tests=False)

        assert result["status"] == "ERROR"

    def test_run_tests_true_invokes_suite_seam(self, project: Path) -> None:
        """With run_tests=True the suite seam is actually called; a green suite
        + green gate passes through to a close."""
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        green = GateResult(steps=[GateStep("lint", passed=True)])
        with patch(
            "beadloom.services.mcp_server.run_ci_gate", return_value=green
        ), patch(
            "beadloom.services.mcp_server._run_test_suite",
            return_value=(True, "10 passed"),
        ) as suite, patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, "next: bd-2", "")
            result = handle_complete_bead(project, bead="bd-1", run_tests=True)

        assert suite.called
        assert result["status"] == "PASS"

    def test_findings_shape_is_agent_actionable(self, project: Path) -> None:
        """A failing test-suite finding carries the shared agent-actionable
        shape (kind/rule/severity/why/remediation)."""
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        green = GateResult(steps=[GateStep("lint", passed=True)])
        with patch(
            "beadloom.services.mcp_server.run_ci_gate", return_value=green
        ), patch(
            "beadloom.services.mcp_server._run_test_suite",
            return_value=(False, "1 failed"),
        ), patch("beadloom.services.mcp_server.run_bd"):
            result = handle_complete_bead(project, bead="bd-1", run_tests=True)

        finding = next(f for f in result["findings"] if f.get("kind") == "tests")
        for key in ("kind", "rule", "severity", "why", "remediation"):
            assert key in finding
        assert "1 failed" in finding["why"]


class TestRunTestSuite:
    def test_passing_suite(self, project: Path) -> None:
        import subprocess as _sp

        from beadloom.services.mcp_server import _run_test_suite

        completed = _sp.CompletedProcess(
            args=[], returncode=0, stdout="42 passed in 1s\n", stderr=""
        )
        with patch("subprocess.run", return_value=completed):
            passed, summary = _run_test_suite(project)
        assert passed is True
        assert "passed" in summary

    def test_failing_suite(self, project: Path) -> None:
        import subprocess as _sp

        from beadloom.services.mcp_server import _run_test_suite

        completed = _sp.CompletedProcess(
            args=[], returncode=1, stdout="1 failed, 3 passed\n", stderr=""
        )
        with patch("subprocess.run", return_value=completed):
            passed, summary = _run_test_suite(project)
        assert passed is False
        assert "failed" in summary

    def test_runner_missing_is_graceful(self, project: Path) -> None:
        from beadloom.services.mcp_server import _run_test_suite

        with patch("subprocess.run", side_effect=FileNotFoundError("uv")):
            passed, summary = _run_test_suite(project)
        assert passed is False
        assert "not available" in summary

    def test_empty_stdout_summary(self, project: Path) -> None:
        import subprocess as _sp

        from beadloom.services.mcp_server import _run_test_suite

        completed = _sp.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=completed):
            passed, summary = _run_test_suite(project)
        assert passed is True
        assert summary == ""


# ---------------------------------------------------------------------------
# Hardening: checkpoint error/edge paths
# ---------------------------------------------------------------------------


class TestCheckpointHardening:
    def test_comment_add_failure_returns_error(self, project: Path) -> None:
        """A failed `bd comments add` surfaces a structured ERROR and does NOT
        touch ACTIVE.md."""
        import json

        from beadloom.services.mcp_server import handle_checkpoint

        feat = project / ".claude" / "development" / "docs" / "features" / "EPIC-1"
        feat.mkdir(parents=True)
        active = feat / "ACTIVE.md"
        active.write_text("# ACTIVE\n", encoding="utf-8")
        before = active.read_text(encoding="utf-8")

        show = json.dumps([{"id": "bd-1", "design": "epic: EPIC-1"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [
                BdResult(0, show, ""),  # bd show
                BdResult(1, "", "comment failed"),  # comments add
            ]
            result = handle_checkpoint(project, bead="bd-1", text="x")

        assert result["status"] == "ERROR"
        assert "comments add" in result["error"]
        assert active.read_text(encoding="utf-8") == before

    def test_epic_resolved_but_active_missing(self, project: Path) -> None:
        """The bead names an epic but that epic has NO ACTIVE.md on disk: the
        note append is skipped cleanly (active_updated False), comment still OK."""
        import json

        from beadloom.services.mcp_server import handle_checkpoint

        show = json.dumps([{"id": "bd-1", "design": "epic: NO-ACTIVE-EPIC"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [BdResult(0, show, ""), BdResult(0, "", "")]
            result = handle_checkpoint(project, bead="bd-1", text="note")

        assert result["status"] == "OK"
        assert result["comment_added"] is True
        assert result["active_updated"] is False

    def test_active_note_uses_feature_token(self, project: Path) -> None:
        """The ACTIVE note is appended when the bead names a `feature:` (not just
        `epic:`) token."""
        import json

        from beadloom.services.mcp_server import handle_checkpoint

        feat = project / ".claude" / "development" / "docs" / "features" / "FEATX"
        feat.mkdir(parents=True)
        active = feat / "ACTIVE.md"
        active.write_text("# ACTIVE\n", encoding="utf-8")

        show = json.dumps([{"id": "bd-1", "design": "feature: FEATX"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [BdResult(0, show, ""), BdResult(0, "", "")]
            result = handle_checkpoint(project, bead="bd-1", text="progress note")

        assert result["active_updated"] is True
        assert "progress note" in active.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Hardening: dispatch routing for the 4 process-tools + project_root guards
# ---------------------------------------------------------------------------


def _conn(project: Path):  # type: ignore[no-untyped-def]
    from beadloom.infrastructure.db import open_db

    return open_db(project / ".beadloom" / "beadloom.db")


class TestDispatchProcessTools:
    def test_dispatch_routes_task_init(self, project: Path) -> None:
        from beadloom.services.mcp_server import _dispatch_tool

        conn = _conn(project)
        try:
            with patch("beadloom.services.mcp_server.run_bd") as run_bd:
                run_bd.side_effect = _fake_bd_create_factory(["a", "b", "c", "d"])
                result = _dispatch_tool(
                    conn,
                    "task_init",
                    {"type": "feature", "key": "DSP-1"},
                    project_root=project,
                )
            assert result["status"] == "OK"
        finally:
            conn.close()

    def test_dispatch_routes_bead_context(self, project: Path) -> None:
        from beadloom.services.mcp_server import _dispatch_tool

        conn = _conn(project)
        try:
            with patch("beadloom.services.mcp_server.run_bd") as run_bd:
                run_bd.return_value = BdResult(0, _bd_show_json("bd-1"), "")
                result = _dispatch_tool(
                    conn,
                    "bead_context",
                    {"bead": "bd-1"},
                    project_root=project,
                )
            assert result["status"] == "OK"
        finally:
            conn.close()

    def test_dispatch_routes_complete_bead(self, project: Path) -> None:
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import _dispatch_tool

        conn = _conn(project)
        try:
            green = GateResult(steps=[GateStep("lint", passed=True)])
            with patch(
                "beadloom.services.mcp_server.run_ci_gate", return_value=green
            ), patch("beadloom.services.mcp_server.run_bd") as run_bd:
                run_bd.return_value = BdResult(0, "next", "")
                result = _dispatch_tool(
                    conn,
                    "complete_bead",
                    {"bead": "bd-1", "run_tests": False},
                    project_root=project,
                )
            assert result["status"] == "PASS"
        finally:
            conn.close()

    @pytest.mark.parametrize(
        ("name", "args"),
        [
            ("task_init", {"type": "feature", "key": "X"}),
            ("bead_context", {"bead": "bd-1"}),
            ("complete_bead", {"bead": "bd-1"}),
            ("checkpoint", {"bead": "bd-1", "text": "x"}),
        ],
    )
    def test_process_tool_requires_project_root(
        self, project: Path, name: str, args: dict[str, object]
    ) -> None:
        """Every process-tool refuses to run without a project_root."""
        from beadloom.services.mcp_server import _dispatch_tool

        conn = _conn(project)
        try:
            with pytest.raises(ValueError, match="project_root"):
                _dispatch_tool(conn, name, args, project_root=None)
        finally:
            conn.close()

    def test_unknown_tool_raises(self, project: Path) -> None:
        from beadloom.services.mcp_server import _dispatch_tool

        conn = _conn(project)
        try:
            with pytest.raises(ValueError, match="Unknown tool"):
                _dispatch_tool(conn, "nope", {}, project_root=project)
        finally:
            conn.close()
