"""The parser reads Markdown's blocks as VitePress 1.6.4's markdown-it does (``beadloom-ujzb.21``).

What was measured, on Node 22.9.0 against a portal's installed VitePress 1.6.4:

- every block-token expectation below: the token types and line maps that
  VitePress's own ``createMarkdownRenderer`` produced for the same text. Over this
  repository's 142 Markdown files and the R2 reviewer's 18 cases (57,613 block
  tokens) the two parsers agreed on every token once markdown-it-anchor's
  permalink and a table cell's line map (kept by markdown-it-py, dropped by
  markdown-it 14) were set aside; GitHub alerts differ only in the token's name;
- every front matter length: what the gray-matter bundled in VitePress cut off.

The raw HTML cases follow Vue's template tokenizer; the R2 cases that rest on it
were compiled with ``@vue/compiler-sfc`` (the project-text tests).
"""

from __future__ import annotations

import pytest

from beadloom.application.site.markdown_positions import located_markdown, normalise
from beadloom.application.site.markdown_source import Segment, read_markdown
from beadloom.application.site.raw_html import read_markup
from beadloom.application.site.vitepress_markdown import front_matter_length, vitepress_markdown


def _blocks(text: str) -> list[tuple[str, list[int] | None]]:
    return [(token.type, token.map) for token in vitepress_markdown().parse(text)]


# -- markdown-it-container, under VitePress's names ------------------------------


def test_a_container_holds_blocks_and_closes_at_its_marker() -> None:
    assert _blocks("::: tip Title\n    code\n:::\n") == [
        ("container_tip_open", [0, 2]),
        ("code_block", [1, 2]),
        ("container_tip_close", None),
    ]


def test_a_longer_marker_holds_a_shorter_container() -> None:
    types = [kind for kind, _ in _blocks("::::: warning\n::: info\ninner\n:::\n:::::\n")]
    assert types[:2] == ["container_warning_open", "container_info_open"]
    assert types[-2:] == ["container_info_close", "container_warning_close"]


def test_an_unclosed_container_runs_to_the_end_of_its_parent() -> None:
    assert _blocks("- ::: details\n  body\n- next\n")[2:4] == [
        ("container_details_open", [0, 2]),
        ("paragraph_open", [1, 2]),
    ]


@pytest.mark.parametrize("text", ["::: note\nx\n:::\n", ":: tip\nx\n", "::: tip\tx\n"])
def test_a_name_vitepress_does_not_register_opens_no_container(text: str) -> None:
    assert not any(kind.startswith("container_") for kind, _ in _blocks(text))


def test_a_marker_indented_four_columns_does_not_close_the_container() -> None:
    assert _blocks("::: raw\n    :::\n:::\n")[1] == ("code_block", [1, 2])


# -- @mdit-vue/plugin-component's HTML rules -------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<T>\n{{ x }}\n", [("html_block", [0, 2])]),
        ('<my-el a="1">\n\npara\n', [("html_block", [0, 1])]),
        ('<img src="a.png">\n', [("html_block", [0, 1])]),
        ("<span>x</span> y\n", [("paragraph_open", [0, 1])]),
        ("<template>\nx\n</template>\n", [("html_block", [0, 3])]),
    ],
)
def test_an_unknown_tag_or_a_lone_tag_opens_an_html_block(
    text: str, expected: list[tuple[str, list[int]]]
) -> None:
    assert _blocks(text)[: len(expected)] == expected


def test_a_component_closed_on_its_own_line_is_a_tag_and_inline_text() -> None:
    expected = [("html_inline", [0, 1]), ("inline", [0, 1])]
    assert _blocks('<Badge text="v1" /> after\n') == expected
    assert _blocks("<Foo>x</Foo> rest\n") == expected


def test_an_inline_tag_may_carry_an_attribute_vue_reads() -> None:
    children = vitepress_markdown().parse('x <span @click="a" :b="c">y</span>\n')[1].children
    assert [child.type for child in children or []] == [
        "text",
        "html_inline",
        "text",
        "html_inline",
    ]


def test_an_html_block_is_not_read_where_code_is() -> None:
    assert _blocks("    <div>\n") == [("code_block", [0, 1])]


