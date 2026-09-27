"""The version surface: the command's report over a project, and the places it names."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from beadloom.doc_sync.version_surface import VersionSurface


def run_version_surface(project: Path, *extra: str) -> tuple[int, str]:
    result = CliRunner().invoke(main, ["version-surface", "--project", str(project), *extra])
    if result.exception is not None and not isinstance(result.exception, SystemExit):
        raise result.exception
    return result.exit_code, result.output


def block_under(output: str, heading: str) -> str:
    return next((block for block in output.split("\n\n") if heading in block), "")


def places_at(surface: VersionSurface, relative: str) -> list[object]:
    wanted = Path(relative)
    return [place for place in surface.places if place.path == wanted]
