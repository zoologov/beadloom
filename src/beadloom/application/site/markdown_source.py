# beadloom:domain=application
# beadloom:feature=site-generation
"""A project's Markdown as VitePress reads it, each construct located in the source text.

Two passes change a project's own text on its way onto a portal page: its links
are rebased (:mod:`.markdown_links`) and it is made inert to Vue's template
compiler (:mod:`.project_text`). Both must change the text exactly where
VitePress reads a link, a code span or raw HTML, and nowhere else, so both read
it through :func:`read_markdown`: markdown-it-py configured as VitePress
configures markdown-it (:mod:`.vitepress_markdown`), with every token located in
the source (:mod:`.markdown_positions`). BDL-076, ``beadloom-ujzb.21``, which
replaced a hand-written reader that disagreed with markdown-it in six classes.

The reading is offered three ways:

- :attr:`MarkdownSource.parts`: what VitePress writes into the page, in order,
  as a Vue template sees it: the elements markdown-it writes, raw HTML, text,
  code spans and code blocks;
- :attr:`MarkdownSource.links` and :attr:`MarkdownSource.definitions`: every
  link and image markdown-it renders, and every reference definition;
- :attr:`MarkdownSource.code`: which characters are code.

Front matter is read the way gray-matter reads it, and only when the text opens
its page (``front_matter=True``); below other content it is Markdown like any
other line.
"""

# beadloom:domain=application

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.site.markdown_positions import located_markdown, normalise
from beadloom.application.site.vitepress_markdown import TITLED_CONTAINERS, front_matter_length

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from markdown_it.token import Token

#: A source range: start and end offsets.
Span = tuple[int, int]


@dataclass(frozen=True)
class Segment:
    """Text as markdown-it read it, and the source offset of each of its characters.

    ``origins`` holds one offset per character and one more for the end. A
    segment cut out of quoted or indented lines is not contiguous in the source:
    each of its lines sits behind that line's own prefix.
    """

    text: str
    origins: tuple[int, ...]

    def source(self, index: int) -> int:
        """The source offset of the character at *index* (``len(text)`` for the end)."""
        return self.origins[index]

    def pieces(self, start: int, end: int) -> tuple[Span, ...]:
        """The source ranges ``text[start:end]`` occupies, one per line it crosses."""
        pieces: list[Span] = []
        cursor = start
        while cursor < end:
            newline = self.text.find("\n", cursor, end)
            stop = end if newline < 0 else newline
            if stop > cursor:
                pieces.append((self.origins[cursor], self.origins[stop - 1] + 1))
            cursor = stop + 1
        return tuple(pieces)

    def slice(self, start: int, end: int) -> Segment:
        end_origin = self.origins[end - 1] + 1 if end > start else self.origins[start]
        return Segment(self.text[start:end], (*self.origins[start:end], end_origin))


# -- what a Vue template sees, in order ------------------------------------------


@dataclass(frozen=True)
class Element:
    """An element markdown-it writes around content: a paragraph, a list item, an emphasis."""

    opening: bool


@dataclass(frozen=True)
class RawHtml:
    """HTML markdown-it passes through as written, which Vue reads as template."""

    segment: Segment


@dataclass(frozen=True)
class Text:
    """Text markdown-it renders as an element's content, which Vue reads for ``{{ }}``.

    ``segment`` is Markdown: a backslash escapes the character after it. Where it
    sits in its inline token is what markdown-it-attrs reads (:mod:`.markdown_attrs`):
    ``opens`` and ``closes`` say it starts and ends the inline token, and ``alone``
    that the inline is a paragraph right after a table or a list.
    """

    segment: Segment
    opens: bool = False
    closes: bool = False
    alone: bool = False


@dataclass(frozen=True)
class CodeSpan:
    """A code span, and its content as markdown-it renders it."""

    start: int
    end: int
    content: str


