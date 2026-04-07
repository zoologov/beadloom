"""Tests for `beadloom export` — satellite artifact (BDL-037 BEAD-03).

Covers:
- ``build_export`` pure serialization from a SQLite graph (deterministic).
- ``serialize_export`` byte-stable JSON (sorted keys, sorted node/edge arrays).
- ``resolve_repo_name`` (config.yml > git remote basename > dir name).
- the ``beadloom export`` CLI command (stdout + ``--out FILE``).

Determinism is asserted with an *injected* ``exported_at`` and ``commit_sha`` —
never wall-clock (per bead constraint).
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.graph.federation import (
    build_export,
    current_commit_sha,
    resolve_repo_name,
    serialize_export,
)
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_FIXED_TIME = "2026-06-01T00:00:00+00:00"
_FIXED_SHA = "0123456789abcdef0123456789abcdef01234567"


def _make_db(tmp_path: Path) -> Path:
    """Create a populated beadloom DB and return the project root."""
    project = tmp_path / "proj"
    beadloom_dir = project / ".beadloom"
    beadloom_dir.mkdir(parents=True)

    db_path = beadloom_dir / "beadloom.db"
    conn = open_db(db_path)
    create_schema(conn)

    # Inserted out of sorted order to prove the export sorts deterministically.
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, lifecycle) "
        "VALUES (?, ?, ?, ?, ?)",
        ("user-service", "service", "User management", "src/users.py", "active"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, lifecycle) "
        "VALUES (?, ?, ?, ?, ?)",
        ("auth-login", "feature", "User authentication", None, "planned"),
    )
    # Plain edge.
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, lifecycle) VALUES (?, ?, ?, ?)",
        ("auth-login", "user-service", "uses", "active"),
    )
    # Edge carrying AMQP contract metadata in extra.
    contract = {
        "contract": {
            "protocol": "amqp",
            "source_file": "src/broker.py",
            "direction": "produces",
            "message_type": "PlanCreated",
        }
    }
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra, lifecycle) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            "user-service",
            "auth-login",
            "depends_on",
            json.dumps(contract),
            "deprecated",
        ),
    )
    conn.commit()
    conn.close()
    return project


class TestBuildExport:
    def test_envelope_fields(self, tmp_path: Path) -> None:
        project = _make_db(tmp_path)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        export = build_export(
            conn,
            repo="core-monolith",
            commit_sha=_FIXED_SHA,
            exported_at=_FIXED_TIME,
            generator="beadloom 1.9.0",
        )
        conn.close()
        assert export["schema_version"] == 1
        assert export["repo"] == "core-monolith"
        assert export["commit_sha"] == _FIXED_SHA
        assert export["exported_at"] == _FIXED_TIME
        assert export["generator"] == "beadloom 1.9.0"

    def test_nodes_sorted_with_fields(self, tmp_path: Path) -> None:
        project = _make_db(tmp_path)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        export = build_export(
            conn,
            repo="r",
            commit_sha=_FIXED_SHA,
            exported_at=_FIXED_TIME,
            generator="g",
        )
        conn.close()
        nodes = export["nodes"]
        assert [n["ref_id"] for n in nodes] == ["auth-login", "user-service"]
        first = nodes[0]
        assert first["kind"] == "feature"
        assert first["summary"] == "User authentication"
        assert first["lifecycle"] == "planned"
        assert first["source"] is None

    def test_edges_carry_lifecycle_and_contract(self, tmp_path: Path) -> None:
        project = _make_db(tmp_path)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        export = build_export(
            conn,
            repo="r",
            commit_sha=_FIXED_SHA,
            exported_at=_FIXED_TIME,
            generator="g",
        )
        conn.close()
        edges = export["edges"]
        # Sorted by (src, dst, kind).
        assert [(e["src"], e["dst"], e["kind"]) for e in edges] == [
            ("auth-login", "user-service", "uses"),
            ("user-service", "auth-login", "depends_on"),
        ]
        plain, with_contract = edges
        assert plain["lifecycle"] == "active"
        assert "contract" not in plain
        assert with_contract["lifecycle"] == "deprecated"
        assert with_contract["contract"] == {
            "protocol": "amqp",
            "source_file": "src/broker.py",
            "direction": "produces",
            "message_type": "PlanCreated",
        }

    def test_exchange_and_routing_survive_export(self, tmp_path: Path) -> None:
        """BEAD-02 (G4): exchange/routing_key ride inside the edge contract payload.

        ``build_export`` passes the whole ``extra.contract`` blob through, so the
        enriched AMQP fields reach the artifact unchanged (the hub keys on them).
        """
        project = tmp_path / "exch"
        (project / ".beadloom").mkdir(parents=True)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, lifecycle) "
            "VALUES ('svc', 'service', 'S', 'active')"
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, lifecycle) "
            "VALUES ('q', 'feature', 'Q', 'active')"
        )
        contract = {
            "contract": {
                "protocol": "amqp",
                "message_type": "PlanCreated",
                "direction": "produces",
                "exchange": "plans",
                "routing_key": "upload",
            }
        }
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra, lifecycle) "
            "VALUES ('svc', 'q', 'produces', ?, 'active')",
            (json.dumps(contract),),
        )
        conn.commit()
        export = build_export(
            conn,
            repo="r",
            commit_sha=_FIXED_SHA,
            exported_at=_FIXED_TIME,
            generator="g",
        )
        conn.close()
        edge = next(e for e in export["edges"] if e["kind"] == "produces")
        assert edge["contract"]["exchange"] == "plans"
        assert edge["contract"]["routing_key"] == "upload"


class TestExportForeignEdges:
    """Cross-repo @repo: edges survive into the export artifact (#100)."""

    def _make_db_with_foreign(self, tmp_path: Path) -> Path:
        project = tmp_path / "proj"
        (project / ".beadloom").mkdir(parents=True)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, lifecycle) "
            "VALUES ('plans', 'feature', 'Plans', 'active')"
        )
        conn.execute(
            "INSERT INTO foreign_edges "
            "(src_ref_id, dst_ref_id, kind, extra, lifecycle) "
            "VALUES ('plans', '@integration-service:queue', 'depends_on', '{}', 'planned')"
        )
        conn.commit()
        conn.close()
        return project

    def test_foreign_edge_present_in_export(self, tmp_path: Path) -> None:
        project = self._make_db_with_foreign(tmp_path)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        export = build_export(
            conn,
            repo="core-monolith",
            commit_sha=_FIXED_SHA,
            exported_at=_FIXED_TIME,
            generator="g",
        )
        conn.close()
        edges = export["edges"]
        foreign = [e for e in edges if e["dst"] == "@integration-service:queue"]
        assert len(foreign) == 1
        assert foreign[0]["src"] == "plans"
        assert foreign[0]["kind"] == "depends_on"
        assert foreign[0]["lifecycle"] == "planned"

    def test_foreign_edge_contract_surfaced(self, tmp_path: Path) -> None:
        project = tmp_path / "proj2"
        (project / ".beadloom").mkdir(parents=True)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, lifecycle) "
            "VALUES ('producer', 'service', 'P', 'active')"
        )
        contract = {
            "contract": {"protocol": "amqp", "message_type": "m1", "direction": "produces"}
        }
        conn.execute(
            "INSERT INTO foreign_edges "
            "(src_ref_id, dst_ref_id, kind, extra, lifecycle) "
            "VALUES ('producer', '@other:q', 'produces', ?, 'active')",
            (json.dumps(contract),),
        )
        conn.commit()
        conn.close()
        conn = open_db(project / ".beadloom" / "beadloom.db")
        export = build_export(
            conn, repo="r", commit_sha=_FIXED_SHA, exported_at=_FIXED_TIME, generator="g"
        )
        conn.close()
        foreign = [e for e in export["edges"] if e["dst"] == "@other:q"]
        assert len(foreign) == 1
        assert foreign[0]["contract"]["message_type"] == "m1"


