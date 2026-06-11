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
# BDL-051 BEAD-10: ACTIVE.md bead-status TABLE maintenance
# ---------------------------------------------------------------------------


_ACTIVE_TABLE = """# ACTIVE: EPIC-1

## Bead status

| Bead | Role | Status |
|------|------|--------|
| beadloom-mukc.1 | dev — first | in progress |
| beadloom-mukc.10 | dev — tenth | in progress |
| beadloom-mukc.2 | test — second | ✓ done |

## Progress
"""


class TestSetActiveTableStatus:
    def test_flips_matching_row_status(self, tmp_path: Path) -> None:
        from beadloom.services.mcp_server import _set_active_table_status

        active = tmp_path / "ACTIVE.md"
        active.write_text(_ACTIVE_TABLE, encoding="utf-8")
        ok = _set_active_table_status(active, "beadloom-mukc.10", "✓ done")
        assert ok is True
        text = active.read_text(encoding="utf-8")
        assert "| beadloom-mukc.10 | dev — tenth | ✓ done |" in text
        # Other rows are preserved untouched.
        assert "| beadloom-mukc.1 | dev — first | in progress |" in text
        assert "| beadloom-mukc.2 | test — second | ✓ done |" in text

    def test_bead_id_is_token_matched_not_prefix(self, tmp_path: Path) -> None:
        """`.1` must not match `.10` — the row for `.1` stays untouched when we
        flip `.10`, and flipping `.1` does not touch `.10`."""
        from beadloom.services.mcp_server import _set_active_table_status

        active = tmp_path / "ACTIVE.md"
        active.write_text(_ACTIVE_TABLE, encoding="utf-8")
        ok = _set_active_table_status(active, "beadloom-mukc.1", "✓ done")
        assert ok is True
        text = active.read_text(encoding="utf-8")
        assert "| beadloom-mukc.1 | dev — first | ✓ done |" in text
        # `.10` is left in progress (NOT collaterally flipped).
        assert "| beadloom-mukc.10 | dev — tenth | in progress |" in text

    def test_status_cell_with_extra_prose_replaced_cleanly(
        self, tmp_path: Path
    ) -> None:
        from beadloom.services.mcp_server import _set_active_table_status

        active = tmp_path / "ACTIVE.md"
        active.write_text(
            "| Bead | Role | Status |\n"
            "|------|------|--------|\n"
            "| bd-x | dev | in progress — blocked on review feedback |\n",
            encoding="utf-8",
        )
        ok = _set_active_table_status(active, "bd-x", "✓ done")
        assert ok is True
        assert "| bd-x | dev | ✓ done |" in active.read_text(encoding="utf-8")

    def test_missing_file_returns_false(self, tmp_path: Path) -> None:
        from beadloom.services.mcp_server import _set_active_table_status

        ok = _set_active_table_status(tmp_path / "nope.md", "bd-x", "✓ done")
        assert ok is False

    def test_no_table_returns_false_and_unchanged(self, tmp_path: Path) -> None:
        from beadloom.services.mcp_server import _set_active_table_status

        active = tmp_path / "ACTIVE.md"
        body = "# ACTIVE\n\nNo table here, just prose.\n"
        active.write_text(body, encoding="utf-8")
        ok = _set_active_table_status(active, "bd-x", "✓ done")
        assert ok is False
        assert active.read_text(encoding="utf-8") == body

    def test_no_matching_row_returns_false_and_unchanged(
        self, tmp_path: Path
    ) -> None:
        from beadloom.services.mcp_server import _set_active_table_status

        active = tmp_path / "ACTIVE.md"
        active.write_text(_ACTIVE_TABLE, encoding="utf-8")
        before = active.read_text(encoding="utf-8")
        ok = _set_active_table_status(active, "beadloom-mukc.999", "✓ done")
        assert ok is False
        assert active.read_text(encoding="utf-8") == before


def _active_with_table(project: Path, epic: str, bead: str) -> Path:
    feat = project / ".claude" / "development" / "docs" / "features" / epic
    feat.mkdir(parents=True, exist_ok=True)
    active = feat / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n"
        "|------|------|--------|\n"
        f"| {bead} | dev | in progress |\n"
        "| other-bead | test | in progress |\n",
        encoding="utf-8",
    )
    return active


