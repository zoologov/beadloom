# beadloom:domain=application
# beadloom:feature=site-generation
"""Retire a node's page from a section the node's page has left (BDL-081 R2).

A node's page sits under the section its kind names (:mod:`node_pages`), so a node
whose kind is read differently moves: a node declared ``kind: site`` is read as a
``service`` since BDL-080 S1a, and 8.0.0 wrote its page under ``other/``. A portal
rewritten in place would otherwise carry that node twice, the old page beside the
new one.

Node pages are generated content and carry no marker, so a page is removed only on
the evidence :func:`~beadloom.application.site.node_pages.is_page_of` reads: the
front matter and heading ``docs site`` writes on every node page. A file at that path
with any other opening is the project's and stays; so does any path the project
provides under ``.beadloom/site/``, which is copied over the portal last; and so does
the page of a node this run writes no page for. A section the removal leaves empty is
removed with it, as the scaffold's retired files do.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.site.node_pages import NODE_PAGE_SECTIONS, NodePage, is_page_of
from beadloom.application.site.scaffold import retire_emptied_folders

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable
    from pathlib import Path


@dataclass(frozen=True)
class RetiredPages:
    """The node pages one run removed from a section they left, and the sections emptied."""

    pages: tuple[str, ...] = ()
    folders: tuple[str, ...] = ()


def _is_beadloom_page(path: Path, ref_id: str) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        return is_page_of(path.read_text(encoding="utf-8"), ref_id)
    except (OSError, UnicodeDecodeError):
        return False


def retire_moved_pages(
    out_dir: Path, pages: Iterable[NodePage], *, keep: Collection[str] = ()
) -> RetiredPages:
    """Remove the page of each node in *pages* that beadloom wrote under another section.

    The old path is built from the node's own id, never read back out of the new
    path: an id may hold a ``/``, so ``services/x/b.md`` is the page of ``x/b`` and
    says nothing about ``b``. No path this run wrote is ever a candidate.

    Args:
        out_dir: The portal's root.
        pages: Every node page this run wrote.
        keep: Paths relative to *out_dir* never removed: the project's overrides.
    """
    pages = list(pages)
    protected = {page.rel_path for page in pages} | set(keep)
    retired: list[str] = []
    for page in pages:
        for section in NODE_PAGE_SECTIONS:
            old = f"{section}/{page.ref_id}.md"
            if old in protected or not _is_beadloom_page(out_dir / old, page.ref_id):
                continue
            (out_dir / old).unlink()
            retired.append(old)
    retired.sort()
    folders = retire_emptied_folders(out_dir, retired)
    return RetiredPages(pages=tuple(retired), folders=tuple(folders))
