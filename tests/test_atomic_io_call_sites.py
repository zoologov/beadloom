"""Call-site hardening for the atomic graph-YAML write seam (BDL-060 S1, G6).

``tests/test_atomic_io.py`` proves the helper (``write_yaml_atomic``) in
isolation. This module proves the *safety guarantee survives at the real routed
call-sites* — that an interrupted write through ``beadloom link`` (the
services.yml/graph link-patcher) or ``update_node_in_yaml`` (the graph-loader
save path) leaves the prior on-disk file intact with no stray temp file, that
the routed writers stay byte-identical to the pre-refactor direct
``yaml.dump`` -> ``write_text`` path, and that the boundary edge cases
(non-writable dir / fresh non-existent target / mid-write interruption) behave
honestly (no partial file, a clear error).

These are deliberately end-to-end through the production entry-points rather
than calling the helper directly, so a future regression that bypasses the
atomic seam at a call-site is caught here even if the helper itself is fine.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.graph.loader import update_node_in_yaml
from beadloom.infrastructure.atomic_io import write_yaml_atomic
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator


# --- factory helpers ---------------------------------------------------------


def _make_graph_project(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal project with a single graph YAML; return (project, yml)."""
    project = tmp_path / "proj"
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    yml = graph_dir / "graph.yml"
    yml.write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "F1", "kind": "feature", "summary": "Feature 1"},
                    {"ref_id": "F2", "kind": "feature", "summary": "Feature 2"},
                ],
            }
        ),
        encoding="utf-8",
    )
    return project, yml


def _make_loader_db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    conn = open_db(tmp_path / "loader.db")
    create_schema(conn)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("F1", "feature", "Feature 1", None),
    )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def loader_db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    yield from _make_loader_db(tmp_path)


def _temp_siblings(directory: Path, target_name: str) -> list[str]:
    """Names in *directory* that are not the target file (i.e. stray temps)."""
    return sorted(p.name for p in directory.iterdir() if p.name != target_name)


# --- 1. Atomicity at the routed call-sites -----------------------------------