class TestCompleteBeadActiveTable:
    def test_pass_flips_row_to_done(self, project: Path) -> None:
        import json

        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        active = _active_with_table(project, "EPIC-1", "bd-1")
        green = GateResult(steps=[GateStep("lint", passed=True, summary="clean")])
        show = json.dumps([{"id": "bd-1", "design": "epic: EPIC-1"}])
        with patch(
            "beadloom.services.mcp_server.run_ci_gate", return_value=green
        ), patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [
                BdResult(0, show, ""),  # bd show (locate ACTIVE)
                BdResult(0, "next: bd-2\n", ""),  # bd close
            ]
            result = handle_complete_bead(project, bead="bd-1", run_tests=False)

        assert result["status"] == "PASS"
        text = active.read_text(encoding="utf-8")
        assert "| bd-1 | dev | ✓ done |" in text
        # The sibling row is untouched.
        assert "| other-bead | test | in progress |" in text

    def test_fail_leaves_table_alone(self, project: Path) -> None:
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        active = _active_with_table(project, "EPIC-1", "bd-1")
        before = active.read_text(encoding="utf-8")
        red = GateResult(
            steps=[GateStep("lint", passed=False, findings=[{"why": "x"}], summary="1")]
        )
        with patch(
            "beadloom.services.mcp_server.run_ci_gate", return_value=red
        ), patch("beadloom.services.mcp_server.run_bd"):
            result = handle_complete_bead(project, bead="bd-1", run_tests=False)

        assert result["status"] == "FAIL"
        assert active.read_text(encoding="utf-8") == before

    def test_pass_with_no_active_table_still_passes(self, project: Path) -> None:
        """A missing ACTIVE/table must NOT fail the tool nor the close."""
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        green = GateResult(steps=[GateStep("lint", passed=True)])
        with patch(
            "beadloom.services.mcp_server.run_ci_gate", return_value=green
        ), patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [
                BdResult(0, "[]", ""),  # bd show — no epic
                BdResult(0, "next", ""),  # bd close
            ]
            result = handle_complete_bead(project, bead="bd-1", run_tests=False)

        assert result["status"] == "PASS"