@dataclass(frozen=True)
class CodeBlock:
    """A fenced or an indented code block, whole lines from ``start`` to ``end``.

    For an indented block, which VitePress renders without ``v-pre``,
    ``insert_at`` is where a line can be inserted before it and still sit in its
    containers, ``continuation`` begins any new line inside them, and ``resume``
    is what the rest of the block's first line needs once a line break is
    inserted at ``insert_at`` (empty when ``insert_at`` starts a line), and
    ``lead`` what goes between ``insert_at`` and an inserted line's own text. For
    a fence, ``info`` is the source span of its info string, which VitePress
    writes into the page as it is.
    """

    kind: str
    start: int
    end: int
    content: str
    insert_at: int = 0
    continuation: str = ""
    resume: str = ""
    lead: str = ""
    info: Span | None = None


@dataclass(frozen=True)
class Autolink:
    """An autolink, ``<address>``, from ``start`` to ``end``.

    ``label`` is the text markdown-it renders for it, the address with its
    percent-escapes decoded, and ``destination`` the address it links to.
    """

    start: int
    end: int
    label: str
    destination: str


@dataclass(frozen=True)
class RawLabel:
    """Text markdown-it-attrs reads as written, escapes included, ending at ``end``.

    An image's label (the image token's content) and a container's info string,
    which the plugin's fence pattern reads on any block token that has one.
    """

    end: int
    label: str


Part = Element | RawHtml | Text | CodeSpan | CodeBlock | Autolink | RawLabel


# -- links and definitions --------------------------------------------------------


@dataclass(frozen=True)
class Link:
    """A link or an image markdown-it renders.

    ``opener`` is ``[`` (``![`` for an image) and ``tail`` is everything after the
    label: removing both leaves the label as written. ``destination`` is the span
    of an inline destination; a reference link names its definition's
    ``reference`` label instead.
    """

    image: bool
    opener: Span
    tail: tuple[Span, ...]
    destination: Span | None
    reference: str | None


@dataclass(frozen=True)
class Definition:
    """A reference definition: its label, its destination, and the lines it fills.

    ``lines`` is the whole lines, from their start to past their newline, and
    ``pieces`` the definition's own text on them, without any container prefix.
    """

    reference: str
    destination: Span
    lines: Span
    pieces: tuple[Span, ...]


@dataclass(frozen=True)
class CodeRegion:
    """A run of code: ``frontmatter``, ``fence``, ``indented`` or ``code_span``."""

    start: int
    end: int
    kind: str


@dataclass(frozen=True)
class MarkdownSource:
    """One reading of a Markdown text (module docstring)."""

    parts: tuple[Part, ...]
    links: tuple[Link, ...]
    definitions: tuple[Definition, ...]
    code: tuple[CodeRegion, ...]


def read_markdown(text: str, *, front_matter: bool = True) -> MarkdownSource:
    """*text*, already normalised (:func:`.markdown_positions.normalise`), as VitePress reads it.

    With *front_matter*, a leading block gray-matter takes as front matter is
    not Markdown; VitePress cuts it off before markdown-it runs.
    """
    if normalise(text) != text:
        raise ValueError("read_markdown needs text normalised as markdown-it normalises it")
    head = front_matter_length(text) if front_matter else 0
    reader = _Reader(text, head)
    reader.read(located_markdown().parse(text[head:], reader.env))
    return reader.result()


@dataclass(frozen=True)
class Edit:
    """Replace the source from ``start`` to ``end`` with ``text`` (an insertion when they meet)."""

    start: int
    end: int
    text: str


def apply_edits(source: str, edits: Iterable[Edit]) -> str:
    """*source* with every edit made; edits must not overlap."""
    parts: list[str] = []
    cursor = 0
    for edit in sorted(edits, key=lambda e: (e.start, e.end)):
        if edit.start < cursor:
            raise ValueError(f"overlapping edits at {edit.start}")
        parts.extend((source[cursor : edit.start], edit.text))
        cursor = edit.end
    parts.append(source[cursor:])
    return "".join(parts)


def offset(segment: Segment, base: int) -> Segment:
    """*segment* with every origin moved by *base*."""
    return Segment(segment.text, tuple(origin + base for origin in segment.origins))


# -- the reader -------------------------------------------------------------------


