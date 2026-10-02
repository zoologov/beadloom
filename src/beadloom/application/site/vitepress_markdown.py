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

What is not followed here, and where it is followed instead:

- front matter is cut off before markdown-it runs, by gray-matter;
  :func:`front_matter_length` follows gray-matter's rule instead, and
  :func:`front_matter_is_read` whether gray-matter parses the block without an
  error, since an error fails the build;
- ``linkify`` turns a bare ``https://…`` into a link. Python needs
  ``linkify-it-py`` for it, which is not a dependency; a bare address is absolute,
  so no link rule rebases it, and its text is element text that Vue reads either
  way. The one place that differs, a percent-escaped brace the link's text
  decodes, is handled where the text is made inert (:mod:`.project_text`);
- ``markdown-it-attrs`` does not change where a block or a span begins, but it
  does change the text: it reads a ``{...}`` at the end of a block, after an
  inline element, or on a line of its own as the element's attributes, removes
  it from the text, and Vue compiles an attribute named ``:x``, ``@x``, ``v-x`` or
  ``#x`` (``beadloom-ujzb.23``, M2). Where it reads a brace is mirrored in
  :mod:`.markdown_attrs`;
- ``markdown-it-emoji``, ``markdown-it-anchor``, the GitHub alerts, the table of
  contents and the title change attributes and text Vue does not compile, not
  where a block or a span begins;
- the ``<<< path`` snippet and ``<!--@include: path-->`` read files at build time,
  which the portal does not publish; they stay outside what is read here.
"""

# beadloom:domain=application

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

import yaml
from markdown_it import MarkdownIt

if TYPE_CHECKING:
    from collections.abc import Hashable

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


#: The languages gray-matter parses as YAML: none named, or ``yaml``.
_YAML_LANGUAGES = frozenset({"", "yaml"})
#: gray-matter drops comment lines before it decides a block is empty.
_COMMENT_LINE_RE = re.compile(r"^\s*#[^\n]+", re.MULTILINE)
#: The tag of a YAML merge key (``<<``), whose keys may be written again.
_MERGE_TAG = "tag:yaml.org,2002:merge"
#: What JavaScript makes of an object used as a key.
_JS_OBJECT = "[object Object]"
#: The magnitude from which JavaScript writes a whole number with an exponent.
_JS_EXPONENT_FROM = 1e21
#: A plain scalar that starts like a number, a date or ``.inf``/``.nan``.
_NUMERIC_LOOKING_RE = re.compile(r"[-+]?(?:\.?[0-9]|\.(?:inf|nan))", re.IGNORECASE)
#: What PyYAML raises on a block it cannot construct: a date it cannot build is a
#: ``ValueError``, a collection as a key a ``TypeError``.
_UNREADABLE = (yaml.YAMLError, ValueError, TypeError, OverflowError, RecursionError)


def front_matter_is_read(text: str) -> bool:
    """Whether gray-matter, as VitePress 1.6.4 runs it, reads *text*'s front matter without error.

    VitePress parses a page's leading front matter with gray-matter, whose YAML
    engine is js-yaml 3's ``safeLoad``, and an error stops the build (BDL-076,
    ``beadloom-ujzb.23``, re-review finding m1). A text with no front matter, or
    a block holding only comments, is read. gray-matter takes the rest of the
    opening line as the block's language: only YAML is confirmed here, since no
    other engine is mirrored, and an unknown name fails the build.

    PyYAML stands in for js-yaml, with js-yaml's reading of keys: a key is the
    string JavaScript makes of it, so ``1`` and ``"1"``, ``null`` and ``~`` are one
    key and a key written twice is refused; a mapping or a list may be a key. Where
    the two parsers still part, the answer is no: PyYAML refuses a tab js-yaml
    accepts after a colon, and two keys that start like numbers are refused, since
    the two resolve such scalars differently. A block answered no is shown as
    Markdown instead, which builds, so a wrong no costs a block shown as text and
    never a failed build.
    """
    length = front_matter_length(text)
    if not length:
        return True
    body = text[len(_FRONT_MATTER_OPEN) : length]
    newline = body.find("\n")
    language = body if newline < 0 else body[:newline]
    if language.strip() not in _YAML_LANGUAGES:
        return False
    close = body.find(_FRONT_MATTER_CLOSE, len(language))
    matter = body[len(language) : close if close >= 0 else len(body)]
    if not _COMMENT_LINE_RE.sub("", matter).strip():
        return True
    try:
        yaml.load(matter, Loader=_JsYamlKeysLoader)  # noqa: S506 - a SafeLoader subclass
    except _UNREADABLE:
        return False
    return True


class _JsYamlKeysLoader(yaml.SafeLoader):
    """PyYAML's safe loader, reading a mapping's keys as js-yaml 3 does."""

    def construct_mapping(
        self, node: yaml.MappingNode, deep: bool = False
    ) -> dict[Hashable, Any]:  # the stub's own signature
        """Keys as JavaScript strings; an explicit key written twice is refused.

        A merged key (``<<``) may be written again, as js-yaml allows.
        """
        seen: set[str] = set()
        numeric = [key for key, _ in node.value if _numeric_looking(key)]
        if len(numeric) > 1:
            raise yaml.constructor.ConstructorError(
                None, None, "keys js-yaml may read as one number", numeric[1].start_mark
            )
        for key_node, _ in node.value:
            if key_node.tag == _MERGE_TAG:
                continue
            key = _js_key(self.construct_object(key_node, deep=True), key_node)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, "duplicated mapping key", key_node.start_mark
                )
            seen.add(key)
        self.flatten_mapping(node)
        return {
            _js_key(self.construct_object(key, deep=True), key): self.construct_object(
                value, deep=deep
            )
            for key, value in node.value
        }


def _numeric_looking(node: yaml.Node) -> bool:
    """A plain key js-yaml may read as a number or a date, which PyYAML reads by YAML 1.1.

    The two resolve such scalars differently (``1e3`` is a number to js-yaml and a
    string to PyYAML, ``017`` octal to js-yaml only), so two of them in one mapping
    may be one key to js-yaml while PyYAML sees two.
    """
    return (
        isinstance(node, yaml.ScalarNode)
        and node.style is None
        and _NUMERIC_LOOKING_RE.match(node.value) is not None
    )


def _js_key(value: object, node: yaml.Node) -> str:
    """*value* as the property name js-yaml 3 stores it under (``String(key)``)."""
    if isinstance(value, list):
        if any(isinstance(item, list) for item in value):
            raise yaml.constructor.ConstructorError(
                None, None, "nested arrays are not supported inside keys", node.start_mark
            )
        return ",".join("" if item is None else _js_key(item, node) for item in value)
    if isinstance(value, dict):
        return _JS_OBJECT
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return _js_number(value)
    return str(value)


def _js_number(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value.is_integer() and abs(value) < _JS_EXPONENT_FROM:
        return str(int(value))
    return repr(value)