class TestCheckpointActiveTable:
    def test_checkpoint_sets_row_in_progress(self, project: Path) -> None:
        import json

        from beadloom.services.mcp_server import handle_checkpoint

        active = _active_with_table(project, "EPIC-1", "bd-1")
        # Pre-set the row to something else so we can see it flip.
        active.write_text(
            active.read_text(encoding="utf-8").replace(
                "| bd-1 | dev | in progress |", "| bd-1 | dev | todo |"
            ),
            encoding="utf-8",
        )
        show = json.dumps([{"id": "bd-1", "design": "epic: EPIC-1"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [BdResult(0, show, ""), BdResult(0, "", "")]
            result = handle_checkpoint(project, bead="bd-1", text="working")

        assert result["status"] == "OK"
        assert "| bd-1 | dev | in progress |" in active.read_text(encoding="utf-8")

    def test_checkpoint_explicit_status(self, project: Path) -> None:
        import json

        from beadloom.services.mcp_server import handle_checkpoint

        active = _active_with_table(project, "EPIC-1", "bd-1")
        show = json.dumps([{"id": "bd-1", "design": "epic: EPIC-1"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [BdResult(0, show, ""), BdResult(0, "", "")]
            result = handle_checkpoint(
                project, bead="bd-1", text="blocked", status="blocked"
            )

        assert result["status"] == "OK"
        assert "| bd-1 | dev | blocked |" in active.read_text(encoding="utf-8")

    def test_checkpoint_no_table_is_best_effort(self, project: Path) -> None:
        """The note-append path still works; table update silently no-ops."""
        import json

        from beadloom.services.mcp_server import handle_checkpoint

        feat = project / ".claude" / "development" / "docs" / "features" / "EPIC-1"
        feat.mkdir(parents=True)
        (feat / "ACTIVE.md").write_text("# ACTIVE\n\n## Progress\n", encoding="utf-8")
        show = json.dumps([{"id": "bd-1", "design": "epic: EPIC-1"}])
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.side_effect = [BdResult(0, show, ""), BdResult(0, "", "")]
            result = handle_checkpoint(project, bead="bd-1", text="note")

        assert result["status"] == "OK"
        assert result["comment_added"] is True


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


# ---------------------------------------------------------------------------
# S4 BEAD-11: ACTIVE-table maintenance — real-file integration + safety
#
# These verify behaviour the dev's unit tests don't already cover: a realistic
# full ACTIVE.md (heading + Bead-status table with prose-bearing Role/Status
# cells + a Progress Log that also mentions bead ids in PROSE), exact byte
# preservation of everything outside the one flipped row, idempotency, and the
# pipe-in-status corruption edge (current behaviour pinned; see BUG comment).
# ---------------------------------------------------------------------------


# A realistic ACTIVE.md like the ones this repo uses for BDL-0xx epics: a real
# `| Bead | Role | Status |` table mixing ✓ done / in progress / blocked, prose
# inside Role/Status cells, plus a Progress Log that name-drops bead ids in
# prose (which must NOT be mistaken for table rows).
_REAL_ACTIVE = """# ACTIVE: BDL-051 — Beadloom governs itself

> **Phase:** Development

---

## Bead status

| Bead | Role | Status |
|------|------|--------|
| beadloom-mukc.1 | dev — graph discipline | ✓ done |
| beadloom-mukc.10 | dev — ACTIVE table | in progress |
| beadloom-mukc.11 | test — ACTIVE table | blocked on .10 |
| beadloom-mukc.2 | review — ai_agents | in progress (needs rebase) |

## Progress Log

- 2026-06-11 — beadloom-mukc.10 landed the table helper; beadloom-mukc.11 next.
- 2026-06-11 — note: beadloom-mukc.1 closed earlier today.

## Notes

Nothing | with a stray pipe in prose should ever be treated as a row.
"""


def _real_active(tmp_path: Path) -> Path:
    active = tmp_path / "ACTIVE.md"
    active.write_text(_REAL_ACTIVE, encoding="utf-8")
    return active


class TestActiveTableRealFileIntegration:
    """A realistic full ACTIVE.md: only the one target row changes; the rest of
    the file (headings, sibling rows, Progress Log, Notes) stays byte-for-byte."""

    def test_flips_only_target_row_rest_byte_identical(self, tmp_path: Path) -> None:
        from beadloom.services.mcp_server import _set_active_table_status

        active = _real_active(tmp_path)
        ok = _set_active_table_status(active, "beadloom-mukc.11", "✓ done")

        assert ok is True
        after = active.read_text(encoding="utf-8")
        # Target row's status cell flipped (prose status replaced cleanly).
        assert "| beadloom-mukc.11 | test — ACTIVE table | ✓ done |" in after
        # Reconstruct the expected file: only that one line differs.
        expected = _REAL_ACTIVE.replace(
            "| beadloom-mukc.11 | test — ACTIVE table | blocked on .10 |",
            "| beadloom-mukc.11 | test — ACTIVE table | ✓ done |",
        )
        assert after == expected

    def test_sibling_rows_and_prose_untouched(self, tmp_path: Path) -> None:
        from beadloom.services.mcp_server import _set_active_table_status

        active = _real_active(tmp_path)
        _set_active_table_status(active, "beadloom-mukc.10", "✓ done")
        after = active.read_text(encoding="utf-8")

        # Sibling table rows: byte-unchanged.
        assert "| beadloom-mukc.1 | dev — graph discipline | ✓ done |" in after
        assert "| beadloom-mukc.11 | test — ACTIVE table | blocked on .10 |" in after
        assert "| beadloom-mukc.2 | review — ai_agents | in progress (needs rebase) |" in after
        # Headings + Progress Log + Notes: untouched.
        assert "# ACTIVE: BDL-051 — Beadloom governs itself" in after
        assert "## Progress Log" in after
        assert "## Notes" in after

    def test_bead_id_in_progress_log_prose_not_mistaken_for_row(
        self, tmp_path: Path
    ) -> None:
        """`beadloom-mukc.1` is name-dropped in the Progress Log; flipping its
        table row must change ONLY the table row, leaving the prose lines and the
        stray-pipe Notes line exactly as-is."""
        from beadloom.services.mcp_server import _set_active_table_status

        active = _real_active(tmp_path)
        ok = _set_active_table_status(active, "beadloom-mukc.1", "✓ done")

        assert ok is True
        after = active.read_text(encoding="utf-8")
        # Prose mentions are preserved verbatim.
        assert (
            "- 2026-06-11 — beadloom-mukc.10 landed the table helper;"
            " beadloom-mukc.11 next." in after
        )
        assert "- 2026-06-11 — note: beadloom-mukc.1 closed earlier today." in after
        # The stray-pipe prose line in Notes is not turned into a row.
        assert (
            "Nothing | with a stray pipe in prose should ever be treated as a row."
            in after
        )
        # Only the .1 *table* row reflects the flip (it was already ✓ done, so the
        # whole file is unchanged except for canonicalised spacing — assert equal).
        assert after == _REAL_ACTIVE

    @pytest.mark.parametrize(
        ("target", "must_stay"),
        [
            ("beadloom-mukc.1", ("beadloom-mukc.10", "beadloom-mukc.11")),
            ("beadloom-mukc.10", ("beadloom-mukc.1", "beadloom-mukc.11")),
            ("beadloom-mukc.11", ("beadloom-mukc.1", "beadloom-mukc.10")),
        ],
    )
    def test_similar_ids_only_exact_one_flips(
        self, tmp_path: Path, target: str, must_stay: tuple[str, ...]
    ) -> None:
        """`.1` / `.10` / `.11` are distinct whole tokens — flipping one never
        collaterally changes another's status cell."""
        from beadloom.services.mcp_server import _set_active_table_status

        active = _real_active(tmp_path)
        # Capture each sibling's exact row line before the flip.
        before_lines = {
            other: next(
                ln
                for ln in _REAL_ACTIVE.splitlines()
                if ln.strip().startswith(f"| {other} ")
            )
            for other in must_stay
        }
        ok = _set_active_table_status(active, target, "✓ DONE-MARKER")

        assert ok is True
        after = active.read_text(encoding="utf-8")
        assert f"| {target} " in after and "✓ DONE-MARKER" in after
        for other, line in before_lines.items():
            assert line in after, f"{other} row must stay untouched"
            assert "✓ DONE-MARKER" not in line

    def test_idempotent_double_set_is_stable(self, tmp_path: Path) -> None:
        """Setting the same status twice → second write is a stable no-change
        (no duplicated cells / corruption)."""
        from beadloom.services.mcp_server import _set_active_table_status

        active = _real_active(tmp_path)
        ok1 = _set_active_table_status(active, "beadloom-mukc.10", "✓ done")
        first = active.read_text(encoding="utf-8")
        ok2 = _set_active_table_status(active, "beadloom-mukc.10", "✓ done")
        second = active.read_text(encoding="utf-8")

        assert ok1 is True and ok2 is True
        assert first == second
        # Exactly one occurrence of the flipped row — no duplication.
        assert second.count("| beadloom-mukc.10 | dev — ACTIVE table | ✓ done |") == 1

    @pytest.mark.parametrize(
        "status",
        ["✓ done", "in progress", "blocked", "⏸ paused", "done — ✓ (90% cov)"],
    )
    def test_status_with_unicode_markdown_round_trips(
        self, tmp_path: Path, status: str
    ) -> None:
        """Unicode/markdown status values land verbatim in the status cell and
        survive a re-read (UTF-8 round-trip), with a 3-cell row preserved."""
        from beadloom.services.mcp_server import _set_active_table_status

        active = _real_active(tmp_path)
        ok = _set_active_table_status(active, "beadloom-mukc.11", status)

        assert ok is True
        after = active.read_text(encoding="utf-8")
        assert f"| beadloom-mukc.11 | test — ACTIVE table | {status} |" in after
        # The row still has exactly three columns (two interior separators).
        row = next(
            ln for ln in after.splitlines() if "beadloom-mukc.11" in ln and "|" in ln
        )
        assert row.strip().count("|") == 4  # | a | b | c | → 4 pipes

    def test_no_final_newline_file_does_not_grow_a_newline(
        self, tmp_path: Path
    ) -> None:
        """A row on the last line without a trailing newline keeps no trailing
        newline after the flip (EOL preserved)."""
        from beadloom.services.mcp_server import _set_active_table_status

        active = tmp_path / "ACTIVE.md"
        active.write_text(
            "| Bead | Role | Status |\n"
            "|------|------|--------|\n"
            "| bd-x | dev | todo |",  # no trailing newline
            encoding="utf-8",
        )
        ok = _set_active_table_status(active, "bd-x", "✓ done")

        assert ok is True
        after = active.read_text(encoding="utf-8")
        assert after.endswith("| bd-x | dev | ✓ done |")
        assert not after.endswith("\n")


    def test_write_failure_is_swallowed_returns_false(self, tmp_path: Path) -> None:
        """If the write-back raises OSError (e.g. read-only FS), the helper does
        not propagate — it returns False rather than crashing the tool."""
        import pathlib

        from beadloom.services.mcp_server import _set_active_table_status

        active = _real_active(tmp_path)
        orig = active.read_text(encoding="utf-8")
        with patch.object(
            pathlib.Path, "write_text", side_effect=OSError("read-only")
        ):
            ok = _set_active_table_status(active, "beadloom-mukc.10", "✓ done")

        assert ok is False
        # File content is left intact (the failed write changed nothing on disk).
        assert active.read_text(encoding="utf-8") == orig


class TestActiveTableStatusWithPipe:
    """A status arg containing a `|` is a safety edge: the helper neither escapes
    so the helper replaces any pipe in the status with "/" — the row stays a clean
    3 cells and never gains an extra column. See BUG comment on the bead (fixed)."""

    def test_pipe_in_status_is_escaped_not_injected(
        self, tmp_path: Path
    ) -> None:
        from beadloom.services.mcp_server import (
            _set_active_table_status,
            _split_table_row,
        )

        active = tmp_path / "ACTIVE.md"
        active.write_text(
            "| Bead | Role | Status |\n"
            "|------|------|--------|\n"
            "| bd-x | dev | todo |\n",
            encoding="utf-8",
        )
        ok = _set_active_table_status(active, "bd-x", "done | EXTRA")

        assert ok is True
        after = active.read_text(encoding="utf-8")
        row = next(ln for ln in after.splitlines() if ln.startswith("| bd-x"))
        cells = _split_table_row(row)
        # FIXED: the pipe is replaced with "/" → the row stays 3 cells (no extra column).
        assert cells is not None and len(cells) == 3
        assert cells[0] == "bd-x" and cells[1] == "dev"
        assert cells[2] == "done / EXTRA"

    def test_newline_in_status_does_not_split_the_row(self, tmp_path: Path) -> None:
        # A newline/CR/tab in a (user-supplied) status must not split the row
        # across lines — whitespace is collapsed to single spaces.
        from beadloom.services.mcp_server import (
            _set_active_table_status,
            _split_table_row,
        )

        active = tmp_path / "ACTIVE.md"
        active.write_text(
            "| Bead | Role | Status |\n"
            "|------|------|--------|\n"
            "| bd-x | dev | todo |\n"
            "| bd-y | test | todo |\n",
            encoding="utf-8",
        )
        ok = _set_active_table_status(active, "bd-x", "in\nprogress\r\nnow\t!")

        assert ok is True
        after = active.read_text(encoding="utf-8")
        # Still exactly 4 lines (header + sep + 2 rows) — no row split.
        assert len(after.splitlines()) == 4
        row = next(ln for ln in after.splitlines() if ln.startswith("| bd-x"))
        cells = _split_table_row(row)
        assert cells is not None and len(cells) == 3
        assert cells[2] == "in progress now !"
        # The untouched row is byte-identical.
        assert "| bd-y | test | todo |" in after


class TestCompleteBeadActiveTableEndToEnd:
    """complete_bead end-to-end via the public dispatch path (bd + gate mocked):
    PASS flips the row + closes; FAIL leaves the row + does not close; a missing
    ACTIVE still PASSes (best-effort)."""

    def _epic_active(self, project: Path, bead: str) -> Path:
        feat = project / ".claude" / "development" / "docs" / "features" / "EPIC-1"
        feat.mkdir(parents=True, exist_ok=True)
        active = feat / "ACTIVE.md"
        active.write_text(
            "# ACTIVE: EPIC-1\n\n## Bead status\n\n"
            "| Bead | Role | Status |\n"
            "|------|------|--------|\n"
            f"| {bead} | dev | in progress |\n"
            "| sibling-bead | test | in progress |\n\n"
            "## Progress Log\n\n- kickoff\n",
            encoding="utf-8",
        )
        return active

    def test_pass_flips_row_and_closes(self, project: Path) -> None:
        import json

        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import _dispatch_tool

        active = self._epic_active(project, "bd-1")
        before = active.read_text(encoding="utf-8")
        green = GateResult(steps=[GateStep("lint", passed=True, summary="clean")])
        show = json.dumps([{"id": "bd-1", "design": "epic: EPIC-1"}])
        conn = _conn(project)
        try:
            with patch(
                "beadloom.services.mcp_server.run_ci_gate", return_value=green
            ), patch("beadloom.services.mcp_server.run_bd") as run_bd:
                run_bd.side_effect = [
                    BdResult(0, show, ""),  # bd show — locate ACTIVE
                    BdResult(0, "next: bd-2\n", ""),  # bd close
                ]
                result = _dispatch_tool(
                    conn,
                    "complete_bead",
                    {"bead": "bd-1", "run_tests": False},
                    project_root=project,
                )
                # bd close WAS invoked (PASS implies the close happened).
                close_calls = [
                    c for c in run_bd.call_args_list if c.args[0][0] == "close"
                ]
        finally:
            conn.close()

        assert result["status"] == "PASS"
        assert result["active_updated"] is True
        assert len(close_calls) == 1
        after = active.read_text(encoding="utf-8")
        assert "| bd-1 | dev | ✓ done |" in after
        assert "| sibling-bead | test | in progress |" in after
        # Everything outside the flipped row is byte-identical.
        assert after == before.replace(
            "| bd-1 | dev | in progress |", "| bd-1 | dev | ✓ done |"
        )

    def test_fail_does_not_flip_and_does_not_close(self, project: Path) -> None:
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import _dispatch_tool

        active = self._epic_active(project, "bd-1")
        before = active.read_text(encoding="utf-8")
        red = GateResult(
            steps=[GateStep("lint", passed=False, findings=[{"why": "x"}], summary="1")]
        )
        conn = _conn(project)
        try:
            with patch(
                "beadloom.services.mcp_server.run_ci_gate", return_value=red
            ), patch("beadloom.services.mcp_server.run_bd") as run_bd:
                result = _dispatch_tool(
                    conn,
                    "complete_bead",
                    {"bead": "bd-1", "run_tests": False},
                    project_root=project,
                )
                # bd was never called on a red gate (no show, no close).
                assert run_bd.call_count == 0
        finally:
            conn.close()

        assert result["status"] == "FAIL"
        assert active.read_text(encoding="utf-8") == before

    def test_pass_with_no_active_still_passes_and_closes(self, project: Path) -> None:
        """No epic ACTIVE at all → still PASS + close (active_updated False)."""
        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import _dispatch_tool

        green = GateResult(steps=[GateStep("lint", passed=True)])
        conn = _conn(project)
        try:
            with patch(
                "beadloom.services.mcp_server.run_ci_gate", return_value=green
            ), patch("beadloom.services.mcp_server.run_bd") as run_bd:
                run_bd.side_effect = [
                    BdResult(0, "[]", ""),  # bd show — no epic resolvable
                    BdResult(0, "next", ""),  # bd close
                ]
                result = _dispatch_tool(
                    conn,
                    "complete_bead",
                    {"bead": "bd-1", "run_tests": False},
                    project_root=project,
                )
        finally:
            conn.close()

        assert result["status"] == "PASS"
        assert result["active_updated"] is False
