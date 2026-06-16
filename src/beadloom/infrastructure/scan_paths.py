"""Scan-path resolution: read source scan directories from ``config.yml``.

A small, domain-agnostic config reader.  Lives in the infrastructure layer so
that domains (e.g. ``graph``) can resolve scan directories without reaching UP
into the ``application`` layer — closing the historic ``graph -> application``
layering inversion (BDL-059 S3).
"""

# beadloom:domain=infrastructure
# beadloom:component=scan-paths

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Default scan directories when config.yml has no scan_paths.
_DEFAULT_SCAN_DIRS = ("src", "lib", "app")


def resolve_scan_paths(project_root: Path) -> list[str]:
    """Resolve source scan directories from config.yml.

    Reads ``scan_paths`` from ``.beadloom/config.yml``.  Falls back to
    ``["src", "lib", "app"]`` when config is absent or has no scan_paths.
    """
    config_path = project_root / ".beadloom" / "config.yml"
    if config_path.exists():
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        paths = config.get("scan_paths")
        if isinstance(paths, list) and paths:
            return [str(p) for p in paths]
    return list(_DEFAULT_SCAN_DIRS)
