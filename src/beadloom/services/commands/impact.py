"""The `impact` command: what a change touches, answered from the source."""
# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from beadloom.services.commands._root import main


@main.command()
@click.argument("target")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root, which supplies the boundary (default: current directory).",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Source tree to derive over (default: derived from the target).",
)
@click.option("--json", "as_json", is_flag=True, help="JSON output.")
def impact(target: str, *, project: Path | None, root: Path | None, as_json: bool) -> None:
    """Who else writes this, who else calls it, and how many branches it has.

    TARGET is a path or a symbol name. The seed the answer is computed over is
    DERIVED from it and named in the output, together with the rule that derived
    it: the same derivation reports two writers under one seed and none under
    another, so an answer that does not say what it was seeded with cannot be
    checked. A target no rule finds a sink for is reported as unresolved rather
    than answered over an empty set.
    """
    from beadloom.application.impact import (
        NoSuchTargetError,
        answer_to_dict,
        impact_of,
        render_impact,
    )

    project_root = project or Path.cwd()
    try:
        answer = impact_of(target, project_root=project_root, root=root)
    except NoSuchTargetError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(answer_to_dict(answer), ensure_ascii=False, indent=2))
    else:
        click.echo(render_impact(answer))
