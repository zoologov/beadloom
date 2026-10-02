# beadloom:domain=application
# beadloom:feature=site-generation
"""markdown-it-py set up the way VitePress 1.6.4 sets up markdown-it, as far as Python can follow.

The portal's pages are compiled by VitePress, which reads Markdown with
markdown-it 14.1 and then hands the HTML to Vue. What the generator changes in a
project's own text (its links, and what Vue must not read) depends on how that
text is read, so it is read here by the same algorithm: markdown-it-py 4.x is
the Python port of markdown-it 14.1 (BDL-076, ``beadloom-ujzb.21``, after a
hand-written reader disagreed with markdown-it in six classes and each failed
``vitepress build``).

VitePress builds ``MarkdownIt({html: true, linkify: true})`` on markdown-it's
default preset, and then changes the parser with plugins. This module follows
each one that changes WHICH block or inline construct a line is:

- the preset: ``js-default`` (CommonMark plus tables and strikethrough), with
  raw HTML on;
- ``@mdit-vue/plugin-component`` replaces the HTML rules. An unknown tag at the
  start of a line (a Vue component, ``<T>``) opens an HTML block, a line that is
  one tag opens one too, and an inline tag may carry an attribute that starts
  with ``@``. Both rules are ported below, line for line;
- ``markdown-it-container`` opens a container at ``::: tip`` and the other names
  VitePress registers, and its content is read as blocks. Ported below.

What is not followed, and why it does not change a decision made here:

- front matter is cut off before markdown-it runs, by gray-matter;
  :func:`front_matter_length` follows gray-matter's rule instead;
- ``linkify`` turns a bare ``https://…`` into a link. Python needs
  ``linkify-it-py`` for it, which is not a dependency; a bare address is absolute,
  so no link rule rebases it, and its text is element text that Vue reads either
  way;
- ``markdown-it-attrs`` (``{.class}``), ``markdown-it-emoji``,
  ``markdown-it-anchor``, the GitHub alerts, the table of contents and the title
  change attributes and text, not where a block or a span begins;
- the ``<<< path`` snippet and ``<!--@include: path-->`` read files at build time,
  which the portal does not publish; they stay outside what is read here.
"""

# beadloom:domain=application

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt

if TYPE_CHECKING:
    from markdown_it.parser_block import RuleFuncBlockType
    from markdown_it.rules_block import StateBlock
    from markdown_it.rules_inline import StateInline

# -- the component plugin's HTML rules (@mdit-vue/plugin-component 2.1) --------

#: Tags VitePress treats as blocks (``TAGS_BLOCK``).
_TAGS_BLOCK = (
    "address", "article", "aside", "base", "basefont", "blockquote", "body", "caption",
    "center", "col", "colgroup", "dd", "details", "dialog", "dir", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "frame", "frameset", "h1", "h2",
    "h3", "h4", "h5", "h6", "head", "header", "hr", "html", "iframe", "legend", "li", "link",
    "main", "menu", "menuitem", "nav", "noframes", "ol", "optgroup", "option", "p", "param",
    "search", "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "title",
    "tr", "track", "ul",
)  # fmt: skip
#: Tags VitePress treats as inline (``TAGS_INLINE``).
_TAGS_INLINE = (
    "a", "abbr", "acronym", "audio", "b", "bdi", "bdo", "big", "br", "button", "canvas",
    "cite", "code", "data", "datalist", "del", "dfn", "em", "embed", "i", "iframe", "img",
    "input", "ins", "kbd", "label", "map", "mark", "meter", "noscript", "object", "output",
    "picture", "progress", "q", "ruby", "s", "samp", "script", "select", "slot", "small",
    "span", "strong", "sub", "sup", "svg", "template", "textarea", "time", "u", "tt", "var",
    "video", "wbr",
)  # fmt: skip
#: Vue's own tags, which are components even though their names look like HTML.
_TAGS_VUE_RESERVED = frozenset(
    ("template", "component", "transition", "transition-group", "keep-alive", "slot", "teleport")
)
_INLINE_TAGS = "|".join(tag for tag in _TAGS_INLINE if tag not in _TAGS_VUE_RESERVED)

