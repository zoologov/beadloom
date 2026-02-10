"""Beadloom TUI -- Interactive terminal dashboard.

Requires the 'textual' package: pip install beadloom[tui]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def launch(db_path: Path, project_root: Path) -> None:
    """Launch the Beadloom TUI application.

    Raises ImportError if textual is not installed.
    """
    from beadloom.tui.app import BeadloomApp

    app = BeadloomApp(db_path=db_path, project_root=project_root)
    app.run()
