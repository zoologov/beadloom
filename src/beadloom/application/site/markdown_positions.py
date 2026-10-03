# beadloom:domain=application
# beadloom:feature=site-generation
"""Where in the source each piece of text markdown-it reads came from.

markdown-it-py gives a block token the lines it spans, and an inline token
nothing at all, while the generator must change a project's text at exact
characters: a link's destination, a code span, a ``<`` that Vue would read as a
tag (BDL-076, ``beadloom-ujzb.21``). This module wraps the rules of the parser
:func:`.vitepress_markdown.vitepress_markdown` builds, so that every token
carries its place in the source in ``token.meta``:

- a block token whose content is text (an ``inline`` token, an HTML block, a
  definition, a container's title) carries ``origins``: for each character of
  its content, the source offset it was read from, plus one entry for the end.
  The content is cut out of indented, quoted and table lines, so this is a map,
  not an offset: a tab partly consumed by indentation becomes spaces, and a
  table cell loses the backslash of an escaped pipe;
- an inline token carries ``span``, its start and end within its parent's
  content, and a link or an image the parts of it a rewrite needs;
- an indented code block carries what a line needs to stay inside the block's
  containers (its list items and block quotes), for a line inserted around it.

The offsets are offsets into the text the parser was given, which must already
be normalised the way markdown-it normalises it (:func:`normalise`).
"""

# beadloom:domain=application

from __future__ import annotations

import functools
import re
from typing import TYPE_CHECKING, TypeVar

from markdown_it.common.utils import isStrSpace, normalizeReference

from beadloom.application.site.vitepress_markdown import CONTAINERS, vitepress_markdown

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from markdown_it import MarkdownIt
    from markdown_it.ruler import Ruler
    from markdown_it.rules_block import StateBlock
    from markdown_it.rules_inline import StateInline
    from markdown_it.token import Token

    #: A function that records positions on the tokens one block rule pushed.
    Locate = Callable[[StateBlock, int, Sequence[Token]], None]

_Rule = TypeVar("_Rule")

_NEWLINES_RE = re.compile(r"\r\n?")
#: A character of a container's line prefix that only opens a list item.
_LIST_MARKER_RE = re.compile(r"[^>\s]")
_TAB_STOP = 4
_MAILTO = "mailto:"
#: A block quote's marker with no space after it on its line, where the quote's own
#: optional space is still to come.
_QUOTE_MARKER = ">"


def normalise(text: str) -> str:
    """*text* as markdown-it reads it: line endings as ``\\n``, NUL as U+FFFD."""
    return _NEWLINES_RE.sub("\n", text).replace("\0", "\ufffd")


@functools.lru_cache(maxsize=1)
def located_markdown() -> MarkdownIt:
    """The VitePress parser, recording on every token where its text came from.

    Shared and cached: a parse leaves the parser as it was.
    """
    md = vitepress_markdown()
    md.options["inline_definitions"] = True
    for name in ("link", "image", "backticks", "autolink", "html_inline"):
        _wrap_inline(md, name)
    locators: dict[str, Locate] = {
        "paragraph": _locate_lines,
        "lheading": _locate_lines,
        "reference": _locate_definition,
        "heading": _locate_heading,
        "table": _locate_table,
        "html_block": _locate_html_block,
        "code": _locate_code_block,
        "fence": _locate_fence,
    }
    locators.update({f"container_{name}": _locate_container for name in CONTAINERS})
    for name, locate in locators.items():
        _wrap_block(md, name, locate)
    return md


# -- inline rules -----------------------------------------------------------------


def _wrap_inline(md: MarkdownIt, name: str) -> None:
    rule, alt = _existing(md.inline.ruler, name)

    def located(state: StateInline, silent: bool) -> bool:
        start, count = state.pos, len(state.tokens)
        if not rule(state, silent):
            return False
        if not silent:
            _mark_inline(state, start, state.tokens[count:])
        return True

    md.inline.ruler.at(name, located, {"alt": alt})


def _mark_inline(state: StateInline, start: int, pushed: Sequence[Token]) -> None:
    """Record ``span`` on the token a rule produced; the parts of a link or an image."""
    for token in pushed:
        if token.type in {"html_inline", "code_inline"}:
            token.meta["span"] = (start, state.pos)
            return
        if token.type == "link_open" and token.markup in {"autolink", "linkify"}:
            token.meta["span"] = (start, state.pos)
            token.meta["autolink"] = True
            token.meta.update(_autolink_parts(state, start, pushed[pushed.index(token) :]))
            return
        if token.type in {"link_open", "image"}:
            token.meta["span"] = (start, state.pos)
            token.meta.update(_link_parts(state, start, image=token.type == "image"))
            return


