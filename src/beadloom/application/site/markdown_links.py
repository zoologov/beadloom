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
- any other file in the repository -> the declared repository's copy of it, or,
  with no repository declared, the link's own text (an image's alt text);
- a target outside the repository -> the link's text;
- an absolute address (any scheme), a protocol-relative one, an anchor and an
  empty target -> left as written.

Inline links, images, the badge-link idiom ``[![alt](img)](target)`` and
reference definitions (``[label]: target``) are all rebased. A reference whose
definition becomes text is withdrawn: the definition is removed and every
``[text][label]``, ``[label][]`` and ``[label]`` naming it becomes its text.
Nothing inside a code span or a fenced block changes. Pure and deterministic.
"""

# beadloom:domain=application

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

# Inline link/image: optional "!" (image), [text], (target). The text may hold
# one whole nested image, the badge-link idiom. The target stops at the first
# ")", which is enough for the targets READMEs and summaries carry.
_LINK_RE = re.compile(r"(!?)\[((?:[^\[\]]|!\[[^\]]*\]\([^)]*\))*)\]\(([^)]*)\)")

# Code spans and fenced blocks, which are never rewritten. Fences first, so a
# fence wins over the inline spans inside it.
_PROTECT_RE = re.compile(r"(```.*?```|``.*?``|`[^`]*`)", re.DOTALL)

# A reference definition on its own line: up to three spaces of indent,
# [label]:, the target (bare or <bracketed>), then an optional title.
_DEFINITION_RE = re.compile(
    r"^( {0,3})\[([^\]\n]+)\]:[ \t]*(<[^>\n]*>|\S+)([^\n]*)(\n?)", re.MULTILINE
)

# A full or collapsed reference: [text][label] / [text][].
_FULL_REFERENCE_RE = re.compile(r"(!?)\[((?:[^\[\]]|!\[[^\]]*\]\([^)]*\))*)\]\[([^\[\]]*)\]")
# A shortcut reference: [label], not followed by "(", "[" or ":".
_SHORTCUT_REFERENCE_RE = re.compile(r"(!?)(?<!\])\[([^\[\]]+)\](?![\[(:])")

# A target the portal does not resolve against its own tree: any URI scheme
# (http:, mailto:, ...) or a protocol-relative "//host" address.
_ABSOLUTE_RE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|//)")

# A target and its optional title: `path "title"` or `<path with spaces> "title"`.
_TARGET_RE = re.compile(r"^\s*(<[^>]*>|\S+)(\s.*?)?\s*$", re.DOTALL)

_DOCS_DIR = "docs"


@dataclass(frozen=True)
class PortalLinks:
    """What the portal publishes, and where a file it does not publish lives.

    ``doc_slugs`` are the published documents, ``docs/``-relative without
    ``.md``; ``page_routes`` maps a lowercased project path that has a page of
    its own (the README pair) to that page's route; ``repo_url`` is the declared
    repository, ``""`` when none is; a lowercased project path in ``withheld``
    has no destination at all, so a link to it becomes its text.
    """

    doc_slugs: frozenset[str] = frozenset()
    page_routes: Mapping[str, str] = field(default_factory=dict)
    repo_url: str = ""
    withheld: frozenset[str] = frozenset()

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

    def repository_url_of(self, path: str) -> str | None:
        """The declared repository's copy of *path*, or ``None`` with no repository."""
        if not self.repo_url:
            return None
        return f"{self.repo_url}/blob/main/{path}" if path else self.repo_url


@dataclass(frozen=True)
class _Origin:
    """Where the text came from: its file's directory, and the directory its page mirrors."""

    portal: PortalLinks
    source_dir: str
    mirrored_dir: str


def rebase_links(
    markdown: str,
    portal: PortalLinks,
    *,
    source_dir: str = "",
    mirrored_dir: str = "",
) -> str:
    """Rebase every link in *markdown* onto the portal (see the module docstring).

    ``source_dir`` is the project-relative directory of the file the text came
    from (``""`` for the project root). ``mirrored_dir`` is a project directory
    the page's own location mirrors on the portal (``"docs"`` for a published
    document), so a relative link that stays inside it is left as written.
    """
    origin = _Origin(portal, source_dir.strip("/"), mirrored_dir.strip("/"))
    text, withdrawn = _rebase_definitions(markdown, origin)
    segments = _PROTECT_RE.split(text)
    # re.split with one capture group alternates prose and protected segments.
    return "".join(
        segment if index % 2 else _rewrite_prose(segment, origin, withdrawn)
        for index, segment in enumerate(segments)
    )