class TestSerializeExport:
    def test_deterministic_byte_identical(self, tmp_path: Path) -> None:
        project = _make_db(tmp_path)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        kwargs = {
            "repo": "r",
            "commit_sha": _FIXED_SHA,
            "exported_at": _FIXED_TIME,
            "generator": "g",
        }
        out_a = serialize_export(build_export(conn, **kwargs))
        out_b = serialize_export(build_export(conn, **kwargs))
        conn.close()
        assert out_a == out_b
        # Sorted keys → envelope keys appear alphabetically.
        parsed = json.loads(out_a)
        assert list(parsed.keys()) == sorted(parsed.keys())


class TestResolveRepoName:
    def test_config_key_wins(self, tmp_path: Path) -> None:
        project = tmp_path / "myproj"
        (project / ".beadloom").mkdir(parents=True)
        (project / ".beadloom" / "config.yml").write_text(
            "repo: chosen-name\n", encoding="utf-8"
        )
        assert resolve_repo_name(project) == "chosen-name"

    def test_falls_back_to_dir_name(self, tmp_path: Path) -> None:
        project = tmp_path / "fallback-dir"
        (project / ".beadloom").mkdir(parents=True)
        # No config repo key, no git remote → directory basename.
        assert resolve_repo_name(project) == "fallback-dir"


class TestCurrentCommitSha:
    """``commit_sha`` reflects the target project's repo, not an enclosing one (#103)."""

    def _git(self, cwd: Path, *args: str) -> None:
        subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    def _init_repo(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._git(root, "init")
        self._git(root, "config", "user.email", "t@example.com")
        self._git(root, "config", "user.name", "t")
        (root / "f.txt").write_text("x", encoding="utf-8")
        self._git(root, "add", ".")
        self._git(root, "commit", "-m", "init")

    def test_returns_head_for_repo_root(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        self._init_repo(repo)
        sha = current_commit_sha(repo)
        assert sha is not None
        assert len(sha) == 40

    def test_returns_none_for_nested_non_repo_dir(self, tmp_path: Path) -> None:
        """A nested dir inside a git tree must NOT leak the host repo's HEAD."""
        repo = tmp_path / "host"
        self._init_repo(repo)
        nested = repo / "sub" / "project"
        nested.mkdir(parents=True)
        assert current_commit_sha(nested) is None

    def test_returns_none_outside_any_repo(self, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        plain.mkdir()
        assert current_commit_sha(plain) is None


class TestExportCli:
    def test_stdout_export(self, tmp_path: Path) -> None:
        project = _make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["export", "--project", str(project)])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["schema_version"] == 1
        assert len(parsed["nodes"]) == 2
        assert len(parsed["edges"]) == 2

    def test_out_file(self, tmp_path: Path) -> None:
        project = _make_db(tmp_path)
        out = tmp_path / "export.json"
        runner = CliRunner()
        result = runner.invoke(
            main, ["export", "--project", str(project), "--out", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        parsed = json.loads(out.read_text(encoding="utf-8"))
        assert parsed["repo"] == "proj"
        assert parsed["nodes"][0]["ref_id"] == "auth-login"

    def test_no_db_errors(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["export", "--project", str(project)])
        assert result.exit_code == 1
        assert "database not found" in result.output.lower()
