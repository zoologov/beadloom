"""E2E tests for BDL-018: Doc-Sync Honest Detection.

Validates that the three-layer sync-check mechanism correctly detects
documentation staleness across realistic scenarios:
  1. Hash-based drift detection (preserved baselines across reindex)
  2. Source-directory coverage (untracked files)
  3. Module-name coverage (missing mentions in docs)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import open_db
from beadloom.infrastructure.reindex import reindex

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a realistic Beadloom project with graph, docs, and code."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    docs_dir = tmp_path / "docs" / "domains" / "myapp"
    docs_dir.mkdir(parents=True)
    src_dir = tmp_path / "src" / "myapp"
    src_dir.mkdir(parents=True)

    # Graph YAML — one domain node with source directory.
    # Note: docs: must be a YAML list (the parser iterates it).
    (graph_dir / "domains.yml").write_text(
        "nodes:\n"
        "  - ref_id: myapp\n"
        "    kind: domain\n"
        '    summary: "My App domain"\n'
        "    source: src/myapp/\n"
        "    docs:\n"
        "      - docs/domains/myapp/README.md\n"
    )

    # Documentation mentioning 'handler' module.
    (docs_dir / "README.md").write_text(
        "# My App\n\nThis domain contains the handler module.\n"
    )

    # Code with beadloom annotation.
    (src_dir / "__init__.py").write_text("")
    (src_dir / "handler.py").write_text(
        "# beadloom:domain=myapp\n"
        "def process():\n"
        "    return True\n"
    )

    return tmp_path


class TestSyncHonestDetection:
    """E2E: sync-check detects staleness after code changes."""

    def test_baseline_then_drift(self, project: Path) -> None:
        """After reindex, adding new code should make sync-check detect stale."""
        from beadloom.doc_sync.engine import check_sync

        # 1. Initial reindex — establishes baseline.
        reindex(project)
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        results = check_sync(conn, project_root=project)
        conn.close()

        # Should have at least one sync pair.
        assert len(results) >= 1

        # 2. Add a NEW symbol to the code file.
        handler = project / "src" / "myapp" / "handler.py"
        handler.write_text(
            "# beadloom:domain=myapp\n"
            "def process():\n"
            "    return True\n\n"
            "def new_feature():\n"
            "    return 42\n"
        )

        # 3. Second reindex — should preserve baseline from step 1.
        reindex(project)
        conn = open_db(db_path)
        results = check_sync(conn, project_root=project)

        # 4. At least one entry should be stale (symbols changed).
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) >= 1, f"Expected stale entries, got: {results}"
        assert any(
            r.get("reason") == "symbols_changed" for r in stale
        ), f"Expected symbols_changed reason, got: {stale}"

        conn.close()

    def test_untracked_file_detected(self, project: Path) -> None:
        """New file in source dir without annotation should be flagged."""
        from beadloom.doc_sync.engine import check_source_coverage

        # 1. Initial reindex.
        reindex(project)

        # 2. Add a new file WITHOUT annotation.
        new_file = project / "src" / "myapp" / "utils.py"
        new_file.write_text("def helper():\n    pass\n")

        # 3. Check source coverage (doesn't need reindex).
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        gaps = check_source_coverage(conn, project)
        conn.close()

        # 4. Should detect 'utils.py' as untracked.
        assert len(gaps) >= 1
        assert any(
            "src/myapp/utils.py" in gap["untracked_files"]
            for gap in gaps
        ), f"Expected utils.py in untracked files, got: {gaps}"

    def test_missing_module_detected(self, project: Path) -> None:
        """Doc not mentioning a module name should be flagged."""
        from beadloom.doc_sync.engine import check_doc_coverage

        # Add a second code file WITH annotation.
        (project / "src" / "myapp" / "models.py").write_text(
            "# beadloom:domain=myapp\n"
            "class User:\n"
            "    pass\n"
        )

        # Reindex to include new file.
        reindex(project)

        # Doc mentions 'handler' but NOT 'models'.
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        gaps = check_doc_coverage(conn, project)
        conn.close()

        # Should detect 'models' as missing from doc.
        assert len(gaps) >= 1
        assert any(
            "models" in gap["missing_modules"]
            for gap in gaps
        ), f"Expected 'models' in missing_modules, got: {gaps}"

    def test_full_flow_integration(self, project: Path) -> None:
        """Full flow: reindex → add code → reindex → sync-check → stale."""
        from beadloom.doc_sync.engine import check_sync

        # 1. Initial reindex.
        reindex(project)

        # 2. Add new module + modify existing.
        (project / "src" / "myapp" / "service.py").write_text(
            "# beadloom:domain=myapp\n"
            "class MyService:\n"
            "    def run(self) -> None:\n"
            "        pass\n"
        )
        handler = project / "src" / "myapp" / "handler.py"
        handler.write_text(
            "# beadloom:domain=myapp\n"
            "def process():\n"
            "    return True\n\n"
            "def extra():\n"
            "    return 99\n"
        )

        # 3. Second reindex.
        reindex(project)

        # 4. Full sync check.
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        results = check_sync(conn, project_root=project)
        conn.close()

        # 5. Must detect staleness from at least one of:
        #    - symbols_changed (new symbols)
        #    - missing_modules (doc doesn't mention 'service')
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) >= 1, (
            f"Expected stale entries after adding code, got all ok: {results}"
        )


class TestAcceptanceCriteria:
    """Acceptance tests: verify the success metric from the PRD."""

    def test_stale_count_meets_threshold(self, project: Path) -> None:
        """Simulates a project with known stale docs, verifies >= 6 detected."""
        from beadloom.doc_sync.engine import check_sync

        # Create a project with 6 domains, each with stale docs.
        graph_dir = project / ".beadloom" / "_graph"
        docs_base = project / "docs" / "domains"
        src_base = project / "src"

        nodes_yaml = "nodes:\n"
        for i in range(6):
            name = f"domain{i}"
            (docs_base / name).mkdir(parents=True, exist_ok=True)
            (docs_base / name / "README.md").write_text(f"# Domain {i}\n")
            (src_base / name).mkdir(parents=True, exist_ok=True)
            (src_base / name / "__init__.py").write_text("")
            (src_base / name / "core.py").write_text(
                f"# beadloom:domain={name}\n"
                "def original():\n"
                "    pass\n"
            )
            nodes_yaml += (
                f"  - ref_id: {name}\n"
                f"    kind: domain\n"
                f'    summary: "Domain {i}"\n'
                f"    source: src/{name}/\n"
                f"    docs:\n"
                f"      - docs/domains/{name}/README.md\n"
            )

        (graph_dir / "domains.yml").write_text(nodes_yaml)

        # First reindex — baseline.
        reindex(project)

        # Add new code to all 6 domains.
        for i in range(6):
            name = f"domain{i}"
            (src_base / name / "core.py").write_text(
                f"# beadloom:domain={name}\n"
                "def original():\n"
                "    pass\n\n"
                "def new_feature():\n"
                "    return True\n"
            )

        # Second reindex.
        reindex(project)

        # Sync-check.
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        results = check_sync(conn, project_root=project)
        conn.close()

        stale_refs = {r["ref_id"] for r in results if r["status"] == "stale"}
        assert len(stale_refs) >= 6, (
            f"Expected >= 6 stale refs, got {len(stale_refs)}: {stale_refs}"
        )