_ATTR_NAME = r"[a-zA-Z_:@][a-zA-Z0-9:._-]*"
_ATTR_VALUE = r"""(?:[^"'=<>`\x00-\x20]+|'[^']*'|"[^"]*")"""
_ATTRIBUTE = rf"(?:\s+{_ATTR_NAME}(?:\s*=\s*{_ATTR_VALUE})?)"
_OPEN_TAG = rf"<[A-Za-z][A-Za-z0-9\-]*{_ATTRIBUTE}*\s*\/?>"
_CLOSE_TAG = r"<\/[A-Za-z][A-Za-z0-9\-]*\s*>"
_COMMENT = r"<!---->|<!--(?:-?[^>-])(?:-?[^-])*-->"
_HTML_TAG_RE = re.compile(
    rf"(?:{_OPEN_TAG}|{_CLOSE_TAG}|{_COMMENT}|<[?][\s\S]*?[?]>"
    rf"|<![A-Z]+\s+[^>]*>|<!\[CDATA\[[\s\S]*?\]\]>)"
)
_OPEN_CLOSE_TAG = rf"(?:{_OPEN_TAG}|{_CLOSE_TAG})"
_SELF_CLOSING_TAG_RE = re.compile(rf"<[A-Za-z][A-Za-z0-9\-]*{_ATTRIBUTE}*\s*\/>")
_OPEN_AND_CLOSE_IN_ONE_LINE_RE = re.compile(
    rf"<([A-Za-z][A-Za-z0-9\-]*){_ATTRIBUTE}*\s*>.*<\/\1\s*>"
)
_BLOCK_TAGS = "|".join(_TAGS_BLOCK)
#: (opening pattern, closing pattern, may interrupt a paragraph), in VitePress's order.
_HTML_SEQUENCES: tuple[tuple[re.Pattern[str], re.Pattern[str], bool], ...] = (
    (
        re.compile(r"^<(script|pre|style)(?=(\s|>|$))", re.I),
        re.compile(r"<\/(script|pre|style)>", re.I),
        True,
    ),
    (re.compile(r"^<!--"), re.compile(r"-->"), True),
    (re.compile(r"^<\?"), re.compile(r"\?>"), True),
    (re.compile(r"^<![A-Z]"), re.compile(r">"), True),
    (re.compile(r"^<!\[CDATA\["), re.compile(r"\]\]>"), True),
    (re.compile(rf"^</?({_BLOCK_TAGS})(?=(\s|/?>|$))", re.I), re.compile(r"^$"), True),
    (
        re.compile(rf"^</?(?!({_INLINE_TAGS})(?![\w-]))[A-Za-z][A-Za-z0-9\-]*(?=(\s|/?>|$))"),
        re.compile(r"^$"),
        True,
    ),
    (re.compile(rf"^{_OPEN_CLOSE_TAG}\s*$"), re.compile(r"^$"), False),
)  # fmt: skip
#: The index of the component sequence, which may end on the line it opens.
_COMPONENT = 6
_CODE_INDENT = 4


def _html_block(state: StateBlock, start_line: int, end_line: int, silent: bool) -> bool:
    """``createHtmlBlockRule``: an HTML block, a component tag included."""
    pos = state.bMarks[start_line] + state.tShift[start_line]
    line_end = state.eMarks[start_line]
    if state.sCount[start_line] - state.blkIndent >= _CODE_INDENT:
        return False
    if not state.md.options.get("html") or state.src[pos : pos + 1] != "<":
        return False
    line_text = state.src[pos:line_end]
    index = next((i for i, seq in enumerate(_HTML_SEQUENCES) if seq[0].search(line_text)), None)
    if index is None:
        return False
    if silent:
        return _HTML_SEQUENCES[index][2]
    if index == _COMPONENT and _component_on_one_line(state, start_line, line_text):
        return True
    next_line = start_line + 1
    if not _HTML_SEQUENCES[index][1].search(line_text):
        while next_line < end_line:
            if state.sCount[next_line] < state.blkIndent:
                break
            text = state.src[
                state.bMarks[next_line] + state.tShift[next_line] : state.eMarks[next_line]
            ]
            if _HTML_SEQUENCES[index][1].search(text):
                if text:
                    next_line += 1
                break
            next_line += 1
    state.line = next_line
    token = state.push("html_block", "", 0)
    token.map = [start_line, next_line]
    token.content = state.getLines(start_line, next_line, state.blkIndent, True)
    return True


def _component_on_one_line(state: StateBlock, start_line: int, line_text: str) -> bool:
    """A component that closes on its own line: an inline tag, then the rest of the line inline."""
    match = _SELF_CLOSING_TAG_RE.match(line_text) or _OPEN_AND_CLOSE_IN_ONE_LINE_RE.match(
        line_text
    )
    if match is None:
        return False
    state.line = start_line + 1
    tag = state.push("html_inline", "", 0)
    tag.content = match.group(0)
    tag.map = [start_line, state.line]
    rest = state.push("inline", "", 0)
    rest.content = line_text[len(match.group(0)) :]
    rest.map = [start_line, state.line]
    rest.children = []
    return True


