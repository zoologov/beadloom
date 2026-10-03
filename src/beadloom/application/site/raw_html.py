# beadloom:domain=application
# beadloom:feature=site-generation
"""Raw HTML as Vue's template compiler reads it: where each tag, comment and attribute is.

markdown-it passes an HTML block, and each inline tag, through as written, and
VitePress hands the page to Vue's template compiler. Inside that raw HTML it is
Vue's tokenizer that decides what is markup, and it is more willing than
CommonMark: ``<String,`` opens an element named ``String,``, ``<K,V>`` one named
``K,V``, and ``@click`` is an attribute (BDL-076, ``beadloom-ujzb.21``, R2
finding F4: each failed ``vitepress build`` or left a live binding).

:func:`read_markup` follows that tokenizer. A ``<`` followed by a letter opens a
tag whose name runs to whitespace, ``/`` or ``>``; ``</`` and a letter close
one; ``<!--`` opens a comment that runs to ``-->``. Anything else that starts
with ``<!``, ``<?`` or ``</``, and a tag or comment the text ends inside, is
``unreadable``: Vue reports an error for it. A ``<`` followed by anything else
is text, for Vue and here.
"""

# beadloom:domain=application

from __future__ import annotations

from dataclasses import dataclass

_COMMENT_OPEN = "<!--"
_COMMENT_CLOSE = "-->"
_WHITESPACE = frozenset(" \t\n\r\f")
_NAME_END = _WHITESPACE | {"/", ">"}
_ATTRIBUTE_NAME_END = _NAME_END | {"="}


@dataclass(frozen=True)
class Attribute:
    """One attribute: ``start`` is its leading whitespace, ``end`` the end of its value."""

    name: str
    start: int
    name_start: int
    end: int
    value: str | None


@dataclass(frozen=True)
class Markup:
    """A piece of markup in raw HTML, as Vue reads it.

    ``kind`` is ``open``, ``close``, ``comment`` or ``unreadable``. For an opening
    tag, ``attributes_end`` is where its attributes end, before ``/>`` or ``>``.
    """

    kind: str
    start: int
    end: int
    name: str = ""
    self_closing: bool = False
    attributes: tuple[Attribute, ...] = ()
    attributes_end: int = 0


def read_markup(html: str) -> list[Markup]:
    """Every piece of markup in *html*, in order; what lies between them is text."""
    found: list[Markup] = []
    position = html.find("<")
    while 0 <= position < len(html):
        markup = _markup_at(html, position)
        if markup is None:
            position = html.find("<", position + 1)
            continue
        found.append(markup)
        position = html.find("<", markup.end)
    return found


def _markup_at(html: str, start: int) -> Markup | None:
    after = html[start + 1 : start + 2]
    if html.startswith(_COMMENT_OPEN, start):
        close = html.find(_COMMENT_CLOSE, start + len(_COMMENT_OPEN))
        if close < 0:
            return Markup("unreadable", start, start + 1)
        return Markup("comment", start, close + len(_COMMENT_CLOSE))
    if after in {"!", "?"}:
        return Markup("unreadable", start, start + 1)
    if after == "/":
        return _closing_tag(html, start)
    if _is_letter(after):
        return _opening_tag(html, start)
    return None


def _is_letter(char: str) -> bool:
    return len(char) == 1 and char.isascii() and char.isalpha()


def _closing_tag(html: str, start: int) -> Markup:
    name_start = start + 2
    if not _is_letter(html[name_start : name_start + 1]):
        return Markup("unreadable", start, start + 1)
    name_end = _scan_until(html, name_start, _NAME_END)
    close = html.find(">", name_end)
    if close < 0:
        return Markup("unreadable", start, start + 1)
    return Markup("close", start, close + 1, name=html[name_start:name_end])


def _opening_tag(html: str, start: int) -> Markup:
    name_end = _scan_until(html, start + 1, _NAME_END)
    attributes: list[Attribute] = []
    position = name_end
    while True:
        attribute_start = position
        position = _skip_to_attribute(html, position)
        if position >= len(html):
            return Markup("unreadable", start, start + 1)
        if html.startswith("/>", position) or html[position] == ">":
            self_closing = html[position] == "/"
            end = position + (2 if self_closing else 1)
            return Markup(
                "open",
                start,
                end,
                name=html[start + 1 : name_end],
                self_closing=self_closing,
                attributes=tuple(attributes),
                attributes_end=_attributes_end(html, attribute_start, position),
            )
        attribute = _attribute(html, attribute_start, position)
        if attribute is None:
            return Markup("unreadable", start, start + 1)
        attributes.append(attribute)
        position = attribute.end


def _attributes_end(html: str, after_last: int, tail: int) -> int:
    """Where the attributes end: before the whitespace that precedes ``/>`` or ``>``."""
    end = tail
    while end > after_last and html[end - 1] in _WHITESPACE:
        end -= 1
    return end


def _attribute(html: str, start: int, name_start: int) -> Attribute | None:
    """The attribute whose name starts at *name_start*; ``None`` when the text ends inside it."""
    name_end = _scan_until(html, name_start + 1, _ATTRIBUTE_NAME_END)
    name = html[name_start:name_end]
    after_name = _skip(html, name_end, _WHITESPACE)
    if html[after_name : after_name + 1] != "=":
        return Attribute(name, start, name_start, name_end, None)
    value_start = _skip(html, after_name + 1, _WHITESPACE)
    if value_start >= len(html):
        return None
    quote = html[value_start]
    if quote in {'"', "'"}:
        close = html.find(quote, value_start + 1)
        if close < 0:
            return None
        return Attribute(name, start, name_start, close + 1, html[value_start + 1 : close])
    value_end = _scan_until(html, value_start, _WHITESPACE | {">"})
    return Attribute(name, start, name_start, value_end, html[value_start:value_end])


def _skip_to_attribute(html: str, position: int) -> int:
    """Past whitespace, and past a ``/`` that does not close the tag (Vue ignores it)."""
    while position < len(html):
        if html[position] in _WHITESPACE or (
            html[position] == "/" and html[position + 1 : position + 2] != ">"
        ):
            position += 1
        else:
            break
    return position


def _scan_until(html: str, position: int, stops: frozenset[str]) -> int:
    while position < len(html) and html[position] not in stops:
        position += 1
    return position


def _skip(html: str, position: int, skipped: frozenset[str]) -> int:
    while position < len(html) and html[position] in skipped:
        position += 1
    return position
