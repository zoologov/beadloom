"""Where a project's Markdown holds code, which the portal must leave exactly as written.

BDL-076 (``beadloom-ujzb.12``). Two passes change a project's own text on its way
onto a portal page: links are rebased (``beadloom-ujzb.11``) and the text is made
inert to Vue's template compiler. Neither may touch code: a link in a code
example is an example, and ``{{ .Values.image.tag }}`` in a fenced block is
already left alone by VitePress, which wraps fences in ``v-pre``.

:func:`code_regions` answers one question — which characters are code — the way
CommonMark reads it: YAML front matter, fenced blocks (backticks or tildes, in a
list item or a block quote too), indented blocks, and code spans.
"""

from __future__ import annotations

import itertools

import pytest

from beadloom.application.site.markdown_code import code_regions


def _code(markdown: str) -> list[tuple[str, str]]:
    return [
        (region.kind, markdown[region.start : region.end]) for region in code_regions(markdown)
    ]


# -- fenced blocks --------------------------------------------------------------


@pytest.mark.parametrize("fence", ["```", "~~~", "````"])
def test_a_fenced_block_is_code_from_its_opening_line_to_its_closing_line(fence: str) -> None:
    block = f"{fence}yaml\ntag: {{{{ .Values.image.tag }}}}\n{fence}\n"
    assert _code(f"Before.\n\n{block}\nAfter.\n") == [("fence", block)]


def test_a_shorter_fence_inside_a_longer_one_does_not_close_it() -> None:
    block = "````md\n```js\nx\n```\n````\n"
    assert _code(f"{block}After `x`.\n") == [("fence", block), ("code_span", "`x`")]


def test_a_fence_of_the_other_character_does_not_close_it() -> None:
    block = "~~~\n```\n{{ x }}\n~~~\n"
    assert _code(block) == [("fence", block)]


def test_an_unclosed_fence_runs_to_the_end_of_the_text() -> None:
    assert _code("Text.\n\n```\n{{ x }}\n") == [("fence", "```\n{{ x }}\n")]


@pytest.mark.parametrize(
    ("first", "rest"), [("> ", "> "), ("- ", "  "), ("1. ", "   "), ("  ", "  ")]
)
def test_a_fence_in_a_list_item_or_a_block_quote_is_code(first: str, rest: str) -> None:
    block = f"{first}```\n{rest}{{{{ x }}}}\n{rest}```\n"
    assert _code(block) == [("fence", block)]


def test_backticks_in_the_middle_of_a_line_open_no_fence() -> None:
    assert _code("Use ```x``` here.\n") == [("code_span", "```x```")]


# -- front matter ---------------------------------------------------------------


def test_front_matter_at_the_top_is_code() -> None:
    head = "---\ntitle: '{{ x }}'\n---\n"
    assert _code(f"{head}# Doc\n") == [("frontmatter", head)]


def test_a_thematic_break_further_down_is_not_front_matter() -> None:
    assert _code("# Doc\n\n---\n\ntitle: x\n\n---\n") == []


# -- indented blocks ------------------------------------------------------------


def test_an_indented_block_after_a_blank_line_is_code() -> None:
    block = "    {{ .Values.image.tag }}\n    second\n"
    assert _code(f"Text.\n\n{block}\nAfter.\n") == [("indented", block)]


def test_an_indented_block_keeps_its_inner_blank_lines() -> None:
    block = "    one\n\n    two\n"
    assert _code(f"Text.\n\n{block}\nAfter.\n") == [("indented", block)]


def test_an_indented_line_that_continues_a_paragraph_is_not_code() -> None:
    assert _code("A paragraph\n    continued {{ x }}.\n") == []


def test_an_indented_paragraph_inside_a_list_item_is_not_code() -> None:
    assert _code("- item\n\n    continued {{ x }}.\n") == []


def test_an_indented_block_after_a_list_has_ended_is_code() -> None:
    block = "    code\n"
    assert _code(f"- item\n\nA paragraph.\n\n{block}") == [("indented", block)]


def test_a_tab_indents_a_block_as_four_spaces_do() -> None:
    block = "\tcode\n"
    assert _code(f"Text.\n\n{block}") == [("indented", block)]


# -- code spans -----------------------------------------------------------------


def test_a_code_span_is_code() -> None:
    assert _code("Set `{{ x }}` here.") == [("code_span", "`{{ x }}`")]


def test_a_double_backtick_span_holds_a_single_backtick() -> None:
    assert _code("Run `` a ` b `` now.") == [("code_span", "`` a ` b ``")]


def test_a_backtick_run_with_no_partner_is_literal() -> None:
    assert _code("A lone ` backtick and {{ x }}.") == []


def test_an_escaped_backtick_opens_no_span() -> None:
    assert _code("A \\` and `code`.") == [("code_span", "`code`")]


def test_a_code_span_may_cross_a_line_but_not_a_paragraph() -> None:
    assert _code("A `span\nacross` line.") == [("code_span", "`span\nacross`")]
    assert _code("A `broken\n\nspan` here.") == []


def test_regions_are_sorted_and_do_not_overlap() -> None:
    text = "---\na: 1\n---\n`x` and\n\n```\n`y`\n```\n\n    `z`\n"
    regions = code_regions(text)
    assert [r.kind for r in regions] == ["frontmatter", "code_span", "fence", "indented"]
    assert all(a.end <= b.start for a, b in itertools.pairwise(regions))


@pytest.mark.parametrize("next_line", ["- b `c`", "  - b `c`", "1. b `c`", "# b `c`", "> b `c`"])
def test_a_code_span_does_not_close_in_the_next_block(next_line: str) -> None:
    """A list item, a heading or a quote starts a block of its own, and a span stays in its own.

    Measured on this repository's ``docs/domains/onboarding/README.md``: an
    unpartnered backtick in one list item, read as closing in the next, flipped
    every later span of the list inside out.
    """
    text = f"- a `x\n{next_line}"
    assert _code(text) == [("code_span", "`c`")]


def test_a_code_span_does_not_close_in_the_next_table_row() -> None:
    assert _code("| `a |\n| b` |") == []
