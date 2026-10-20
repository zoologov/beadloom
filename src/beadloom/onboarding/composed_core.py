# beadloom:domain=onboarding
# beadloom:component=composed-core
"""The files that carry the composed core, compared and refreshed as one text.

BDL-083 S2R pass 1 Major 1 (RFC D13). Two files carry the composed core: Claude
reads ``.claude/CLAUDE.md`` and Cursor reads ``.cursor/rules/beadloom-flow.mdc``,
whose body is the same text under front matter. Both hold the auto-managed
regions -- version, stack, dependencies, the document language -- rendered for
the project, and those regions move with every release while the composition
does not.

Up to this module the two files were handled by two copies of the logic. The
``CLAUDE.md`` checks blanked the regions before comparing the body and refreshed
them separately; the Cursor rule's check compared the whole body and nothing
refreshed its regions. A version bump therefore read, for the Cursor rule, as a
composition that had moved (the core, the overlays, the project layer, none of
which had), and ``setup-rules --refresh`` repaired one file and left the other,
so the two tools carried two texts after the first release.

* :func:`core_carriers` -- the project-relative paths of both files.
* :func:`core_state` and :func:`core_digest` -- the one comparison of a carrier's
  body against its composition and the record Beadloom keeps of it, with every
  region's body blanked on every side.
* :func:`refresh_core_regions` -- re-renders the regions in every carrier on disk.

A region edited by hand is not a hand edit of the body: it reads as the region
gone stale and is re-rendered by the refresh, in both files the same way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.flow_manifest import ArtifactState, classify, digest
from beadloom.onboarding.scanner import blank_auto_regions, refresh_auto_regions
from beadloom.onboarding.tool_reach import cursor_core_rule_relpath

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "CLAUDE_MD_RELPATH",
    "core_carriers",
    "core_digest",
    "core_state",
    "refresh_core_regions",
]

#: Where Claude reads the composed core.
CLAUDE_MD_RELPATH = ".claude/CLAUDE.md"


def core_carriers() -> tuple[str, ...]:
    """Project-relative path of every file that carries the composed core."""
    return (CLAUDE_MD_RELPATH, str(cursor_core_rule_relpath()))


def core_digest(text: str) -> str:
    """The recorded fingerprint of a carrier: its text with every region's body blanked."""
    return digest(blank_auto_regions(text))


def core_state(
    *,
    on_disk: str | None,
    expected: str,
    recorded: str | None,
    alternates: tuple[str, ...] = (),
    accounted: bool = False,
) -> ArtifactState:
    """Classify a carrier's body against its composition, regions blanked on every side.

    The arguments are :func:`~beadloom.onboarding.flow_manifest.classify`'s, given
    as the texts themselves; ``recorded`` is the digest :func:`core_digest` wrote.
    """
    return classify(
        on_disk=None if on_disk is None else blank_auto_regions(on_disk),
        expected=blank_auto_regions(expected),
        recorded=recorded,
        alternates=tuple(blank_auto_regions(text) for text in alternates),
        accounted=accounted,
    )


def refresh_core_regions(project_root: Path, *, dry_run: bool = False) -> dict[str, list[str]]:
    """Re-render the regions of every carrier on disk; ``{relpath: changed regions}``.

    A carrier that is absent or already current is not in the result. With
    ``dry_run`` the names are returned and nothing is written.
    """
    changed: dict[str, list[str]] = {}
    for relpath in core_carriers():
        sections = refresh_auto_regions(project_root / relpath, project_root, dry_run=dry_run)
        if sections:
            changed[relpath] = sections
    return changed
