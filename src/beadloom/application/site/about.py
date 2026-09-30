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
  ``docs/<x>``) -> ``{repo_url}/blob/main/<path>``. With no ``repo_url`` — a
  project that declares no repository link (BDL-076 B1) — there is nowhere true
  to send it: a link keeps its text and an image its alt text.
- a target outside the repository (``../x``) -> its text.
- absolute addresses (any scheme, including shields.io badges), protocol-relative
  ``//host`` addresses and pure anchors (``#section``) -> unchanged.

Inline links, images, the badge-link idiom ``[![alt](img)](target)`` and
reference definitions are all rebased; links inside inline code spans and
fenced code blocks are never rewritten.
"""

# beadloom:domain=application

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.site.markdown_links import PortalLinks, rebase_links

if TYPE_CHECKING:
    from collections.abc import Mapping

#: The README pair, lowercased: the files an About page is rendered from.
_README_CROSS_LINKS = frozenset({"readme.md", "readme.ru.md"})


def portal_links_for(
    *,
    published_doc_slugs: set[str] | frozenset[str],
    repo_url: str,
    cross_link_routes: Mapping[str, str] | None = None,
) -> PortalLinks:
    """What the portal publishes, with the README pair routed or withheld.

    A README of the pair that ``cross_link_routes`` does not route has no page,
    so a link to it keeps its text rather than going to the repository.
    """
    routes = {name.lower(): route for name, route in (cross_link_routes or {}).items()}
    return PortalLinks(
        doc_slugs=frozenset(published_doc_slugs),
        page_routes=routes,
        repo_url=repo_url,
        withheld=_README_CROSS_LINKS - routes.keys(),
    )


def render_about(
    readme_text: str,
    *,
    published_doc_slugs: set[str],
    repo_url: str,
    cross_link_routes: dict[str, str] | None = None,
) -> str:
    """Transform README Markdown into the About-page body (link rebasing).

    ``cross_link_routes`` maps a lowercased README cross-link basename (e.g.
    ``"readme.ru.md"``) to the site route to rewrite it to (e.g. ``"/ru/"``).
    When ``None`` the cross-link is dropped (text kept) — back-compat.
    """
    portal = portal_links_for(
        published_doc_slugs=published_doc_slugs,
        repo_url=repo_url,
        cross_link_routes=cross_link_routes,
    )
    return rebase_links(readme_text, portal)
