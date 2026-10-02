# beadloom:domain=application
# beadloom:feature=site-generation
"""Where a link in a project's own Markdown points once the text is on the portal.

The generator copies text out of the project's files onto portal pages: the
README onto the About page, a node's summary onto its node page, and every
document under ``docs/`` into the published documentation. A relative link in
that text was written against the file it sat in. On the portal it resolves
against the page instead, and a target the portal does not publish is a dead
link that fails ``vitepress build`` (BDL-076, ``beadloom-ujzb.11``: a README that
opened with ``See [license](LICENSE).`` failed an adopter's build through the
root service's page).

:func:`rebase_links` is the one rule for all of them. The target is resolved
against the directory of the file the text came from, and then:

- a file the portal publishes (a document under ``docs/``, the README pair) ->
  that file's page;
- a file inside a directory the page mirrors (a published document linking
  another file under ``docs/``) -> left as written, since it still resolves;
  when the portal names the files it publishes there, a target it does not
  publish becomes the link's text, since the build cannot resolve it
  (``beadloom-ujzb.12``: ``![](./missing.png)`` failed ``vitepress build``);
- an image the portal publishes (a file under ``docs/``, which the portal copies)
  on a page outside that directory -> the copy, from where the page sits, when
  the page's place is known (``beadloom-ujzb.12``);
- any other file in the repository -> the declared repository's page for it, and
  for an image the file itself, at the commit the site was generated from and
  under the forge's own route (``beadloom-ujzb.8``); with no repository
  declared, no commit, or no forge known for its host, the link's own text (an
  image's alt text);
- a target outside the repository -> the link's text;
- an absolute address (any scheme), a protocol-relative one, an anchor and an
  empty target -> left as written.

Inline links, images, the badge-link idiom ``[![alt](img)](target)`` and
reference definitions (``[label]: target``) are all rebased. A reference whose
definition becomes text is withdrawn: the definition is removed and every
``[text][label]``, ``[label][]`` and ``[label]`` naming it becomes its text.
A link is what markdown-it renders as one, read the way VitePress reads the text
(:func:`.markdown_source.read_markdown`): a link whose text is a code span is a
link, and anything inside code or raw HTML is not (BDL-076, ``beadloom-ujzb.21``).
Pure and deterministic.

:func:`raw_html_destination` is the same rule for an ``href`` or a ``src`` the
project wrote as raw HTML, which VitePress neither checks nor rewrites: a
published page is reached by its full address under the portal's base path.
"""

# beadloom:domain=application

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.application.site.markdown_positions import normalise
from beadloom.application.site.markdown_source import Edit, apply_edits, read_markdown
from beadloom.application.site.repository_link import RepositoryLink

if TYPE_CHECKING:
    from collections.abc import Mapping

    from beadloom.application.site.markdown_source import Definition, Link

# A target the portal does not resolve against its own tree: any URI scheme
# (http:, mailto:, ...) or a protocol-relative "//host" address.
_ABSOLUTE_RE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|//)")
_WHITESPACE_RE = re.compile(r"\s")

_DOCS_DIR = "docs"


@dataclass(frozen=True)
class PortalLinks:
    """What the portal publishes, and where a file it does not publish lives.

    ``doc_slugs`` are the published documents, ``docs/``-relative without
    ``.md``; ``page_routes`` maps a lowercased project path that has a page of
    its own (the README pair) to that page's route; ``repository`` is the
    declared repository at the commit the site was generated from, empty when
    none is declared; a lowercased project path in ``withheld``
    has no destination at all, so a link to it becomes its text. ``base`` is the
    path the portal is served under, which a raw HTML link needs spelled out;
    ``mirrored_files`` are the project paths of every file the portal publishes
    in a mirrored directory, ``None`` when unknown, and then a link inside that
    directory is trusted as written.
    """

    doc_slugs: frozenset[str] = frozenset()
    page_routes: Mapping[str, str] = field(default_factory=dict)
    repository: RepositoryLink = field(default_factory=RepositoryLink)
    withheld: frozenset[str] = frozenset()
    base: str = "/"
    mirrored_files: frozenset[str] | None = None

    def route_of(self, path: str) -> str | None:
        """The portal page of the project file *path*, or ``None``."""
        route = self.page_routes.get(path.lower())
        if route is not None:
            return route
        prefix = f"{_DOCS_DIR}/"
        if not path.startswith(prefix):
            return None
        rest = path[len(prefix) :]
        slug = rest[: -len(".md")] if rest.endswith(".md") else rest
        return f"/{_DOCS_DIR}/{slug}" if slug in self.doc_slugs else None

    def page_url(self, route: str) -> str:
        """*route* as a raw link reaches it: under the base, at the file VitePress writes.

        A route ending in ``/`` is a directory's index page; any other route is
        the ``.html`` file VitePress writes for it.
        """
        path = route.lstrip("/")
        if path and not path.endswith("/"):
            path = f"{path}.html"
        return f"{self.base.rstrip('/')}/{path}"

    def publishes(self, path: str) -> bool:
        """Whether the project file *path*, in a mirrored directory, reaches the portal.

        *path* may name the file, its page without ``.md`` or as ``.html``, or a
        directory whose ``index.md`` is published.
        """
        if self.mirrored_files is None:
            return True
        stem = path[: -len(".html")] if path.endswith(".html") else path
        candidates = (path, f"{stem}.md", f"{path}/index.md")
        return any(candidate in self.mirrored_files for candidate in candidates)

    def repository_url_of(self, path: str, *, image: bool = False) -> str | None:
        """The declared repository's page for *path* (for an *image*, the file), or ``None``.

        ``None`` with no repository, and when the repository cannot address a
        path: no commit to link at, or no forge known for its host. The root is
        the repository itself.
        """
        repository = self.repository
        if not repository.url:
            return None
        if not path:
            return repository.url
        link = repository.raw_url(path) if image else repository.file_url(path)
        return link or None


