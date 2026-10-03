# beadloom:domain=application
# beadloom:feature=site-generation
"""Where VitePress's markdown-it-attrs would read a brace as the start of attributes.

VitePress 1.6.4 runs markdown-it-attrs 4.x with its defaults, since the portal's
configuration sets no ``markdown.attrs``: ``{`` and ``}`` delimit attributes and
every attribute name is allowed. The plugin is a core rule that runs after the
inline parse and before text tokens are joined, and reads braces only in text
tokens and in an image's label. Its patterns, as the bundled source has them
(BDL-076, ``beadloom-ujzb.23``, re-review finding M2):

- the end of a block: the last child of an inline token ends with ``{...}``
  (``end of block``, ``list item end``), or a line of its own after a soft break
  is ``{...}`` (``softbreak then curly``, ``list softbreak``);
- after an element: a text token starts with ``{...}`` right after a closing
  inline element, an image or a code span (``inline attributes``, ``inline
  nesting 0``);
- a paragraph of its own right after a table or a list (``tables``, ``list
  double softbreak``);
- a thematic break written as ``*** {...}`` (``horizontal rule``);
- a fence's info string, whose attributes VitePress's fence renderer drops.

What it reads moves onto the element and leaves the text, and Vue compiles an
attribute whose name starts with ``:``, ``@``, ``v-`` or ``#``. A brace escaped
with a backslash is a token of its own (``text_special``) when the plugin runs, so
it is never a delimiter, and it renders as the brace it is.

:func:`attribute_braces` names the braces to escape in one run of an inline
token's text. A run here may be several tokens to markdown-it, since an emphasis
or an escape splits one, so the reading is a superset of the plugin's: a brace
named here that the plugin would not have read gains a backslash that renders as
nothing. :func:`ends_with_attributes` is the test the plugin applies to an image's
label, which it reads as written, escapes included.
"""

# beadloom:domain=application

from __future__ import annotations

import re

_OPEN = "{"
_CLOSE = "}"
_ESCAPE = "\\"
#: The shortest attributes the plugin reads, ``{a}``, and with a class or id, ``{.a}``.
_SHORTEST = 3
_SHORTEST_NAMED = 4
_NAMED = (".", "#")
#: Characters that close an emphasis or a strikethrough just before a brace.
_CLOSERS = frozenset("*_~")
#: ``*** {.a}``: the plugin turns such a paragraph into a rule (its ``__hr`` pattern).
_RULE_RE = re.compile(r" {0,3}[-*_]{3,} ?(?=\{[^}])")


def attribute_braces(text: str, *, opens: bool, closes: bool, alone: bool) -> list[int]:
    """The indices of the braces in *text* the plugin could read as a left delimiter.

    *text* is one run of an inline token's text, as Markdown source. *opens* says
    the run starts its inline token and *closes* that it ends it; *alone* says the
    inline is a paragraph that directly follows a table or a list.
    """
    found: set[int] = set()
    line_start = 0
    for line in text.split("\n"):
        line_end = line_start + len(line)
        for index in range(line_start, line_end):
            if (
                _is_open(text, index)
                and _after_element(text, index, opens=opens)
                and _reads_from_start(text[index:line_end])
            ):
                found.add(index)
        line_start = line_end + 1
    if opens:
        found.update(_opening(text, alone=alone))
    if closes:
        found.update(_closing(text))
    return sorted(found)


def ends_with_attributes(text: str) -> bool:
    """The plugin's ``end`` test on *text* as written: the last ``{`` opens a run closing it."""
    start = text.rfind(_OPEN)
    return start >= 0 and _reads_to_end(text, start)


def _opening(text: str, *, alone: bool) -> set[int]:
    """A paragraph after a table or a list that starts with a brace, and ``*** {...}``."""
    found: set[int] = set()
    if alone and _is_open(text, 0):
        found.add(0)
    rule = _RULE_RE.match(text)
    if rule is not None:
        found.add(rule.end())
    return found


def _closing(text: str) -> set[int]:
    """The brace that ends the inline (``end``) and a last line that is one (``only``)."""
    found: set[int] = set()
    line_start = text.rfind("\n") + 1
    line = text[line_start:]
    last = _last_open(line)
    if last is not None and _reads_to_end(line, last):
        found.add(line_start + last)
    if line_start and _is_open(line, 0) and line.endswith(_CLOSE) and _long_enough(line):
        found.add(line_start)
    return found


def _after_element(text: str, index: int, *, opens: bool) -> bool:
    """Whether a token that closes an element can end just before *index*."""
    if index == 0:
        return not opens
    return text[index - 1] in _CLOSERS


def _reads_from_start(run: str) -> bool:
    """markdown-it-attrs' ``hasDelimiters('start')`` on *run*, which starts with ``{``."""
    end = run.find(_CLOSE, len(_OPEN) + 1)
    if end < 0 or run[end + 1 : end + 2] == _CLOSE:
        return False
    return _long_enough(run[: end + 1])


def _reads_to_end(line: str, start: int) -> bool:
    """markdown-it-attrs' ``hasDelimiters('end')``: the ``{`` at *start* opens a closing run."""
    return line.find(_CLOSE, start + len(_OPEN) + 1) == len(line) - 1 and _long_enough(
        line[start:]
    )


def _long_enough(curly: str) -> bool:
    shortest = _SHORTEST_NAMED if curly[1:2] in _NAMED else _SHORTEST
    return len(curly) >= shortest


def _last_open(line: str) -> int | None:
    for index in range(len(line) - 1, -1, -1):
        if _is_open(line, index):
            return index
    return None


def _is_open(text: str, index: int) -> bool:
    """Whether *index* holds a ``{`` that no backslash escapes."""
    if text[index : index + 1] != _OPEN:
        return False
    backslashes = 0
    while index - backslashes - 1 >= 0 and text[index - backslashes - 1] == _ESCAPE:
        backslashes += 1
    return backslashes % 2 == 0