class _Reader:
    """Walks the token stream once and collects every located construct."""

    def __init__(self, text: str, head: int) -> None:
        self.text = text
        self.head = head
        self.env: dict[str, object] = {}
        self.line_starts = _line_starts(text[head:])
        self.parts: list[Part] = []
        self.links: list[Link] = []
        self.definitions: list[Definition] = []
        self.code: list[CodeRegion] = []
        self.alone = False
        if head:
            self.code.append(CodeRegion(0, head, "frontmatter"))

    def result(self) -> MarkdownSource:
        return MarkdownSource(
            parts=tuple(self.parts),
            links=tuple(self.links),
            definitions=tuple(self.definitions),
            code=tuple(sorted(self.code, key=lambda region: region.start)),
        )

    def read(self, tokens: Sequence[Token]) -> None:
        for index, token in enumerate(tokens):
            self.alone = index >= _ALONE_AFTER and _follows_a_list_or_table(tokens, index)
            self._block(token)

    def _block(self, token: Token) -> None:
        if token.type == "inline" or (token.type == "html_inline" and token.map is not None):
            if token.type == "html_inline":
                self.parts.append(RawHtml(self._segment(token)))
                return
            self._inline(self._segment(token), token.children or [], alone=self.alone)
        elif token.type == "html_block":
            self.parts.append(RawHtml(self._segment(token)))
        elif token.type in {"fence", "code_block"}:
            self._code_block(token)
        elif token.type == "definition":
            self._definition(token)
        elif token.nesting and not token.hidden:
            self.parts.append(Element(opening=token.nesting > 0))
            self._container_info(token)
            self._container_title(token)

    def _segment(self, token: Token) -> Segment:
        return offset(Segment(token.content, token.meta["origins"]), self.head)

    def _lines(self, token: Token) -> Span:
        first, last = token.map or (0, 0)
        return (self.head + self.line_starts[first], self.head + self.line_starts[last])

    def _code_block(self, token: Token) -> None:
        start, end = self._lines(token)
        if token.type == "fence":
            info_start, info_end = token.meta["info"]
            info = (self.head + info_start, self.head + info_end)
            self.parts.append(CodeBlock("fence", start, end, token.content, info=info))
            self.code.append(CodeRegion(start, end, "fence"))
            return
        self.parts.append(
            CodeBlock(
                "indented",
                start,
                end,
                token.content,
                insert_at=self.head + token.meta["insert_at"],
                continuation=token.meta["continuation"],
                resume=token.meta["resume"],
                lead=token.meta["lead"],
            )
        )
        self.code.append(CodeRegion(start, end, "indented"))

    def _definition(self, token: Token) -> None:
        segment = self._segment(token)
        start, end = token.meta["destination"]
        self.definitions.append(
            Definition(
                reference=token.meta["reference"],
                destination=(segment.source(start), segment.source(end)),
                lines=self._lines(token),
                pieces=segment.pieces(0, len(segment.text)),
            )
        )

    def _container_info(self, token: Token) -> None:
        info_end = token.meta.get("info_end")
        if info_end is not None:
            self.parts.append(RawLabel(self.head + info_end, token.info))

    def _container_title(self, token: Token) -> None:
        title = token.meta.get("title")
        name = token.type.removeprefix("container_").removesuffix("_open")
        if title is None or name not in TITLED_CONTAINERS or not title[0]:
            return
        segment = offset(Segment(*title), self.head)
        children = located_markdown().parseInline(segment.text, self.env)[0].children or []
        self.parts.append(Element(opening=True))
        self._inline(segment, children)
        self.parts.append(Element(opening=False))

    def _inline(
        self, segment: Segment, children: Sequence[Token], *, alone: bool = False
    ) -> None:
        """The parts of one inline token, in order: text runs between located children."""
        walk = _InlineWalk(segment, self, alone=alone)
        for child in children:
            walk.child(child)
        walk.text_until(len(segment.text))


