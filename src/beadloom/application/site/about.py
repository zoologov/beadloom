# beadloom:domain=application
# beadloom:feature=site-generation
"""README -> VitePress About page transform (BDL-046 BEAD-01).

:func:`render_about` rebases a README's Markdown link/image targets so they
resolve on the published VitePress site, while leaving prose, code spans, and
fenced code blocks untouched. It is pure and deterministic: no I/O, no DB,
same input -> same output.

The rebasing itself is :func:`beadloom.application.site.markdown_links.rebase_links`,
the rule every page that carries a project's own text uses since BDL-076
(``beadloom-ujzb.11``): a node's summary and a published document follow it too.
What is the About page's own is the README pair, which :func:`portal_links_for`
states:

- ``README.ru.md`` / ``README.md`` cross-links: if ``cross_link_routes`` maps
  the (lowercased) target to a site route, the link target is REWRITTEN to that
  route (visible text kept) — this is the bilingual About toggle
  (``[Русский](README.ru.md)`` -> ``[Русский](/ru/)``). When no map is given (or
  the target is absent from it) the link is dropped, keeping only the text: the
  README has no page to go to.
- ``docs/<x>.md`` / ``docs/<x>`` whose slug ``<x>`` is published ->
  extension-less site link ``/docs/<x>``.
- any other file in the repository (``LICENSE``, source paths, an unpublished
  ``docs/<x>``) -> the declared repository's page for it at the commit the site
  was generated from, under its forge's route, and an image to the file itself
  (BDL-076 ``beadloom-ujzb.8``). With no ``repo_url`` — a project that declares
  no repository link (BDL-076 B1) — or no commit or forge to address a path by,
  there is nowhere true to send it: a link keeps its text and an image its alt
  text.
- a target outside the repository (``../x``) -> its text.
- absolute addresses (any scheme, including shields.io badges), protocol-relative
  ``//host`` addresses and pure anchors (``#section``) -> unchanged.

Inline links, images, the badge-link idiom ``[![alt](img)](target)`` and
reference definitions are all rebased; links inside inline code spans and
fenced code blocks are never rewritten. The README then goes onto the page as
every project text does, shown as written rather than compiled as a Vue template
(:func:`beadloom.application.site.project_text.render_project_text`, BDL-076
``beadloom-ujzb.12``).
"""

# beadloom:domain=application

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.site.markdown_links import PortalLinks
from beadloom.application.site.project_text import render_project_text

if TYPE_CHECKING:
    from collections.abc import Mapping

    from beadloom.application.site.repository_link import RepositoryLink

#: The README pair, lowercased: the files an About page is rendered from.
_README_CROSS_LINKS = frozenset({"readme.md", "readme.ru.md"})


def portal_links_for(
    *,
    published_doc_slugs: set[str] | frozenset[str],
    repository: RepositoryLink,
    cross_link_routes: Mapping[str, str] | None = None,
    base: str = "/",
    published_files: frozenset[str] | None = None,
) -> PortalLinks:
    """What the portal publishes, with the README pair routed or withheld.

    A README of the pair that ``cross_link_routes`` does not route has no page,
    so a link to it keeps its text rather than going to the repository.
    ``repository`` is the declared repository at the site's commit. ``base``
    is the path the portal is served under; ``published_files`` are the project
    paths of the files it publishes under ``docs/``, ``None`` when unknown.
    """
    routes = {name.lower(): route for name, route in (cross_link_routes or {}).items()}
    return PortalLinks(
        doc_slugs=frozenset(published_doc_slugs),
        page_routes=routes,
        repository=repository,
        withheld=_README_CROSS_LINKS - routes.keys(),
        base=base,
        mirrored_files=published_files,
    )


def render_about(
    readme_text: str,
    *,
    published_doc_slugs: set[str],
    repository: RepositoryLink,
    cross_link_routes: dict[str, str] | None = None,
) -> str:
    """Transform README Markdown into the About-page body (links rebased, shown as written).

    ``cross_link_routes`` maps a lowercased README cross-link basename (e.g.
    ``"readme.ru.md"``) to the site route to rewrite it to (e.g. ``"/ru/"``).
    When ``None`` the cross-link is dropped (text kept) — back-compat.
    """
    portal = portal_links_for(
        published_doc_slugs=published_doc_slugs,
        repository=repository,
        cross_link_routes=cross_link_routes,
    )
    return render_project_text(readme_text, portal)
