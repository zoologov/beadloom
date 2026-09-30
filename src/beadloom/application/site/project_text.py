# beadloom:domain=application
# beadloom:feature=site-generation
"""A project's own Markdown as a portal page shows it: the author's text, never a Vue template.

VitePress compiles every Markdown page as a Vue template, and the generator puts
the project's own text on portal pages: the README on the About page, a node's
summary on its node page, every document under ``docs/`` in the published
documentation. Measured on VitePress 1.6.4 (BDL-076, ``beadloom-ujzb.12``): a
Helm value ``{{ .Values.image.tag }}`` in that text failed ``vitepress build``,
``{{ name }}`` rendered as nothing and ``{{ 1 + 1 }}`` as ``2``, in prose and in
inline code alike; ``List<String>``, an unclosed ``<details>`` and a ``<script>``
failed the build; a ``<style>`` restyled the whole page.

:func:`render_project_text` is the one path that text takes onto a page. Its
links are rebased (:func:`.markdown_links.rebase_links`), and then:

- an interpolation is wrapped in ``<span v-pre>``, which VitePress documents for
  exactly this: Vue leaves the element's content as it is. A code span holding
  one becomes ``<code v-pre>``, and an indented block holding one is wrapped in a
  ``<div v-pre>``. A fenced block is left alone, since VitePress already renders
  it with ``v-pre``; so is YAML front matter.
- a tag is kept when Vue compiles it as the HTML the author meant: a lowercase
  element of the HTML a forge renders in a README, balanced by its closing tag.
  An inline element closes in its own paragraph; a block element may close in a
  later one, on a line of its own. A Vue directive on a kept element
  (``v-if``, ``:title``) is shown rather than run, by ``v-pre`` on the element.
- any other tag is text: a name that is not such an element (``List<String>``,
  ``<MyWidget />``), an element that would run or restyle the page (``<script>``,
  ``<style>``), an element with no partner.
- a raw ``href``, ``src`` or ``srcset`` follows the rule of a Markdown link
  (:func:`.markdown_links.raw_html_destination`). An ``<a>`` with nowhere to go
  keeps its content, and an ``<img>`` becomes its alt text.

Wrapping the whole text in one ``v-pre`` was measured and rejected: it stops the
Mermaid component from mounting, so a diagram in a published document shows as
literal ``<Mermaid>`` markup, and Vue still refuses an unbalanced tag inside it.
Pure and deterministic.
"""

# beadloom:domain=application

from __future__ import annotations