# -- front matter, as gray-matter reads it ---------------------------------------


@pytest.mark.parametrize(
    ("text", "length"),
    [
        ("---\na: 1\n---\nbody", 13),
        ("---\na: 1\n---", 12),
        ("---\n---\nbody", 8),
        ("---\na: 1\n---x\nbody", 12),
        ("----\na: 1\n----\n", 0),
        ("# t\n---\na\n---\n", 0),
        ("---\na: 1\n", 9),
    ],
)
def test_front_matter_is_what_gray_matter_takes(text: str, length: int) -> None:
    assert front_matter_length(text) == length


def test_an_unclosed_front_matter_is_none_where_only_a_closed_one_counts() -> None:
    assert front_matter_length("---\na: 1\n", closed_only=True) == 0


# -- raw HTML as Vue reads it ------------------------------------------------------


@pytest.mark.parametrize(
    "html",
    [
        "<!-- open",
        "<!DOCTYPE html>",
        "<?xml?>",
        "</ div>",
        "</div",
        '<a href="x',
        "<a href=",
        "<b",
    ],
)
def test_markup_vue_cannot_read_is_unreadable(html: str) -> None:
    assert [markup.kind for markup in read_markup(html)] == ["unreadable"]


def test_a_less_than_sign_before_a_space_or_a_digit_is_text() -> None:
    assert read_markup("a < b and 1<2") == []


def test_a_stray_slash_inside_a_tag_is_skipped_and_a_self_closing_one_ends_it() -> None:
    (tag,) = read_markup("<img / src=x/ >")
    assert (tag.kind, [attribute.name for attribute in tag.attributes]) == ("open", ["src"])
    (closed,) = read_markup("<br/>")
    assert closed.self_closing


def test_attribute_values_are_read_in_every_quoting() -> None:
    (tag,) = read_markup("<a href='x' title=\"t\" data-n=3 hidden>")
    assert [(a.name, a.value) for a in tag.attributes] == [
        ("href", "x"),
        ("title", "t"),
        ("data-n", "3"),
        ("hidden", None),
    ]


# -- where each piece of text came from ------------------------------------------


def _origins_hold(text: str) -> None:
    """Every located segment's characters are the source's, except tab padding."""
    for token in located_markdown().parse(text, {}):
        origins = token.meta.get("origins")
        if origins is None:
            continue
        for index, char in enumerate(token.content):
            assert text[origins[index]] == char or char == " ", (token.type, index)


@pytest.mark.parametrize(
    "text",
    [
        "| a | b |\n|---|---|\n| x \\| y | `c` |\n",
        "> - item\n>   cont\n",
        "-\tlist with a tab\n\n\t\tcode\n",
        "# Heading ##\n\nSetext\n===\n",
        "[a]:\n  /url\n  'title'\n",
    ],
)
def test_every_located_character_comes_from_the_source(text: str) -> None:
    _origins_hold(text)


def test_a_container_title_is_located_after_its_name() -> None:
    (title,) = [
        token.meta["title"]
        for token in located_markdown().parse("::: details  My *title*\nx\n:::\n", {})
        if "title" in token.meta
    ]
    assert title[0] == "My *title*"
    assert title[1][0] == len("::: details  ")


def test_a_segment_splits_into_one_source_range_per_line() -> None:
    segment = Segment("ab\ncd", (2, 3, 4, 7, 8, 9))
    assert segment.pieces(1, 5) == ((3, 4), (7, 9))
    assert segment.slice(3, 5) == Segment("cd", (7, 8, 9))


def test_reading_text_that_is_not_normalised_is_refused() -> None:
    with pytest.raises(ValueError, match="normalised"):
        read_markdown("a\r\nb")
    assert normalise("a\r\nb\rc\0") == "a\nb\nc�"


def test_a_container_title_is_text_vue_reads() -> None:
    text = "::: tip {{ x }}\nbody\n:::\n"
    parts = read_markdown(text).parts
    texts = [part.segment.text for part in parts if hasattr(part, "segment")]
    assert "{{ x }}" in texts
