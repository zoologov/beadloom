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
@click.option(
    "--section",
    "as_section",
    is_flag=True,
    help="Render the answer as the `## Axes` section a work item's document carries.",
)
def impact(
    target: str,
    *,
    project: Path | None,
    root: Path | None,
    as_json: bool,
    as_section: bool,
) -> None:
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
    elif as_section:
        from beadloom.application.impact.section import render_axes_section

        click.echo(render_axes_section(answer))
    else:
        click.echo(render_impact(answer))


@main.command()
@click.argument(
    "document", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--refs",
    "as_refs",
    is_flag=True,
    help="Print only the `refs:` line, generated from the rows kept in scope.",
)
@click.option("--json", "as_json", is_flag=True, help="JSON output.")
def axes(*, document: Path, as_refs: bool, as_json: bool) -> None:
    """Read a work item's `## Axes` section back: what it declares, and its refs.

    DOCUMENT is a BRIEF or an RFC. The section records the derivation's output
    and the person's scope decision; this reads it back, so a bead's `refs:` is
    GENERATED from the document rather than written beside it. Two authored
    homes for one fact are two things that can disagree, which is the class this
    epic exists to remove.
    """
    from beadloom.doc_sync.axes_section import read_axes_section, refs_line

    section = read_axes_section(document.read_text(encoding="utf-8"))
    if section is None:
        click.echo(
            f"Error: {document} carries no `## Axes` section — run "
            f"`beadloom impact <path|symbol> --section` and record its answer there",
            err=True,
        )
        sys.exit(1)

    if as_json:
        click.echo(
            json.dumps(
                {
                    "seed": section.seed,
                    "derived_by": section.derived_by,
                    "unresolved": section.unresolved,
                    "refs": [axis.node for axis in section.kept if axis.node],
                    "axes": [
                        {
                            "axis": axis.axis,
                            "node": axis.node,
                            "sites": axis.sites,
                            "in_scope": axis.in_scope,
                            "why": axis.why,
                            "line": axis.line,
                        }
                        for axis in section.axes
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if as_refs:
        click.echo(refs_line(section))
        return

    click.echo(f"Seed: {section.seed or 'NOT STATED'}")
    click.echo(f"Unresolved: {section.unresolved or 'NOT STATED'}")
    click.echo("")
    for axis in section.axes:
        decision = {True: "in", False: "out", None: "UNDECIDED"}[axis.in_scope]
        click.echo(f"  [{decision}] {axis.axis} — {axis.node or '—'}: {axis.sites}")
    click.echo("")
    click.echo(refs_line(section))