class TestLinkCommandAtomicity:
    """An interrupted ``beadloom link`` write leaves the prior YAML intact."""

    def test_crash_at_commit_preserves_prior_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — a project whose graph.yml has a known prior content.
        project, yml = _make_graph_project(tmp_path)
        prior_bytes = yml.read_bytes()

        # The commit point is Path.replace inside write_yaml_atomic; fail it
        # so the write is interrupted exactly at the rename.
        def _boom(*_a: object, **_k: object) -> None:
            raise OSError("simulated crash at commit")

        monkeypatch.setattr(Path, "replace", _boom)

        # Act — drive the real CLI link-patcher (it routes through the seam).
        result = CliRunner().invoke(
            main,
            ["link", "F1", "https://github.com/org/repo/issues/42",
             "--project", str(project)],
        )

        # Assert — command failed, prior file is byte-for-byte intact, and no
        # stray temp file remains alongside it.
        assert result.exit_code != 0
        assert yml.read_bytes() == prior_bytes
        assert _temp_siblings(yml.parent, "graph.yml") == []

    def test_crash_at_commit_preserves_prior_on_remove(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — first add a link (clean), capturing the resulting bytes.
        project, yml = _make_graph_project(tmp_path)
        url = "https://github.com/org/repo/issues/42"
        runner = CliRunner()
        add = runner.invoke(main, ["link", "F1", url, "--project", str(project)])
        assert add.exit_code == 0, add.output
        prior_bytes = yml.read_bytes()

        # Now interrupt the *remove* patcher at the commit point.
        def _boom(*_a: object, **_k: object) -> None:
            raise OSError("simulated crash at commit")

        monkeypatch.setattr(Path, "replace", _boom)

        # Act
        result = runner.invoke(
            main, ["link", "F1", "--remove", url, "--project", str(project)]
        )

        # Assert — the with-link state survived the interrupted removal.
        assert result.exit_code != 0
        assert yml.read_bytes() == prior_bytes
        assert _temp_siblings(yml.parent, "graph.yml") == []


class TestLoaderSavePathAtomicity:
    """An interrupted ``update_node_in_yaml`` write leaves the prior YAML intact."""

    def test_crash_at_commit_preserves_prior_yaml(
        self, tmp_path: Path, loader_db: sqlite3.Connection,
        monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        _project, yml = _make_graph_project(tmp_path)
        graph_dir = yml.parent
        prior_bytes = yml.read_bytes()

        def _boom(*_a: object, **_k: object) -> None:
            raise OSError("simulated crash at commit")

        monkeypatch.setattr(Path, "replace", _boom)

        # Act / Assert — the loader save path surfaces the error, no partial file.
        with pytest.raises(OSError, match="simulated crash"):
            update_node_in_yaml(
                graph_dir, loader_db, "F1", summary="MUTATED"
            )

        assert yml.read_bytes() == prior_bytes
        assert _temp_siblings(graph_dir, "graph.yml") == []


# --- 2. Byte-parity at the call-sites ----------------------------------------


_REPRESENTATIVE: dict[str, Any] = {
    "nodes": [
        {"ref_id": "F1", "kind": "feature", "summary": "Feature 1"},
        {"ref_id": "F2", "kind": "feature", "summary": "Béta — unicode"},
        {
            "ref_id": "F1",
            "kind": "feature",
            "summary": "Feature 1",
            "links": [{"url": "https://github.com/org/repo/issues/42",
                       "label": "github"}],
        },
    ],
}


class TestLinkCommandByteParity:
    """The link-patcher emits exactly what the pre-refactor direct dump would."""

    def test_add_link_matches_direct_dump(self, tmp_path: Path) -> None:
        # Arrange — replicate the in-memory mutation the patcher performs, then
        # compute the expected bytes via the SAME options the call-site passes
        # (default_flow_style=False, sort_keys=False).
        project, yml = _make_graph_project(tmp_path)
        url = "https://github.com/org/repo/issues/42"

        expected_data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        expected_data["nodes"][0]["links"] = [{"url": url, "label": "github"}]
        expected = yaml.dump(
            expected_data, default_flow_style=False, sort_keys=False
        )

        # Act
        result = CliRunner().invoke(
            main, ["link", "F1", url, "--project", str(project)]
        )

        # Assert — byte-identical to the direct-dump baseline.
        assert result.exit_code == 0, result.output
        assert yml.read_text(encoding="utf-8") == expected

    def test_unicode_payload_round_trips_byte_identical(
        self, tmp_path: Path
    ) -> None:
        # Guard allow_unicode/encoding behavior at the seam for a representative
        # payload through the loader save path.
        _project, yml = _make_graph_project(tmp_path)
        # Seed a unicode summary, then re-dump via the helper with the loader's
        # exact options and compare to the direct baseline.
        data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        data["nodes"][1]["summary"] = "Béta — ünïcode ✓"
        expected = yaml.dump(
            data, default_flow_style=False, allow_unicode=True
        )

        write_yaml_atomic(
            yml, data, default_flow_style=False, allow_unicode=True
        )

        assert yml.read_text(encoding="utf-8") == expected


class TestLoaderSavePathByteParity:
    """update_node_in_yaml writes the same bytes a direct dump would."""

    def test_update_summary_matches_direct_dump(
        self, tmp_path: Path, loader_db: sqlite3.Connection
    ) -> None:
        # Arrange — expected bytes = the prior data with summary mutated,
        # dumped with the call-site's options.
        _project, yml = _make_graph_project(tmp_path)
        graph_dir = yml.parent
        expected_data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        expected_data["nodes"][0]["summary"] = "Updated summary"
        expected = yaml.dump(
            expected_data, default_flow_style=False, allow_unicode=True
        )

        # Act
        found = update_node_in_yaml(
            graph_dir, loader_db, "F1", summary="Updated summary"
        )

        # Assert
        assert found is True
        assert yml.read_text(encoding="utf-8") == expected
        # SQLite was updated in lock-step with the YAML.
        row = loader_db.execute(
            "SELECT summary FROM nodes WHERE ref_id = ?", ("F1",)
        ).fetchone()
        assert row[0] == "Updated summary"


# --- 3. Edge cases at the boundary -------------------------------------------


class TestEdgeCases:
    """Honest behavior for non-writable dir / fresh target / interruption."""

    def test_fresh_nonexistent_target_is_created(self, tmp_path: Path) -> None:
        # A target that does not yet exist is written cleanly with no leftover
        # temp file (the common first-write case for generated YAMLs).
        target = tmp_path / "rules.yml"
        assert not target.exists()

        write_yaml_atomic(
            target, _REPRESENTATIVE, default_flow_style=False, allow_unicode=True
        )

        assert target.exists()
        assert yaml.safe_load(target.read_text(encoding="utf-8")) == _REPRESENTATIVE
        assert _temp_siblings(tmp_path, "rules.yml") == []

    @pytest.mark.skipif(
        sys.platform == "win32", reason="POSIX dir-permission semantics"
    )
    def test_nonwritable_dir_raises_and_leaves_no_partial(
        self, tmp_path: Path
    ) -> None:
        # A read-only target directory must surface a clear OSError with no
        # partial/temp file written into it.
        ro_dir = tmp_path / "readonly"
        ro_dir.mkdir()
        target = ro_dir / "graph.yml"
        ro_dir.chmod(0o500)  # r-x — no write/create
        try:
            with pytest.raises(OSError):
                write_yaml_atomic(
                    target, _REPRESENTATIVE, default_flow_style=False
                )
            # Nothing landed in the directory (no temp, no target).
            assert list(ro_dir.iterdir()) == []
        finally:
            ro_dir.chmod(0o700)  # restore so tmp cleanup can remove it

    def test_concurrent_ish_replace_last_writer_wins_cleanly(
        self, tmp_path: Path
    ) -> None:
        # Two sequential atomic writes to the same target (the closest in-process
        # analogue of a racing replace): the file is always complete + valid and
        # reflects the last writer, with no temp residue.
        target = tmp_path / "graph.yml"
        first = {"nodes": [{"ref_id": "A", "kind": "domain", "summary": "first"}]}
        second = {"nodes": [{"ref_id": "B", "kind": "domain", "summary": "second"}]}

        write_yaml_atomic(target, first, default_flow_style=False, sort_keys=False)
        write_yaml_atomic(target, second, default_flow_style=False, sort_keys=False)

        loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
        assert loaded == second
        assert _temp_siblings(tmp_path, "graph.yml") == []

    def test_interruption_before_commit_leaves_no_temp(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Interrupt during serialization-to-disk (the fsync), before the commit:
        # the prior target survives and no temp file leaks.
        target = tmp_path / "graph.yml"
        prior = "nodes:\n- ref_id: prior\n"
        target.write_text(prior, encoding="utf-8")

        def _boom_fsync(_fd: int) -> None:
            raise OSError("simulated crash during fsync")

        monkeypatch.setattr(os, "fsync", _boom_fsync)

        with pytest.raises(OSError, match="during fsync"):
            write_yaml_atomic(target, _REPRESENTATIVE, default_flow_style=False)

        assert target.read_text(encoding="utf-8") == prior
        assert _temp_siblings(tmp_path, "graph.yml") == []
