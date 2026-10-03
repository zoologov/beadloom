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
links are rebased (:func:`.markdown_links.rebase_links`), and then it is read
the way VitePress reads it (:func:`.markdown_source.read_markdown`,
``beadloom-ujzb.21``) and changed only where Vue would read it:

- in text markdown-it renders, a brace pair Vue would take for an interpolation
  is broken by an empty comment, ``{<!---->{``: the page shows the two braces,
  and Vue never reads them as a delimiter. A code span holding one becomes
  ``<code v-pre>``, and an indented block holding one is wrapped in a
  ``<div v-pre>`` inside its own list item or block quote. A fenced block is left
  alone, since VitePress renders it with ``v-pre``; so is front matter.
  An entity such as ``&#123;`` is left alone too: VitePress writes it back as an
  entity, which Vue does not read as a brace.
- a link's text that markdown-it writes from an address, an autolink's
  ``<https://…>`` or a bare address VitePress links, decodes its
  percent-escapes, so it can show a brace pair its source does not. Such a link
  is written as the Markdown link it renders, ``[address](<address>)``, whose
  text is then read like any other (``beadloom-ujzb.23``, M1).
- a brace VitePress's markdown-it-attrs would read as the start of attributes
  (:mod:`.markdown_attrs`) is escaped with a backslash, which renders as the
  brace and which the plugin never reads (``beadloom-ujzb.23``, M2). An image's
  label and a container's info string, which the plugin reads as written, end
  with an empty comment instead, so they no longer end with braces.
- a fence's info string, which VitePress writes into the page as it is, holds
  ``<``, ``"`` and a brace pair as entities (``beadloom-ujzb.23``, n1).
- front matter gray-matter cannot read would fail the build where it opens a
  page, so the text then starts with a blank line, after which gray-matter finds
  no front matter, and the block is read as Markdown (``beadloom-ujzb.23``, m1).
- in raw HTML, which markdown-it passes through, markup is read as Vue's
  tokenizer reads it (:mod:`.raw_html`). A tag is kept when it is a lowercase
  element of the HTML a forge renders in a README and its partner closes it
  inside the same element markdown-it writes (a paragraph, a list item, an
  emphasis); any other tag, an unclosed comment and markup Vue cannot read are
  text. An attribute only Vue gives meaning to (``@click``, ``#slot``,
  ``.prop``) is dropped; a directive the DOM can hold (``v-if``, ``:title``) is
  shown rather than run, by ``v-pre`` on its element.
- a raw ``href``, ``src`` or ``srcset`` follows the rule of a Markdown link
  (:func:`.markdown_links.raw_html_destination`). An ``<a>`` with nowhere to go
  keeps its content, and an ``<img>`` becomes its alt text.

An edit can change how markdown-it reads the text: a line that opened an HTML
block, once escaped, is a paragraph. So the pass repeats on its own result until
it finds nothing to change. Wrapping the whole text in one ``v-pre`` was
measured and rejected: it stops the Mermaid component from mounting, and Vue
still refuses an unbalanced tag inside it. Pure and deterministic.
"""

# beadloom:domain=application

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.site.markdown_attrs import attribute_braces, ends_with_attributes
from beadloom.application.site.markdown_links import (
    PortalLinks,
    raw_html_destination,
    rebase_links,
)
from beadloom.application.site.markdown_positions import located_markdown, normalise
from beadloom.application.site.markdown_source import (
    Autolink,
    CodeBlock,
    CodeSpan,
    Edit,
    Element,
    MarkdownSource,
    RawHtml,
    RawLabel,
    Segment,
    Text,
    apply_edits,
    read_markdown,
)
from beadloom.application.site.raw_html import Markup, read_markup
from beadloom.application.site.vitepress_markdown import front_matter_is_read

if TYPE_CHECKING:
    from collections.abc import Callable

    #: Where a raw attribute's URL goes: ``(url, is_asset) -> url`` or ``None``.
    RawLink = Callable[[str, bool], "str | None"]

logger = logging.getLogger(__name__)

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
)  # fmt: skip
#: Elements with no closing tag.
_VOID = frozenset(
    ("area", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source",
     "track", "wbr")
)  # fmt: skip
#: The attributes that hold a URL, per element, and whether the URL is an asset.
_URL_ATTRS: dict[str, dict[str, bool]] = {
    "a": {"href": False},
    "img": {"src": True, "srcset": True},
    "source": {"src": True, "srcset": True},
    "video": {"src": True, "poster": True},
    "audio": {"src": True},
}
#: Attribute names only Vue gives meaning to (an event, a slot, a property binding).
_VUE_ONLY = ("@", "#", ".", "[")
#: Directive names the DOM can hold, which ``v-pre`` turns into plain attributes.
_DIRECTIVES = ("v-", ":")
_V_PRE = "v-pre"
#: An empty comment: between two braces it ends an interpolation before it starts.
_BREAK = "<!---->"
#: Characters with a meaning to VitePress's inline Markdown, escaped inside ``<code v-pre>``.
_INLINE_SPECIAL = frozenset("\\`*_[]~|:")
#: Characters a link's text would read as Markdown, escaped where an address becomes one.
_LABEL_SPECIAL = frozenset("\\`*_[]<>&!~|")
_ESCAPE = "\\"
#: A brace pair, as an interpolation Vue reads.
_PAIR = "{{"
#: The characters VitePress writes raw from a fence's info string, as entities.
_INFO_ENTITIES = (("<", "&lt;"), ('"', "&quot;"), (_PAIR, "{&#123;"))
#: A bare address VitePress's linkify turns into a link (``fuzzyLink`` is off, so a
#: scheme is needed), up to the characters that end it.
_BARE_ADDRESS_RE = re.compile(r"(?i)\b(?:https?|ftp)://[^\s<>]+")
#: Characters linkify leaves out of the end of an address.
_ADDRESS_TAIL = ".,;:!?'\")]}*_~"
#: A percent-escaped brace, which a linked address's text decodes.
_ESCAPED_BRACE = "%7b"
#: Where a text opens its page with front matter gray-matter cannot read: a blank
#: line first, after which gray-matter finds none.
_NO_FRONT_MATTER = "\n"
#: The most passes the text may need; each one only escapes, wraps or breaks.
_MAX_PASSES = 8
#: Passes in which an indented block may still be wrapped (see :meth:`_Pass._code_block`).
_WRAP_PASSES = 3


def render_project_text(
    markdown: str,
    portal: PortalLinks,
    *,
    source_dir: str = "",
    mirrored_dir: str = "",
    page_dir: str | None = None,
    opens_page: bool = True,
) -> str:
    """*markdown*, the project's own text, as a portal page shows it (module docstring).

    ``source_dir``, ``mirrored_dir`` and ``page_dir`` are
    :func:`.markdown_links.rebase_links`'s. ``opens_page`` says the text begins
    its page, so a leading front matter block is VitePress's front matter; below
    other content it is Markdown.
    """
    text = normalise(markdown)
    front_matter = opens_page
    lead = ""
    if opens_page and not front_matter_is_read(text):
        front_matter, lead = False, _NO_FRONT_MATTER
    text = rebase_links(
        text,
        portal,
        source_dir=source_dir,
        mirrored_dir=mirrored_dir,
        page_dir=page_dir,
        front_matter=front_matter,
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

    return lead + _inert(text, raw_link, front_matter=front_matter)


def _inert(text: str, raw_link: RawLink, *, front_matter: bool) -> str:
    """*text* changed until a reading of it finds nothing Vue would compile.

    Raw URLs are rebased on the first reading only: a rebased URL is an address
    on the portal, which the link rule would read again as a repository path.
    """
    for attempt in range(_MAX_PASSES):
        links = raw_link if attempt == 0 else None
        edits = _Pass(text, links, wrap=attempt < _WRAP_PASSES).run(
            read_markdown(text, front_matter=front_matter)
        )
        if not edits:
            return text
        text = apply_edits(text, edits)
    logger.warning("project text still changed after %d passes", _MAX_PASSES)
    return text


@dataclass(frozen=True)
class _Open:
    """A raw opening tag waiting for its partner, and whether Vue skips what it holds."""

    markup: Markup
    segment: Segment
    v_pre: bool


class _Pass:
    """One reading of the text: the edits that keep it out of Vue's hands.

    The stack holds the raw opening tags still waiting for a partner, and a
    ``None`` for each element markdown-it has opened: a raw tag cannot close
    across one, since the page would then nest wrongly.
    """

    def __init__(self, text: str, raw_link: RawLink | None, *, wrap: bool) -> None:
        self.text = text
        self.raw_link = raw_link
        self.wrap = wrap
        self.stack: list[_Open | None] = []
        self.edits: list[Edit] = []

    def run(self, source: MarkdownSource) -> list[Edit]:
        for part in source.parts:
            if isinstance(part, Element):
                self._element(part)
            elif isinstance(part, RawHtml):
                self._raw(part.segment)
            elif isinstance(part, Text):
                self._text(part)
            elif isinstance(part, CodeSpan):
                self._code_span(part)
            elif isinstance(part, Autolink):
                self._autolink(part)
            elif isinstance(part, RawLabel):
                self._raw_label(part)
            else:
                self._code_block(part)
        self._unwind()
        return self.edits

    @property
    def _protected(self) -> bool:
        """Whether Vue skips what comes next: an open element carries ``v-pre``."""
        return any(entry is not None and entry.v_pre for entry in self.stack)

    # -- elements markdown-it writes ----------------------------------------------

    def _element(self, part: Element) -> None:
        if part.opening:
            self.stack.append(None)
            return
        while self.stack:
            entry = self.stack.pop()
            if entry is None:
                return
            self._escape(entry.segment, entry.markup.start)

    def _unwind(self) -> None:
        for entry in self.stack:
            if entry is not None:
                self._escape(entry.segment, entry.markup.start)
        self.stack.clear()

    # -- text ---------------------------------------------------------------------

    def _text(self, part: Text) -> None:
        """Break each brace pair Vue would read, and escape each brace markdown-it-attrs would.

        A pair is any two braces markdown-it renders adjacent: ``{{``, ``{\\{``. An
        address whose linked text decodes a brace is rewritten whole, and the next
        reading treats its text.
        """
        segment, text = part.segment, part.segment.text
        rewritten = [] if self._protected else self._decoded_addresses(segment)
        escapes = set(
            attribute_braces(text, opens=part.opens, closes=part.closes, alone=part.alone)
        )
        for index in range(len(text)):
            if any(start <= index < end for start, end in rewritten):
                continue
            inserted = ""
            if not self._protected and _closes_pair(text, index):
                inserted += _BREAK
            if index in escapes:
                inserted += _ESCAPE
            if inserted:
                self._insert(segment.source(index), inserted)

    def _decoded_addresses(self, segment: Segment) -> list[tuple[int, int]]:
        """Bare addresses whose linked text decodes a brace pair, each written as a link."""
        rewritten: list[tuple[int, int]] = []
        for match in _BARE_ADDRESS_RE.finditer(segment.text):
            address = match.group(0).rstrip(_ADDRESS_TAIL)
            if _ESCAPED_BRACE not in address.lower():
                continue
            label = located_markdown().normalizeLinkText(address)
            if _PAIR not in label:
                continue
            start, end = match.start(), match.start() + len(address)
            self._replace(segment, start, end, _markdown_link(label, address))
            rewritten.append((start, end))
        return rewritten

    def _autolink(self, part: Autolink) -> None:
        """An autolink whose text shows a brace pair: written as the link it renders."""
        if _PAIR in part.label and not self._protected:
            self.edits.append(
                Edit(part.start, part.end, _markdown_link(part.label, part.destination))
            )

    def _raw_label(self, part: RawLabel) -> None:
        """An empty comment after a label markdown-it-attrs would read as attributes.

        The plugin reads an image's label or a container's info string as written,
        so an escape inside it does not hide a brace; ending with a comment does.
        """
        if not ends_with_attributes(part.label):
            return
        if self.text[part.end : part.end + len(_BREAK)] != _BREAK:
            self._insert(part.end, _BREAK)

    def _raw_text(self, segment: Segment, start: int, end: int) -> None:
        """Break every ``{{`` in raw HTML's text, which Vue reads as written."""
        if self._protected:
            return
        for index in range(start, end - 1):
            if segment.text[index] == "{" and segment.text[index + 1] == "{":
                self._insert(segment.source(index + 1), _BREAK)

    # -- code -----------------------------------------------------------------------

    def _code_span(self, part: CodeSpan) -> None:
        if "{{" not in part.content or self._protected:
            return
        self.edits.append(
            Edit(part.start, part.end, f"<code v-pre>{_inline_code(part.content)}</code>")
        )

    def _code_block(self, part: CodeBlock) -> None:
        """Wrap an indented block holding ``{{`` in ``<div v-pre>``, inside its containers.

        A wrapper that did not take (a container this reading cannot continue)
        would be wrapped again on every pass; after a few, each brace pair in the
        block is split by a zero-width space instead, which no reading can undo.
        """
        if part.kind == "fence":
            self._fence_info(part)
            return
        if "{{" not in part.content or self._protected:
            return
        if not self.wrap:
            block = self.text[part.start : part.end]
            for index in range(len(block) - 1):
                if block[index] == "{" and block[index + 1] == "{":
                    self._insert(part.start + index + 1, "\u200b")
            return
        blank = (part.resume or part.continuation).rstrip()
        if part.resume:
            opening = f"{part.lead}<div {_V_PRE}>\n{blank}\n{part.resume}"
        else:
            opening = f"{part.continuation}<div {_V_PRE}>\n{blank}\n"
        self._insert(part.insert_at, opening)
        closing_blank = part.continuation.rstrip()
        closing = f"{closing_blank}\n{part.continuation}</div>\n{closing_blank}\n"
        self._insert(part.end, closing)

    def _fence_info(self, part: CodeBlock) -> None:
        """A fence's info string with what VitePress would write raw held as entities."""
        if part.info is None:
            return
        start, end = part.info
        info = self.text[start:end]
        shown = info
        for raw, entity in _INFO_ENTITIES:
            shown = shown.replace(raw, entity)
        if shown != info:
            self.edits.append(Edit(start, end, shown))

    # -- raw HTML ---------------------------------------------------------------------

    def _raw(self, segment: Segment) -> None:
        cursor = 0
        for markup in read_markup(segment.text):
            self._raw_text(segment, cursor, markup.start)
            cursor = markup.end
            if markup.kind == "unreadable":
                self._escape(segment, markup.start)
            elif markup.kind == "open":
                self._open(segment, markup)
            elif markup.kind == "close":
                self._close(segment, markup)
        self._raw_text(segment, cursor, len(segment.text))

    def _open(self, segment: Segment, markup: Markup) -> None:
        if markup.name not in _KEPT:
            self._escape(segment, markup.start)
            return
        names = [attribute.name.lower() for attribute in markup.attributes]
        v_pre = any(name == _V_PRE or name.startswith(_DIRECTIVES) for name in names)
        entry = _Open(markup, segment, v_pre)
        if markup.self_closing or markup.name in _VOID:
            self._keep(entry, None)
        else:
            self.stack.append(entry)

    def _close(self, segment: Segment, markup: Markup) -> None:
        if markup.name in _KEPT and markup.name not in _VOID:
            for index in range(len(self.stack) - 1, -1, -1):
                entry = self.stack[index]
                if entry is None:
                    break
                if entry.markup.name == markup.name:
                    for unclosed in self.stack[index + 1 :]:
                        if unclosed is not None:
                            self._escape(unclosed.segment, unclosed.markup.start)
                    del self.stack[index:]
                    self._keep(entry, (segment, markup))
                    return
        self._escape(segment, markup.start)

    def _keep(self, entry: _Open, closing: tuple[Segment, Markup] | None) -> None:
        """A kept element: URLs rebased, Vue-only attributes dropped, directives shown, not run."""
        markup, segment = entry.markup, entry.segment
        if self.raw_link is not None and self._withdrawn(entry, closing, self.raw_link):
            return
        directive = False
        for attribute in markup.attributes:
            name = attribute.name.lower()
            if name.startswith(_VUE_ONLY):
                self._replace(segment, attribute.start, attribute.end, "")
                continue
            directive = directive or (name.startswith(_DIRECTIVES) and name != _V_PRE)
            asset = _URL_ATTRS.get(markup.name, {}).get(name)
            if asset is None or attribute.value is None or self.raw_link is None:
                continue
            rebased = _rebase_url_attr(name, attribute.value, asset, self.raw_link)
            if rebased is None:
                self._replace(segment, attribute.start, attribute.end, "")
            elif rebased != attribute.value:
                lead = segment.text[attribute.start : attribute.name_start]
                written = f'{lead}{attribute.name}="{html.escape(rebased)}"'
                self._replace(segment, attribute.start, attribute.end, written)
        if directive and _V_PRE not in {attribute.name.lower() for attribute in markup.attributes}:
            self._insert(segment.source(markup.attributes_end), f" {_V_PRE}")

    def _withdrawn(
        self, entry: _Open, closing: tuple[Segment, Markup] | None, raw_link: RawLink
    ) -> bool:
        """An ``<a>`` with nowhere to go keeps its content; such an ``<img>`` becomes its alt."""
        markup, segment = entry.markup, entry.segment
        if markup.name == "a":
            href = _value(markup, "href")
            if href is None or raw_link(href, False) is not None:
                return False
            self._replace(segment, markup.start, markup.end, "")
            if closing is not None:
                self._replace(closing[0], closing[1].start, closing[1].end, "")
            return True
        if markup.name == "img":
            src = _value(markup, "src")
            if src is None or raw_link(src, True) is not None:
                return False
            alt = (_value(markup, "alt") or "").replace("<", "&lt;")
            self._replace(segment, markup.start, markup.end, alt)
            return True
        return False

    # -- edits ----------------------------------------------------------------------

    def _escape(self, segment: Segment, index: int) -> None:
        """The ``<`` at *index* as text."""
        start = segment.source(index)
        self.edits.append(Edit(start, start + 1, "&lt;"))

    def _insert(self, at: int, text: str) -> None:
        self.edits.append(Edit(at, at, text))

    def _replace(self, segment: Segment, start: int, end: int, text: str) -> None:
        """Replace ``segment.text[start:end]``, line by line: each line keeps its own prefix."""
        pieces = segment.pieces(start, end)
        if not pieces:
            self._insert(segment.source(start), text)
            return
        first, *rest = pieces
        self.edits.append(Edit(first[0], first[1], text))
        self.edits.extend(Edit(piece_start, piece_end, "") for piece_start, piece_end in rest)


def _value(markup: Markup, name: str) -> str | None:
    """The value of the attribute *name*, ``""`` when it has none, ``None`` when it is absent."""
    for attribute in markup.attributes:
        if attribute.name.lower() == name:
            return attribute.value or ""
    return None


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


def _closes_pair(text: str, index: int) -> bool:
    """Whether the brace at *index*, or an escaped one there, renders beside the ``{`` before."""
    if index == 0 or text[index - 1] != "{":
        return False
    return text[index] == "{" or text[index : index + 2] == "\\{"


def _markdown_link(label: str, destination: str) -> str:
    """``[label](<destination>)``: *label* shown as written, *destination* linked as it is."""
    shown = "".join(f"{_ESCAPE}{char}" if char in _LABEL_SPECIAL else char for char in label)
    return f"[{shown}](<{destination.replace(_ESCAPE, _ESCAPE * 2)}>)"


def _inline_code(content: str) -> str:
    """A code span's content inside ``<code v-pre>``: no character read as Markdown or HTML."""
    escaped = html.escape(content, quote=False)
    return "".join(f"\\{char}" if char in _INLINE_SPECIAL else char for char in escaped)