class _InlineWalk:
    """One inline token's children, turned into parts and links."""

    def __init__(self, segment: Segment, reader: _Reader, *, alone: bool) -> None:
        self.segment = segment
        self.reader = reader
        self.alone = alone
        self.cursor = 0
        self.open_links: list[tuple[int, int] | None] = []

    def text_until(self, position: int) -> None:
        if position > self.cursor:
            self.reader.parts.append(
                Text(
                    self.segment.slice(self.cursor, position),
                    opens=self.cursor == 0,
                    closes=position == len(self.segment.text),
                    alone=self.alone,
                )
            )
        self.cursor = max(self.cursor, position)

    def child(self, child: Token) -> None:
        span = child.meta.get("span")
        if child.type == "html_inline" and span:
            self.text_until(span[0])
            self.reader.parts.append(RawHtml(self.segment.slice(*span)))
            self.cursor = span[1]
        elif child.type == "code_inline" and span:
            self.text_until(span[0])
            start, end = self.segment.source(span[0]), self.segment.source(span[1])
            self.reader.parts.append(CodeSpan(start, end, child.content))
            self.reader.code.append(CodeRegion(start, end, "code_span"))
            self.cursor = span[1]
        elif child.type == "image" and span:
            self.text_until(span[0])
            self.reader.links.append(self._link(child, image=True))
            label = self.segment.text[span[0] + len("![") : child.meta["label_end"]]
            self.reader.parts.append(RawLabel(self.segment.source(span[1] - 1) + 1, label))
            self.cursor = span[1]
        elif child.type == "link_open":
            self._link_open(child, span)
        elif child.type == "link_close":
            self._link_close()
        elif child.nesting:
            self.reader.parts.append(Element(opening=child.nesting > 0))

    def _link_open(self, child: Token, span: Span | None) -> None:
        if span is None or child.meta.get("autolink"):
            if span is not None:
                self.text_until(span[0])
                self._autolink(child, span)
                self.cursor = span[1]
            self.open_links.append(None)
        else:
            self.text_until(span[0])
            self.reader.links.append(self._link(child, image=False))
            self.cursor = span[0] + 1
            self.open_links.append((child.meta["label_end"], span[1]))
        self.reader.parts.append(Element(opening=True))

    def _autolink(self, child: Token, span: Span) -> None:
        """An autolink's text, which markdown-it renders from the address it decodes."""
        if child.markup != _AUTOLINK:
            return
        self.reader.parts.append(
            Autolink(
                start=self.segment.source(span[0]),
                end=self.segment.source(span[1] - 1) + 1,
                label=child.meta["label"],
                destination=child.meta["destination"],
            )
        )

    def _link_close(self) -> None:
        located = self.open_links.pop() if self.open_links else None
        if located is not None:
            self.text_until(located[0])
            self.cursor = located[1]
        self.reader.parts.append(Element(opening=False))

    def _link(self, token: Token, *, image: bool) -> Link:
        start, end = token.meta["span"]
        label_end = token.meta["label_end"]
        opener_end = start + (2 if image else 1)
        destination = token.meta["destination"]
        source = self.segment.source
        return Link(
            image=image,
            opener=(source(start), source(opener_end)),
            tail=self.segment.pieces(label_end, end),
            destination=None
            if destination is None
            else (source(destination[0]), source(destination[1])),
            reference=token.meta["reference"],
        )


#: The tokens before an inline that make it a paragraph of its own after a table or list.
_ALONE_AFTER = 2
_LIST_OR_TABLE_CLOSE = frozenset({"table_close", "bullet_list_close", "ordered_list_close"})
#: The markup markdown-it gives a link opened by ``<address>``.
_AUTOLINK = "autolink"


def _follows_a_list_or_table(tokens: Sequence[Token], index: int) -> bool:
    """Whether ``tokens[index]`` is a paragraph's inline right after a table or a list."""
    return (
        tokens[index].type == "inline"
        and tokens[index - 1].type == "paragraph_open"
        and tokens[index - 2].type in _LIST_OR_TABLE_CLOSE
    )


def _line_starts(text: str) -> list[int]:
    """The offset of each line's start, and one past the end."""
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    if starts[-1] != len(text):
        starts.append(len(text))
    return starts
