"""Braces VitePress's markdown-it-attrs would read as attributes are shown as written.

BDL-076 (``beadloom-ujzb.23``, re-review finding M2). VitePress 1.6.4 runs
markdown-it-attrs with its defaults (delimiters ``{`` and ``}``, every attribute
allowed). It reads a ``{...}`` that ends a paragraph, a heading, a table cell or a
list item, that follows an emphasis, a code span or a link, or that is a line of its
own after a soft break, as attributes of the element, and removes it from the text.
Vue then compiles an attribute that starts with ``:``, ``@``, ``v-`` or ``#``.
Measured with VitePress's renderer and ``@vue/compiler-sfc``: ``In Clojure a map is
{:a 1 :b 2}`` failed with "v-bind is missing expression", ``{v-for="i in list"}``
became a live directive, ``A set {a, b}`` lost its braces, and two headings ending
``{#setup}`` stopped the render ("User defined `id` attribute `setup` is not
unique").

The plugin reads a brace only in a text token. A backslash before the brace makes
markdown-it read it as an escape, a token of its own, so the plugin never sees a
delimiter and the page shows ``{`` exactly as before. Where the plugin reads an
image's raw label, an empty comment after the image keeps the image from ending its
element. Braces the plugin would not read are left as written.
"""

from __future__ import annotations

import pytest

from beadloom.application.site.markdown_links import PortalLinks
from beadloom.application.site.project_text import render_project_text

_NOWHERE = PortalLinks()


def _inert(text: str) -> str:
    return render_project_text(text, _NOWHERE)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # The reviewer's cases.
        ("In Clojure a map is {:a 1 :b 2}\n", "In Clojure a map is \\{:a 1 :b 2}\n"),
        ("Pass options as { :verbose => true }\n", "Pass options as \\{ :verbose => true }\n"),
        ("Log fields like {@timestamp}\n", "Log fields like \\{@timestamp}\n"),
        ("An Elixir map: %{:a => 1}\n", "An Elixir map: %\\{:a => 1}\n"),
        ("## Options {:verbose}\n", "## Options \\{:verbose}\n"),
        ("- the config {:port 8080}\n", "- the config \\{:port 8080}\n"),
        ("A set {a, b}\n", "A set \\{a, b}\n"),
        ('Template {v-for="i in list"}\n', 'Template \\{v-for="i in list"}\n'),
        # The plugin's other places: after a closing inline element, a code span or a link.
        ("*a*{:x} b\n", "*a*\\{:x} b\n"),
        ("`a`{:x} b\n", "`a`\\{:x} b\n"),
        ("[a](https://a.test){:x} b\n", "[a](https://a.test)\\{:x} b\n"),
        # A table cell, a line after a soft break, a paragraph after a table or a list.
        ("| a | b |\n|---|---|\n| c {:x} | d |\n", "| a | b |\n|---|---|\n| c \\{:x} | d |\n"),
        ("para\n{:x}\n", "para\n\\{:x}\n"),
        ("- item\n{:x}\n", "- item\n\\{:x}\n"),
        ("| a |\n|---|\n| b |\n\n{:x}\n", "| a |\n|---|\n| b |\n\n\\{:x}\n"),
        ("- a\n- b\n\n{:x}\n", "- a\n- b\n\n\\{:x}\n"),
        ("| a |\n|---|\n| b |\n\n{a} b}\n", "| a |\n|---|\n| b |\n\n\\{a} b}\n"),
        # A rule written with attributes, a class, an id.
        ("*** {:x}\n", "*** \\{:x}\n"),
        ("Text {.red}\n", "Text \\{.red}\n"),
        ("## Setup {#setup}\n", "## Setup \\{#setup}\n"),
        # A container's title is rendered inline, and its info string is read as
        # written by the plugin's fence pattern, which any block token with one meets.
        ("::: tip Note {:x}\nBody.\n:::\n", "::: tip Note \\{:x}<!---->\nBody.\n:::\n"),
    ],
)
def test_braces_the_plugin_reads_as_attributes_are_shown_as_written(
    text: str, expected: str
) -> None:
    assert _inert(text) == expected


def test_two_headings_with_one_id_are_shown_as_written_rather_than_stopping_the_render() -> None:
    """A project's own ``{#id}`` is shown, not applied: a repeated one stops VitePress's render."""
    text = "## Setup {#setup}\n\n## Again {#setup}\n"
    assert _inert(text) == "## Setup \\{#setup}\n\n## Again \\{#setup}\n"


def test_an_image_whose_label_ends_with_braces_does_not_end_its_paragraph() -> None:
    """The plugin reads an image's label as written, so an escape there would not hide it."""
    text = "![map {:a 1}](https://a.test/p.png)\n"
    assert _inert(text) == "![map {:a 1}](https://a.test/p.png)<!---->\n"


def test_an_interpolation_ending_a_line_after_braces_keeps_both_breaks() -> None:
    """A brace pair is broken for Vue and the delimiter escaped for the plugin, in that order."""
    assert _inert("Set {{x y}\n") == "Set {<!---->\\{x y}\n"


@pytest.mark.parametrize(
    "text",
    [
        # Braces in the middle of a line, which the plugin does not read.
        "Use the {v-if=x} form\n",
        "A {a} in the middle of a line.\n",
        # A Helm value ending a paragraph: the plugin finds a second brace before the end.
        "Set {<!---->{ .Values.tag }}\n",
        # Too short to be attributes, or escaped already.
        "Empty {}\n",
        "Escaped \\{:a 1}\n",
        # Code the plugin never reads.
        "Use `{:a 1}`\n",
        "```clojure\n{:a 1}\n```\n",
    ],
)
def test_braces_the_plugin_does_not_read_are_left_as_written(text: str) -> None:
    assert _inert(text) == text


def test_the_result_is_a_fixed_point() -> None:
    cases = [
        "In Clojure a map is {:a 1 :b 2}\n",
        "*a*{:x} and `b`{:y} and {:z}\n",
        "| a |\n|---|\n| b |\n\n{a} b}\n",
        "![map {:a 1}](https://a.test/p.png)\n",
        "Set {{x y}\n",
        "::: tip Note {:x}\nBody.\n:::\n",
    ]
    for text in cases:
        once = _inert(text)
        assert _inert(once) == once, text