def _html_inline(state: StateInline, silent: bool) -> bool:
    """``htmlInlineRule``: a tag, comment or declaration inside a paragraph."""
    pos = state.pos
    if not state.md.options.get("html"):
        return False
    if state.src[pos] != "<" or pos + 2 >= state.posMax:
        return False
    second = state.src[pos + 1]
    if second not in "!?/" and not ("a" <= second.lower() <= "z"):
        return False
    match = _HTML_TAG_RE.match(state.src, pos)
    if match is None:
        return False
    if not silent:
        token = state.push("html_inline", "", 0)
        token.content = match.group(0)
    state.pos = match.end()
    return True


# -- markdown-it-container 4.0, under the names VitePress registers ------------

#: VitePress's containers; the first five render their title as inline Markdown.
CONTAINERS = ("tip", "info", "warning", "danger", "details", "v-pre", "raw", "code-group")
TITLED_CONTAINERS = frozenset(CONTAINERS[:5])
_MARKER = ":"
_MIN_MARKERS = 3


def _container(name: str) -> RuleFuncBlockType:
    """markdown-it-container's block rule for the container *name*."""

    def rule(state: StateBlock, start_line: int, end_line: int, silent: bool) -> bool:
        start = state.bMarks[start_line] + state.tShift[start_line]
        line_end = state.eMarks[start_line]
        if state.src[start : start + 1] != _MARKER:
            return False
        pos = _marker_run_end(state.src, start, line_end)
        count = pos - start
        if count < _MIN_MARKERS:
            return False
        params = state.src[pos:line_end]
        if params.strip().split(" ", 1)[0] != name:
            return False
        if silent:
            return True
        next_line, auto_closed = _container_end(state, start_line, end_line, count)
        old_parent, old_max = state.parentType, state.lineMax
        state.parentType = "container"
        state.lineMax = next_line
        opening = state.push(f"container_{name}_open", "div", 1)
        opening.markup = state.src[start:pos]
        opening.block = True
        opening.info = params
        opening.map = [start_line, next_line]
        state.md.block.tokenize(state, start_line + 1, next_line)
        closing = state.push(f"container_{name}_close", "div", -1)
        closing.block = True
        state.parentType, state.lineMax = old_parent, old_max
        state.line = next_line + (1 if auto_closed else 0)
        return True

    return rule


def _marker_run_end(src: str, start: int, line_end: int) -> int:
    pos = start + 1
    while pos <= line_end and src[pos : pos + 1] == _MARKER:
        pos += 1
    return pos


def _container_end(
    state: StateBlock, start_line: int, end_line: int, count: int
) -> tuple[int, bool]:
    """The line that closes the container, and whether a marker line closed it."""
    next_line = start_line
    while True:
        next_line += 1
        if next_line >= end_line:
            return next_line, False
        start = state.bMarks[next_line] + state.tShift[next_line]
        line_end = state.eMarks[next_line]
        if start < line_end and state.sCount[next_line] < state.blkIndent:
            return next_line, False
        if state.src[start : start + 1] != _MARKER:
            continue
        if state.sCount[next_line] - state.blkIndent >= _CODE_INDENT:
            continue
        pos = _marker_run_end(state.src, start, line_end)
        if pos - start < count:
            continue
        if state.skipSpaces(pos) < line_end:
            continue
        return next_line, True


# -- the parser -----------------------------------------------------------------


def vitepress_markdown() -> MarkdownIt:
    """A new markdown-it-py parser that reads Markdown as VitePress 1.6.4's markdown-it does."""
    md = MarkdownIt("js-default", {"html": True})
    md.block.ruler.at("html_block", _html_block, {"alt": ["paragraph", "reference", "blockquote"]})
    md.inline.ruler.at("html_inline", _html_inline)
    for name in CONTAINERS:
        md.block.ruler.before(
            "fence",
            f"container_{name}",
            _container(name),
            {"alt": ["paragraph", "reference", "blockquote", "list"]},
        )
    return md


# -- front matter, as gray-matter reads it ------------------------------------

_FRONT_MATTER_OPEN = "---"
_FRONT_MATTER_CLOSE = "\n---"


def front_matter_length(text: str, *, closed_only: bool = False) -> int:
    """How many leading characters of *text* gray-matter takes as front matter; 0 for none.

    gray-matter opens front matter at a leading ``---`` not followed by another
    ``-``, closes it at the next ``---`` that starts a line, and, with no such
    line, takes the whole text. One newline after the closing marker is part of
    it; anything else on that line is not. With *closed_only*, a block that never
    closes counts as none.
    """
    if not text.startswith(_FRONT_MATTER_OPEN) or text[3:4] == "-":
        return 0
    close = text.find(_FRONT_MATTER_CLOSE, len(_FRONT_MATTER_OPEN))
    if close < 0:
        return 0 if closed_only else len(text)
    end = close + len(_FRONT_MATTER_CLOSE)
    return end + 1 if text[end : end + 1] == "\n" else end
