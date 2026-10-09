# beadloom:domain=application
# beadloom:feature=site-generation
"""The page map: which pages one ``docs site`` run wrote, by section and language.

BDL-080 S4a (owner, 2026-10-09). The dashboard names the portal's own population
beside lint's and the debt report's: how many pages the run generated, which
ones, in which section of the sidebar, and the language of each About page. The
generator states each page's section as it writes it; this module turns those
paths into the ``pages`` key of ``dashboard.data.json``.

A file a project places under ``.beadloom/site/`` is the project's, copied after
the run, and is not among the pages counted here.

**One responsibility:** project the pages a run wrote to the data file's shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

#: The portal's sections in the sidebar's order: the About pages, the dashboard,
#: the architecture pages, one page per node, the landscape pages, and the
#: published documentation.
PAGE_SECTIONS = ("about", "dashboard", "architecture", "nodes", "landscape", "docs")

_PAGE_SUFFIX = ".md"


def _pages(out_dir: Path, paths: Iterable[Path]) -> list[str]:
    return sorted(
        {path.relative_to(out_dir).as_posix() for path in paths if path.suffix == _PAGE_SUFFIX}
    )


def page_map_of(
    out_dir: Path,
    written: Mapping[str, Iterable[Path]],
    *,
    languages: Mapping[str, Path],
) -> dict[str, object]:
    """The data file's ``pages``: every section with its pages, and the languages.

    *written* maps a section of :data:`PAGE_SECTIONS` to the files the run wrote
    for it; only Markdown pages are counted, each once, by its path under
    *out_dir*. A section the run wrote nothing for is listed with 0 pages.
    *languages* maps a language code to the About page written in it.
    """
    listed = {name: _pages(out_dir, written.get(name, ())) for name in PAGE_SECTIONS}
    return {
        "count": sum(len(pages) for pages in listed.values()),
        "sections": [
            {"name": name, "count": len(pages), "pages": pages} for name, pages in listed.items()
        ],
        "languages": [
            {"language": code, "page": page.relative_to(out_dir).as_posix()}
            for code, page in sorted(languages.items())
        ],
    }