def _autolink_parts(state: StateInline, start: int, pushed: Sequence[Token]) -> dict[str, str]:
    """An autolink's rendered text and its address, from its ``link_open`` onwards in *pushed*.

    The text is the address with its percent-escapes decoded (``normalizeLinkText``),
    so it can hold a brace its source does not show. An e-mail address links to
    ``mailto:`` and the address.
    """
    address = state.src[start + 1 : state.pos - 1]
    href = str(pushed[0].attrs.get("href", ""))
    email = href.lower().startswith(_MAILTO) and not address.lower().startswith(_MAILTO)
    label = next((token.content for token in pushed if token.type == "text"), address)
    return {"label": label, "destination": f"{_MAILTO}{address}" if email else address}


def _link_parts(state: StateInline, start: int, *, image: bool) -> dict[str, object]:
    """The label's end, and the destination's span or the reference's label, per markdown-it.

    Mirrors markdown-it's link rule after the fact: an inline destination when
    ``(…)`` parses, a reference otherwise.
    """
    opener = start + 1 if image else start
    src, maximum = state.src, state.posMax
    label_end = state.md.helpers.parseLinkLabel(state, opener, not image)
    destination = _inline_destination(state, label_end + 1)
    if destination is not None:
        return {"label_end": label_end, "destination": destination, "reference": None}
    pos = label_end + 1
    label = ""
    if pos < maximum and src[pos] == "[":
        end = state.md.helpers.parseLinkLabel(state, pos)
        if end >= 0:
            label = src[pos + 1 : end]
    key = normalizeReference(label or src[opener + 1 : label_end])
    return {"label_end": label_end, "destination": None, "reference": key}


def _inline_destination(state: StateInline, pos: int) -> tuple[int, int] | None:
    """The span of ``(destination "title")``'s destination at *pos*, or ``None`` when it fails."""
    src, maximum = state.src, state.posMax
    if pos >= maximum or src[pos] != "(":
        return None
    pos = _skip_space(src, pos + 1, maximum)
    if pos >= maximum:
        return None
    start = pos
    result = state.md.helpers.parseLinkDestination(src, pos, maximum)
    if result.ok and state.md.validateLink(state.md.normalizeLink(result.str)):
        pos = result.pos
    end = pos
    pos = _skip_space(src, pos, maximum)
    title = state.md.helpers.parseLinkTitle(src, pos, maximum)
    if pos < maximum and end != pos and title.ok:
        pos = _skip_space(src, title.pos, maximum)
    if pos >= maximum or src[pos] != ")":
        return None
    return (start, end)


def _skip_space(src: str, pos: int, maximum: int) -> int:
    while pos < maximum and (isStrSpace(src[pos]) or src[pos] == "\n"):
        pos += 1
    return pos


# -- block rules ------------------------------------------------------------------


def _wrap_block(md: MarkdownIt, name: str, locate: Locate) -> None:
    rule, alt = _existing(md.block.ruler, name)

    def located(state: StateBlock, start_line: int, end_line: int, silent: bool) -> bool:
        count = len(state.tokens)
        if not rule(state, start_line, end_line, silent):
            return False
        if not silent:
            locate(state, start_line, state.tokens[count:])
        return True

    md.block.ruler.at(name, located, {"alt": alt})


def _existing(ruler: Ruler[_Rule], name: str) -> tuple[_Rule, list[str]]:
    """The function of the rule *name*, and the chains it terminates (``Ruler.at`` resets them)."""
    index = ruler.__find__(name)
    if index < 0:
        raise LookupError(f"no rule {name!r}")
    rule = ruler.__rules__[index]
    return rule.fn, list(rule.alt)


