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