import bisect
import html
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.site.markdown_code import (
    CodeRegion,
    block_breaks,
    code_regions,
    is_escaped,
)
from beadloom.application.site.markdown_links import (
    PortalLinks,
    raw_html_destination,
    rebase_links,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    #: Where a raw attribute's URL goes: ``(url, is_asset) -> url`` or ``None``.
    RawLink = Callable[[str, bool], "str | None"]

#: The elements a forge renders in a README, and so the ones kept as HTML.
_KEPT = frozenset(
    (
        "a", "abbr", "audio", "b", "bdi", "bdo", "blockquote", "br", "caption", "center", "cite",
        "code", "col", "colgroup", "dd", "del", "details", "dfn", "div", "dl", "dt", "em",
        "figcaption", "figure", "font", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img",
        "ins", "kbd", "li", "mark", "ol", "p", "picture", "pre", "q", "rp", "rt", "ruby", "s",
        "samp", "small", "source", "span", "strike", "strong", "sub", "summary", "sup", "table",
        "tbody", "td", "tfoot", "th", "thead", "time", "tr", "track", "tt", "u", "ul", "var",
        "video", "wbr"
    )
)
#: Elements with no closing tag.
_VOID = frozenset(
    (
        "area", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source",
        "track", "wbr"
    )
)
#: Elements that open an HTML block on a line of their own (CommonMark's type 6).
_BLOCK = frozenset(
    (
        "address", "article", "aside", "blockquote", "body", "caption", "center", "col",
        "colgroup", "dd", "details", "dialog", "dir", "div", "dl", "dt", "fieldset", "figcaption",
        "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "html",
        "legend", "li", "main", "menu", "nav", "ol", "p", "section", "summary", "table", "tbody",
        "td", "tfoot", "th", "thead", "tr", "ul"
    )
)
#: The attributes that hold a URL, per element, and whether the URL is an asset.
_URL_ATTRS: dict[str, dict[str, bool]] = {
    "a": {"href": False},
    "img": {"src": True, "srcset": True},
    "source": {"src": True, "srcset": True},
    "video": {"src": True, "poster": True},
    "audio": {"src": True},
}
#: The most indentation a line may carry and still open an HTML block.
_BLOCK_INDENT = 3

_ATTR = r"""\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"'=<>`]+|'[^']*'|"[^"]*"))?"""
# An HTML comment, an opening tag or a closing tag, as CommonMark recognises them.
_TAG_RE = re.compile(
    rf"(?P<comment><!--.*?-->)"
    rf"|<(?P<name>[A-Za-z][A-Za-z0-9-]*)(?P<attrs>(?:{_ATTR})*)(?P<tail>\s*/?>)"
    rf"|</(?P<close>[A-Za-z][A-Za-z0-9-]*)\s*>",
    re.DOTALL,
)
_ATTR_RE = re.compile(
    r"""(?P<lead>\s+)(?P<name>[A-Za-z_:][A-Za-z0-9_.:-]*)"""
    r"""(?:\s*=\s*(?P<value>[^\s"'=<>`]+|'[^']*'|"[^"]*"))?"""
)
# An opening brace as Markdown may write it: bare, backslash-escaped, or an entity.
_BRACE = r"(?:\\?\{|&(?:#123|#[xX]0*7[bB]|lbrace|lcub);)"
# An interpolation: two opening braces, through the first "}}" on the same line.
_MUSTACHE_RE = re.compile(rf"{_BRACE}{_BRACE}(?:[^\n]*?\}}\}})?")
_BLOCK_CODE = frozenset({"frontmatter", "fence", "indented"})


@dataclass
class _Tag:
    """One tag in the prose, and what becomes of it: ``keep``, ``text``, ``drop``.

    An HTML comment is read as a tag whose fate is ``comment``: it is left as written.
    """

    start: int
    end: int
    name: str
    closing: bool
    attrs: str
    tail: str
    chunk: int
    block: bool
    fate: str = "keep"

    @property
    def pairs(self) -> bool:
        """Whether the tag needs a partner: an opening or closing tag of a non-void element."""
        return self.fate == "keep" and self.name not in _VOID and "/" not in self.tail


def render_project_text(
    markdown: str,
    portal: PortalLinks,
    *,
    source_dir: str = "",
    mirrored_dir: str = "",
    page_dir: str | None = None,
) -> str:
    """*markdown*, the project's own text, as a portal page shows it (module docstring).

    ``source_dir``, ``mirrored_dir`` and ``page_dir`` are
    :func:`.markdown_links.rebase_links`'s.
    """
    text = rebase_links(
        markdown, portal, source_dir=source_dir, mirrored_dir=mirrored_dir, page_dir=page_dir
    )

    def raw_link(url: str, asset: bool) -> str | None:
        return raw_html_destination(
            url,
            portal,
            source_dir=source_dir,
            mirrored_dir=mirrored_dir,
            page_dir=page_dir,
            asset=asset,
        )

    return _inert(text, raw_link)


def _inert(text: str, raw_link: RawLink) -> str:
    regions = code_regions(text)
    tags = _read_tags(text, regions)
    _balance([tag for tag in tags if tag.pairs])
    _withdraw_links(tags, raw_link)
    edits = [(r.start, r.end, _render_code(text[r.start : r.end], r.kind)) for r in regions]
    edits += [(t.start, t.end, _render_tag(t, text, raw_link)) for t in tags]
    parts: list[str] = []
    cursor = 0
    for start, end, replacement in sorted(edits):
        parts.extend((_wrap_mustaches(text[cursor:start]), replacement))
        cursor = end
    parts.append(_wrap_mustaches(text[cursor:]))
    return "".join(parts)


# -- reading the tags ---------------------------------------------------------


def _read_tags(text: str, regions: list[CodeRegion]) -> list[_Tag]:
    """Every tag and comment in the prose between *regions*, in order."""
    breaks = _paragraph_breaks(text, regions)
    gaps = zip(
        [0, *(r.end for r in regions)], [*(r.start for r in regions), len(text)], strict=True
    )
    tags: list[_Tag] = []
    for start, end in gaps:
        for match in _TAG_RE.finditer(text, start, end):
            if match["comment"] is not None:
                tags.append(_comment(match))
            elif not is_escaped(text, match.start()):
                tags.append(_tag_of(match, text, breaks))
    return tags


def _comment(match: re.Match[str]) -> _Tag:
    return _Tag(match.start(), match.end(), "", False, "", "", 0, False, fate="comment")


def _paragraph_breaks(text: str, regions: list[CodeRegion]) -> list[int]:
    """Positions where a paragraph ends: a new block, and both edges of a block of code."""
    breaks = set(block_breaks(text))
    for region in regions:
        if region.kind in _BLOCK_CODE:
            breaks.update((region.start, region.end))
    return sorted(breaks)


def _tag_of(match: re.Match[str], text: str, breaks: list[int]) -> _Tag:
    closing = match["close"] is not None
    name = match["close"] if closing else match["name"]
    chunk = bisect.bisect_right(breaks, match.start())
    tag = _Tag(
        start=match.start(),
        end=match.end(),
        name=name,
        closing=closing,
        attrs=match["attrs"] or "",
        tail=match["tail"] or ">",
        chunk=chunk,
        block=_opens_a_block(text, match, name, breaks[chunk - 1] if chunk else 0),
    )
    if name not in _KEPT:
        tag.fate = "text"
    return tag


def _opens_a_block(text: str, match: re.Match[str], name: str, paragraph_start: int) -> bool:
    """Whether the tag stands where CommonMark opens an HTML block with it.

    A block element's tag at the start of a line opens one anywhere; any other
    element's does only on the first line of a paragraph, alone on its line.
    """
    line_start = text.rfind("\n", 0, match.start()) + 1
    indent = text[line_start : match.start()]
    if indent.strip(" ") or len(indent) > _BLOCK_INDENT:
        return False
    if name.lower() in _BLOCK:
        return True
    line_end = text.find("\n", match.end())
    alone = not text[match.end() : line_end if line_end >= 0 else len(text)].strip()
    return alone and not text[paragraph_start:line_start].strip()


def _balance(tags: list[_Tag]) -> None:
    """Pair every opening tag with its closing tag; a tag left without one is text."""
    stack: list[_Tag] = []
    for tag in tags:
        for opened in [o for o in stack if o.chunk < tag.chunk and not o.block]:
            opened.fate = "text"
            stack.remove(opened)
        if not tag.closing:
            stack.append(tag)
            continue
        index = next((i for i in range(len(stack) - 1, -1, -1) if stack[i].name == tag.name), None)
        if index is None or (stack[index].chunk != tag.chunk and not tag.block):
            tag.fate = "text"
            continue
        for unclosed in stack[index + 1 :]:
            unclosed.fate = "text"
        del stack[index:]
    for unclosed in stack:
        unclosed.fate = "text"


def _withdraw_links(tags: list[_Tag], raw_link: RawLink) -> None:
    """An ``<a>`` whose address has nowhere to go loses its tags and keeps its content.

    After :func:`_balance` the kept ``<a>`` tags nest properly, so a closing tag
    shares the fate of the latest opening tag still open.
    """
    depth: list[_Tag] = []
    for tag in tags:
        if tag.name != "a" or tag.fate != "keep":
            continue
        if not tag.closing:
            href = _attribute(tag.attrs, "href")
            withdrawn = href is not None and raw_link(href, False) is None
            tag.fate = "drop" if withdrawn else "keep"
            depth.append(tag)
        elif depth:
            tag.fate = depth.pop().fate


# -- writing the page ---------------------------------------------------------


def _render_tag(tag: _Tag, text: str, raw_link: RawLink) -> str:
    original = text[tag.start : tag.end]
    if tag.fate == "comment":
        return original
    if tag.fate == "drop":
        return ""
    if tag.fate == "text":
        return "&lt;" + _wrap_mustaches(original[1:])
    if tag.closing:
        return original
    return _render_kept(tag, raw_link)


def _render_kept(tag: _Tag, raw_link: RawLink) -> str:
    """A kept opening tag, its URLs rebased and its directives shown rather than run."""
    url_attrs = _URL_ATTRS.get(tag.name, {})
    attrs: list[str] = []
    directive = False
    for match in _ATTR_RE.finditer(tag.attrs):
        name = match["name"].lower()
        directive = directive or (name.startswith((":", "v-")) and name != "v-pre")
        value = _unquote(match["value"])
        if name not in url_attrs or value is None:
            attrs.append(match.group(0))
            continue
        rebased = _rebase_url_attr(name, value, url_attrs[name], raw_link)
        if rebased is None and tag.name == "img" and name == "src":
            alt = _attribute(tag.attrs, "alt") or ""
            return _wrap_mustaches(alt.replace("<", "&lt;"))
        if rebased == value:
            attrs.append(match.group(0))
        elif rebased is not None:
            attrs.append(f'{match["lead"]}{match["name"]}="{html.escape(rebased)}"')
    if directive and _attribute(tag.attrs, "v-pre") is None:
        attrs.append(" v-pre")
    return f"<{tag.name}{''.join(attrs)}{tag.tail}"


def _rebase_url_attr(name: str, value: str, asset: bool, raw_link: RawLink) -> str | None:
    """The attribute's value with every URL rebased, or ``None`` when one has nowhere to go."""
    if name != "srcset":
        return raw_link(value, asset)
    candidates: list[str] = []
    for candidate in value.split(","):
        url, _, descriptor = candidate.strip().partition(" ")
        rebased = raw_link(url, asset)
        if rebased is None:
            return None
        candidates.append(f"{rebased} {descriptor}".rstrip())
    rewritten = ", ".join(candidates)
    return value if rewritten == ", ".join(c.strip() for c in value.split(",")) else rewritten


def _attribute(attrs: str, wanted: str) -> str | None:
    """The unquoted value of the attribute *wanted*, ``""`` when it has none, else ``None``."""
    for match in _ATTR_RE.finditer(attrs):
        if match["name"].lower() == wanted:
            return _unquote(match["value"]) or ""
    return None


def _unquote(value: str | None) -> str | None:
    if value is not None and value[:1] in {'"', "'"}:
        return value[1:-1]
    return value


def _render_code(code: str, kind: str) -> str:
    """A code region, left as written unless Vue would read an interpolation in it."""
    if "{{" not in code or kind in {"frontmatter", "fence"}:
        return code
    if kind == "indented":
        block = code if code.endswith("\n") else f"{code}\n"
        return f"<div v-pre>\n\n{block}\n</div>\n\n"
    return f"<code v-pre>{html.escape(_code_span_content(code), quote=False)}</code>"


def _code_span_content(span: str) -> str:
    """A code span's content as CommonMark reads it: line endings as spaces, one pad stripped."""
    ticks = len(span) - len(span.lstrip("`"))
    content = span[ticks:-ticks].replace("\n", " ")
    if content.startswith(" ") and content.endswith(" ") and content.strip():
        content = content[1:-1]
    return content


def _wrap_mustaches(prose: str) -> str:
    """Every interpolation in *prose* inside ``<span v-pre>``, so Vue leaves it as written."""
    return _MUSTACHE_RE.sub(lambda match: f"<span v-pre>{match.group(0)}</span>", prose)