def _lines(
    state: StateBlock, begin: int, end: int, indent: int, keep_last_lf: bool
) -> tuple[str, list[int]]:
    """``StateBlock.getLines``, and the source offset of each character it returns."""
    chunks: list[str] = []
    origins: list[int] = []
    for line in range(begin, end):
        line_indent = 0
        line_start = first = state.bMarks[line]
        last = state.eMarks[line] + 1 if line + 1 < end or keep_last_lf else state.eMarks[line]
        last = min(last, len(state.src))
        while first < last and line_indent < indent:
            char = state.src[first]
            if isStrSpace(char):
                if char == "\t":
                    line_indent += _TAB_STOP - (line_indent + state.bsCount[line]) % _TAB_STOP
                else:
                    line_indent += 1
            elif first - line_start < state.tShift[line]:
                line_indent += 1
            else:
                break
            first += 1
        if line_indent > indent:
            pad = line_indent - indent
            chunks.append(" " * pad)
            origins.extend([first - 1] * pad)
        chunks.append(state.src[first:last])
        origins.extend(range(first, last))
    return "".join(chunks), origins


def _store(token: Token, origins: Sequence[int], text: str) -> None:
    """Record *origins* on *token*, whose content they must describe exactly."""
    if text != token.content:
        raise AssertionError(f"located {text!r} for {token.type} {token.content!r}")
    end = origins[-1] + 1 if origins else 0
    token.meta["origins"] = (*origins, end)


def _strip(text: str, origins: list[int]) -> tuple[str, list[int]]:
    lead = len(text) - len(text.lstrip())
    trail = len(text.rstrip())
    if trail <= lead:
        return "", []
    return text[lead:trail], origins[lead:trail]


def _locate_lines(state: StateBlock, start_line: int, pushed: Sequence[Token]) -> None:
    """A paragraph or a setext heading: its lines, stripped as the rule strips them."""
    for token in pushed:
        if token.type == "inline" and token.map is not None:
            text, origins = _lines(state, start_line, token.map[1], state.blkIndent, False)
            text, origins = _strip(text, origins)
            _store(token, origins, text)


def _locate_heading(state: StateBlock, start_line: int, pushed: Sequence[Token]) -> None:
    pos = state.bMarks[start_line] + state.tShift[start_line]
    while state.src[pos : pos + 1] == "#":
        pos += 1
    for token in pushed:
        if token.type == "inline":
            at = (
                state.src.find(token.content, pos, state.eMarks[start_line])
                if token.content
                else pos
            )
            _store(token, range(at, at + len(token.content)), token.content)


def _locate_table(state: StateBlock, start_line: int, pushed: Sequence[Token]) -> None:
    """Each cell, as the table rule splits its row: escaped pipes lose their backslash."""
    rows: dict[int, list[tuple[str, list[int]]]] = {}
    seen: dict[int, int] = {}
    for token in pushed:
        if token.type != "inline" or token.map is None:
            continue
        line = token.map[0]
        if line not in rows:
            rows[line] = _cells(state, line)
        index = seen.get(line, 0)
        seen[line] = index + 1
        cells = rows[line]
        text, origins = cells[index] if index < len(cells) else ("", [])
        _store(token, origins, text)


def _cells(state: StateBlock, line: int) -> list[tuple[str, list[int]]]:
    start = state.bMarks[line] + state.tShift[line]
    raw = state.src[start : state.eMarks[line]]
    text, origins = _strip(raw, list(range(start, start + len(raw))))
    cells = _escaped_split(text, origins)
    if cells and not cells[0][0]:
        cells.pop(0)
    if cells and not cells[-1][0]:
        cells.pop()
    return [_strip(*cell) for cell in cells]


def _escaped_split(text: str, origins: list[int]) -> list[tuple[str, list[int]]]:
    """markdown-it's ``escapedSplit``, carrying each character's source offset."""
    result: list[tuple[str, list[int]]] = []
    current_text = ""
    current_origins: list[int] = []
    last = 0
    escaped = False
    for pos, char in enumerate(text):
        if char == "|":
            if not escaped:
                result.append((current_text + text[last:pos], current_origins + origins[last:pos]))
                current_text, current_origins = "", []
                last = pos + 1
            else:
                current_text += text[last : pos - 1]
                current_origins = current_origins + origins[last : pos - 1]
                last = pos
        escaped = char == "\\"
    result.append((current_text + text[last:], current_origins + origins[last:]))
    return result


def _locate_html_block(state: StateBlock, start_line: int, pushed: Sequence[Token]) -> None:
    """An HTML block's lines; a component closed on its own line is a tag, then inline text."""
    for token in pushed:
        if token.type == "html_block" and token.map is not None:
            text, origins = _lines(state, start_line, token.map[1], state.blkIndent, True)
            _store(token, origins, text)
    tags = [token for token in pushed if token.type in {"html_inline", "inline"}]
    pos = state.bMarks[start_line] + state.tShift[start_line]
    for token in tags:
        _store(token, range(pos, pos + len(token.content)), token.content)
        pos += len(token.content)


