"""The scan paths are read from ``.beadloom/config.yml``, with a default when it is absent.

Split out of ``tests/test_reindex.py`` (BDL-074 ``beadloom-2mj3.7``): the function
lives in ``infrastructure/scan_paths.py`` and the reindex hub only re-exports it;
the reindex's own use of it stays with the reindex tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.infrastructure.scan_paths import resolve_scan_paths

if TYPE_CHECKING:
    from pathlib import Path


class TestResolveScanPaths:
    """Tests for config-driven scan path resolution."""

    def test_reads_from_config(self, tmp_path: Path) -> None:
        """scan_paths from config.yml are used."""
        beadloom_dir = tmp_path / ".beadloom"
        beadloom_dir.mkdir()
        (beadloom_dir / "config.yml").write_text("scan_paths:\n- backend\n- frontend/src\n")
        result = resolve_scan_paths(tmp_path)
        assert result == ["backend", "frontend/src"]

    def test_defaults_without_config(self, tmp_path: Path) -> None:
        """Falls back to defaults when no config exists."""
        result = resolve_scan_paths(tmp_path)
        assert result == ["src", "lib", "app"]
