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
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.graph.federation import (
    build_export,
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