def _rewrite_prose(prose: str, origin: _Origin, withdrawn: frozenset[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        return _rebase_inline(match, origin, withdrawn)

    rewritten = _LINK_RE.sub(replace, prose)
    return _withdraw_references(rewritten, withdrawn) if withdrawn else rewritten


def _rebase_inline(match: re.Match[str], origin: _Origin, withdrawn: frozenset[str]) -> str:
    bang, text, raw_target = match.group(1), match.group(2), match.group(3)
    # The badge-link idiom: the visible text is an image, rebased by the same rule.
    if "![" in text:
        text = _rewrite_prose(text, origin, withdrawn)
    url, title = _split_target(raw_target)
    destination = _destination(url, origin)
    if destination is None:
        return text
    if destination == url:
        return f"{bang}[{text}]({raw_target})"
    return f"{bang}[{text}]({destination}{title})"


def _rebase_definitions(markdown: str, origin: _Origin) -> tuple[str, frozenset[str]]:
    """Rebase every reference definition outside code; return the text and the withdrawn labels."""
    protected = [match.span() for match in _PROTECT_RE.finditer(markdown)]
    withdrawn: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        if any(start <= match.start() < end for start, end in protected):
            return match.group(0)
        indent, label, raw_url, title, newline = match.groups()
        url = raw_url[1:-1] if raw_url.startswith("<") else raw_url
        destination = _destination(url, origin)
        if destination is None:
            withdrawn.add(_label_key(label))
            return ""
        if destination == url:
            return match.group(0)
        return f"{indent}[{label}]: {destination}{title}{newline}"

    return _DEFINITION_RE.sub(replace, markdown), frozenset(withdrawn)


def _withdraw_references(prose: str, withdrawn: frozenset[str]) -> str:
    """Every reference to a withdrawn definition becomes its text (an image, its alt)."""

    def full(match: re.Match[str]) -> str:
        text, label = match.group(2), match.group(3)
        return text if _label_key(label or text) in withdrawn else match.group(0)

    def shortcut(match: re.Match[str]) -> str:
        label = match.group(2)
        return label if _label_key(label) in withdrawn else match.group(0)

    return _SHORTCUT_REFERENCE_RE.sub(shortcut, _FULL_REFERENCE_RE.sub(full, prose))


def _label_key(label: str) -> str:
    """A reference label as Markdown matches it: case-insensitive, whitespace collapsed."""
    return " ".join(label.split()).lower()


def _split_target(raw_target: str) -> tuple[str, str]:
    """The URL of an inline target and its title part (with its leading space)."""
    match = _TARGET_RE.match(raw_target)
    if match is None:
        return "", ""
    url, title = match.group(1), match.group(2) or ""
    return (url[1:-1] if url.startswith("<") else url), title


def _destination(url: str, origin: _Origin) -> str | None:
    """Where *url* goes on the portal: a URL (possibly *url* itself), or ``None`` for text."""
    if not url or url.startswith("#") or _ABSOLUTE_RE.match(url):
        return url
    cut = min((i for i in (url.find("#"), url.find("?")) if i >= 0), default=len(url))
    path, suffix = url[:cut], url[cut:]
    resolved = _resolve(path, origin.source_dir)
    if resolved is None or resolved.lower() in origin.portal.withheld:
        return None
    if origin.mirrored_dir and _is_within(resolved, origin.mirrored_dir):
        return url
    route = origin.portal.route_of(resolved)
    if route is not None:
        return route + suffix
    in_repository = origin.portal.repository_url_of(resolved)
    return None if in_repository is None else in_repository + suffix


def _resolve(path: str, source_dir: str) -> str | None:
    """*path* as a project-relative path, ``""`` for the root, ``None`` outside the project.

    A leading ``/`` is the repository root, as a forge reads it in a README.
    """
    joined = path.lstrip("/") if path.startswith("/") else posixpath.join(source_dir, path)
    normal = posixpath.normpath(joined) if joined else "."
    if normal == ".." or normal.startswith("../"):
        return None
    return "" if normal == "." else normal


def _is_within(path: str, directory: str) -> bool:
    return path == directory or path.startswith(f"{directory}/")