def _locate_definition(state: StateBlock, start_line: int, pushed: Sequence[Token]) -> None:
    """A reference definition: its lines, its label and the span of its destination."""
    for token in pushed:
        if token.type != "definition" or token.map is None:
            continue
        text, origins = _lines(state, start_line, token.map[1], state.blkIndent, False)
        lead = len(text) - len(text.lstrip(" \t"))
        text, origins = text[lead:], origins[lead:]
        token.content = text
        _store(token, origins, text)
        label_end = _label_end(text)
        pos = _skip_space(text, label_end + 2, len(text))
        result = state.md.helpers.parseLinkDestination(text, pos, len(text))
        token.meta["destination"] = (pos, result.pos)
        token.meta["reference"] = normalizeReference(text[1:label_end])


def _label_end(text: str) -> int:
    """Where a definition's ``[label]`` closes: the first unescaped ``]``."""
    pos = 1
    while pos < len(text):
        if text[pos] == "\\":
            pos += 2
            continue
        if text[pos] == "]":
            return pos
        pos += 1
    return len(text)


def _locate_container(state: StateBlock, start_line: int, pushed: Sequence[Token]) -> None:
    """A container's title, the text after its name VitePress renders inline, and its end."""
    opening = pushed[0] if pushed else None
    if opening is None or not opening.type.endswith("_open"):
        return
    params_start = state.bMarks[start_line] + state.tShift[start_line] + len(opening.markup)
    info = opening.info
    name = opening.type[len("container_") : -len("_open")]
    lead = len(info) - len(info.lstrip())
    after_name = info.lstrip()[len(name) :]
    title = after_name.strip()
    at = params_start + lead + len(name) + (len(after_name) - len(after_name.lstrip()))
    opening.meta["title"] = (title, (*range(at, at + len(title)), at + len(title)))
    opening.meta["info_end"] = state.eMarks[start_line]


def _locate_fence(state: StateBlock, start_line: int, pushed: Sequence[Token]) -> None:
    """A fence's info string: the rest of its opening line, after the marker run."""
    for token in pushed:
        if token.type == "fence":
            start = state.bMarks[start_line] + state.tShift[start_line] + len(token.markup)
            token.meta["info"] = (start, state.eMarks[start_line])


def _locate_code_block(state: StateBlock, start_line: int, pushed: Sequence[Token]) -> None:
    """What a line inserted before or after an indented block needs to stay in its containers.

    ``continuation`` begins any new line inside the block's containers: its block
    quote markers, each with the space a quote may take after it, and the
    indentation of its list items. A marker written with no space has its
    content one column nearer, so a new line gets the space, or it would lose
    that column to it. When the block's first line also opens a list item, a
    line cannot go before it; ``insert_at`` is then right after the item's
    marker, and ``resume`` is what the rest of that line needs in front of it
    once it moves to a line of its own. Such an item's content starts one column
    past its marker (markdown-it reads more as code), so a line inserted there
    puts one space after the marker: a tab after it would set the content column
    by where the tab ends, and the item would end before the inserted lines do
    (``beadloom-ujzb.23``, m2).
    """
    line_start = state.src.rfind("\n", 0, state.bMarks[start_line]) + 1
    quoted = state.src[line_start : state.bMarks[start_line]]
    prefix = _LIST_MARKER_RE.sub(" ", quoted)
    if prefix.endswith(_QUOTE_MARKER):
        prefix += " "
    continuation = prefix + " " * state.blkIndent
    lead = state.src[
        state.bMarks[start_line] : state.bMarks[start_line] + state.tShift[start_line]
    ]
    marker = lead.rstrip()
    space = ""
    if marker:
        insert_at = state.bMarks[start_line] + len(marker)
        space = " "
        resume = prefix + _LIST_MARKER_RE.sub(" ", marker)
    elif _LIST_MARKER_RE.search(quoted):
        insert_at = state.bMarks[start_line]
        resume = prefix
    else:
        insert_at = line_start
        resume = ""
    for token in pushed:
        if token.type == "code_block":
            token.meta.update(
                continuation=continuation, insert_at=insert_at, resume=resume, lead=space
            )
