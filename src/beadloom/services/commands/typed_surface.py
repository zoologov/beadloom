"""The ``typed-surface`` command — which files this project declares type-checked.

Presentation and wiring only. The derivation is
:func:`beadloom.application.typed_surface.declared_typed_surface`; this module
turns a surface into lines on a stream and one exit code.

The command exists so a gate can scope a type check to the declared surface
without naming it. ``beadloom-mr2l.82`` scoped the same check by writing the
surface into the hook template, and the mypy configuration then moved while the
hook did not -- so what a hook needs is not a list but the question answered at
the moment it asks.

``--filter`` is the form the pre-commit hook uses: paths in on standard input,
the ones inside the surface out, led by a marked verdict line. The marker is
:data:`beadloom.application.declared_scope.VERDICT_MARKER`, the same one
``scope-check --porcelain`` leads with, so a hook written in ``sh`` splits a
verdict from a payload on one shape rather than on an agreement between two
spellings.

Codes (the contract a caller may rely on):

* ``0`` — the surface was derived. A commit staging nothing inside it also exits
  0 and says so in the verdict: an empty population is a fact, not a failure.
* ``2`` — the surface could not be derived. The verdict carries the reason, on
  standard output, because the caller that needs it most is a hook that reads
  one stream.
"""

# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from beadloom.services.commands._root import main

if TYPE_CHECKING:
    from beadloom.application.typed_surface import TypedSurface

_EXIT_DERIVED = 0
_EXIT_UNDECLARED = 2


@main.command("typed-surface")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--filter",
    "as_filter",
    is_flag=True,
    default=False,
    help=(
        "Read paths from standard input and print the ones inside the declared "
        "surface, led by a marked verdict line — the form a gate consumes."
    ),
)
@click.option("--json", "as_json", is_flag=True, default=False, help="JSON output.")
def typed_surface(*, project: Path | None, as_filter: bool, as_json: bool) -> None:
    """Report the surface this project declares typed, derived from its config.

    A type check is a claim about the files it was handed. Handing it more than
    the project declares typed makes every commit red for reasons nobody signed
    up to, and the one commit that carries a real violation prints the same
    sentence as the rest.
    """
    from beadloom.application.typed_surface import declared_typed_surface

    surface = declared_typed_surface(project or Path.cwd())
    if as_filter:
        _emit_filter(surface)
        return
    click.echo(json.dumps(_payload(surface), indent=2) if as_json else _human(surface))
    sys.exit(_EXIT_DERIVED if surface.declared else _EXIT_UNDECLARED)


def _emit_filter(surface: TypedSurface) -> None:
    """The verdict, then the covered paths — one stream, one statement."""
    from beadloom.application.declared_scope import VERDICT_MARKER

    staged = tuple(line.strip() for line in sys.stdin.read().splitlines() if line.strip())
    partition = surface.partition(staged)
    click.echo(f"{VERDICT_MARKER}{partition.describe()}")
    for path in partition.inside:
        click.echo(path)
    sys.exit(_EXIT_DERIVED if surface.declared else _EXIT_UNDECLARED)


def _human(surface: TypedSurface) -> str:
    """The report a person reads: what is covered, and what was not resolved."""
    lines = [
        "Typed surface — derived from this project's own declaration, never listed",
        "",
    ]
    if surface.declared:
        lines.append(f"  Covered ({len(surface.roots)}):")
        lines.extend(
            f"    {root.path}    {root.source}"
            for root in sorted(surface.roots, key=lambda r: r.path)
        )
    else:
        lines.append(f"  NOT DECLARED: {surface.why_undeclared}")
        lines.append(
            "  A check with no declared surface is not checked. It is not clean."
        )
    lines.append("")
    lines.extend(_unresolved_lines(surface))
    return "\n".join(lines)


def _unresolved_lines(surface: TypedSurface) -> list[str]:
    """What the derivation could not turn into a root, named rather than dropped."""
    if not surface.unresolved:
        return []
    lines = [f"  Unresolved ({len(surface.unresolved)}):"]
    lines.extend(f"    {u.source} — {u.why}" for u in surface.unresolved)
    return lines


def _payload(surface: TypedSurface) -> dict[str, object]:
    """The same facts as the human report, in the shape a monitor reads."""
    return {
        "declared": surface.declared,
        "why_undeclared": surface.why_undeclared,
        "roots": [{"path": r.path, "source": r.source} for r in surface.roots],
        "unresolved": [{"source": u.source, "why": u.why} for u in surface.unresolved],
    }