@dataclass(frozen=True)
class _Origin:
    """Where the text came from, the directory its page mirrors, and where the page sits.

    ``page_dir`` is ``None`` when the page's place on the portal is not known.
    """

    portal: PortalLinks
    source_dir: str
    mirrored_dir: str
    page_dir: str | None = None


def rebase_links(
    markdown: str,
    portal: PortalLinks,
    *,
    source_dir: str = "",
    mirrored_dir: str = "",
    page_dir: str | None = None,
    front_matter: bool = True,
) -> str:
    """Rebase every link in *markdown* onto the portal (see the module docstring).

    ``source_dir`` is the project-relative directory of the file the text came
    from (``""`` for the project root). ``mirrored_dir`` is a project directory
    the page's own location mirrors on the portal (``"docs"`` for a published
    document), so a relative link that stays inside it is left as written.
    ``page_dir`` is the portal directory the page is written to (``""`` for the
    About page, ``"services"`` for a service's page), which lets an image the
    portal publishes be referenced from there. ``front_matter`` says a leading
    front matter block is not Markdown (the text opens its page).

    The links are the ones markdown-it renders (:func:`.markdown_source.read_markdown`),
    so a link whose text is code is one (``beadloom-ujzb.21``), and a link in
    code or raw HTML is not.
    """
    text = normalise(markdown)
    source = read_markdown(text, front_matter=front_matter)
    origin = _origin(portal, source_dir, mirrored_dir, page_dir)
    edits: list[Edit] = []
    withdrawn: set[str] = set()
    defined: set[str] = set()
    for definition in source.definitions:
        if (
            not _rebase_definition(text, definition, origin, edits)
            and definition.reference not in defined
        ):
            withdrawn.add(definition.reference)
        defined.add(definition.reference)
    for link in source.links:
        _rebase_link(text, link, origin, withdrawn, edits)
    return apply_edits(text, edits)


def _rebase_link(
    text: str, link: Link, origin: _Origin, withdrawn: set[str], edits: list[Edit]
) -> None:
    """Rebase one link; with nowhere to go, or a withdrawn definition, it becomes its label."""
    if link.destination is None:
        if link.reference in withdrawn:
            edits.extend(_unwrapped(link))
        return
    start, end = link.destination
    written = text[start:end]
    url = written[1:-1] if written.startswith("<") else written
    destination = _destination(url, origin, image=link.image)
    if destination is None:
        edits.extend(_unwrapped(link))
    elif destination != url:
        edits.append(Edit(start, end, _written_destination(destination, written)))


def _unwrapped(link: Link) -> list[Edit]:
    """The edits that leave only the label of *link*: its opener and its tail go."""
    pieces = (link.opener, *link.tail)
    return [Edit(start, end, "") for start, end in pieces]


def _rebase_definition(
    text: str, definition: Definition, origin: _Origin, edits: list[Edit]
) -> bool:
    """Rebase one definition; ``False`` when it has nowhere to go and is removed."""
    start, end = definition.destination
    written = text[start:end]
    url = written[1:-1] if written.startswith("<") else written
    destination = _destination(url, origin)
    if destination is None:
        edits.extend(_removed(text, definition))
        return False
    if destination != url:
        edits.append(Edit(start, end, _written_destination(destination, written)))
    return True


def _removed(text: str, definition: Definition) -> list[Edit]:
    """The edits that remove *definition*: its whole lines, or, in a container, its own text."""
    line_start, line_end = definition.lines
    first = definition.pieces[0][0] if definition.pieces else line_start
    if not text[line_start:first].strip():
        return [Edit(line_start, line_end, "")]
    return [Edit(start, end, "") for start, end in definition.pieces]


def _written_destination(destination: str, written: str) -> str:
    """*destination* as Markdown writes it: in angle brackets where it must be."""
    if written.startswith("<") and _WHITESPACE_RE.search(destination):
        return f"<{destination}>"
    return destination


def raw_html_destination(
    url: str,
    portal: PortalLinks,
    *,
    source_dir: str = "",
    mirrored_dir: str = "",
    page_dir: str | None = None,
    asset: bool = False,
) -> str | None:
    """Where an ``href`` (or, with *asset*, a ``src``) written as raw HTML goes.

    The rule is :func:`rebase_links`'s, except that a link to a published page
    is written out in full, as :meth:`PortalLinks.page_url` gives it: VitePress
    rewrites a Markdown link and leaves a raw one alone. ``None`` means the
    attribute has nowhere to go.
    """
    origin = _origin(portal, source_dir, mirrored_dir, page_dir)
    if not asset:
        page = _page_of(url, origin)
        if page is not None:
            return page
    return _destination(url, origin, image=asset)


def _origin(
    portal: PortalLinks, source_dir: str, mirrored_dir: str, page_dir: str | None
) -> _Origin:
    page = None if page_dir is None else page_dir.strip("/")
    return _Origin(portal, source_dir.strip("/"), mirrored_dir.strip("/"), page)


def _is_absolute(url: str) -> bool:
    """A target the portal does not resolve: empty, an anchor, a scheme or ``//host``."""
    return not url or url.startswith("#") or _ABSOLUTE_RE.match(url) is not None


def _split_suffix(url: str) -> tuple[str, str]:
    """*url*'s path, and its ``#fragment`` / ``?query`` suffix."""
    cut = min((i for i in (url.find("#"), url.find("?")) if i >= 0), default=len(url))
    return url[:cut], url[cut:]


def _page_of(url: str, origin: _Origin) -> str | None:
    """The full address of the published page *url* names, or ``None`` when it names none."""
    if _is_absolute(url):
        return None
    path, suffix = _split_suffix(url)
    resolved = _resolve(path, origin.source_dir)
    if resolved is None or resolved.lower() in origin.portal.withheld:
        return None
    route = origin.portal.route_of(resolved)
    return None if route is None else origin.portal.page_url(route) + suffix


def _destination(url: str, origin: _Origin, *, image: bool = False) -> str | None:
    """Where *url* goes on the portal: a URL (possibly *url* itself), or ``None`` for text.

    An *image* the portal publishes is referenced from the page's own directory.
    """
    if _is_absolute(url):
        return url
    path, suffix = _split_suffix(url)
    resolved = _resolve(path, origin.source_dir)
    if resolved is None or resolved.lower() in origin.portal.withheld:
        return None
    if origin.mirrored_dir and _is_within(resolved, origin.mirrored_dir):
        published = resolved == origin.mirrored_dir or origin.portal.publishes(resolved)
        return url if published else None
    if image and origin.page_dir is not None and resolved in (origin.portal.mirrored_files or ()):
        return _relative(resolved, origin.page_dir) + suffix
    route = origin.portal.route_of(resolved)
    if route is not None:
        return route + suffix
    in_repository = origin.portal.repository_url_of(resolved, image=image)
    return None if in_repository is None else _with_suffix(in_repository, suffix)


def _with_suffix(link: str, suffix: str) -> str:
    """*link* with the target's ``?query``/``#fragment``; a query joins one *link* has."""
    if suffix.startswith("?") and "?" in link:
        return f"{link}&{suffix[1:]}"
    return link + suffix


def _resolve(path: str, source_dir: str) -> str | None:
    """*path* as a project-relative path, ``""`` for the root, ``None`` outside the project.

    A leading ``/`` is the repository root, as a forge reads it in a README.
    """
    joined = path.lstrip("/") if path.startswith("/") else posixpath.join(source_dir, path)
    normal = posixpath.normpath(joined) if joined else "."
    if normal == ".." or normal.startswith("../"):
        return None
    return "" if normal == "." else normal


def _relative(path: str, page_dir: str) -> str:
    """*path*, a portal file, as a relative reference from the page directory *page_dir*."""
    relative = posixpath.relpath(path, page_dir or ".")
    return relative if relative.startswith("../") else f"./{relative}"


def _is_within(path: str, directory: str) -> bool:
    return path == directory or path.startswith(f"{directory}/")
