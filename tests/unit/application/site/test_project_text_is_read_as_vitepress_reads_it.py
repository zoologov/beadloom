"""Project text is made safe for Vue where VitePress's markdown-it reads it, not by a guess.

BDL-076 (``beadloom-ujzb.21``, R2 findings F3 and F4). Until this bead a
hand-written reader decided which characters of a project's Markdown were code,
which were prose and which were raw HTML. R2 found six classes where it read the
text differently from markdown-it, the parser VitePress compiles every page
with, and each one failed ``vitepress build``: what the reader called code got no
``v-pre`` while markdown-it rendered it as text, and what it called prose was
code to markdown-it, where an inserted ``<span v-pre>`` is escaped and the bare
``{{ }}`` reaches Vue.

The text is now read by markdown-it-py, configured as VitePress configures
markdown-it, so each case below is decided by the parser VitePress itself uses.
A brace pair Vue would read as an interpolation is broken by an empty comment
(``{<!---->{``), which renders as the two braces and which Vue never reads as a
delimiter; the earlier ``<span v-pre>`` wrapper was measured to fail on its own
when it crossed an emphasis (``*a {{ b* }}``: "Element is missing end tag").
"""

from __future__ import annotations

import pytest

from beadloom.application.site.markdown_links import PortalLinks
from beadloom.application.site.project_text import render_project_text

_NOWHERE = PortalLinks()


def _inert(text: str, *, opens_page: bool = True) -> str:
    return render_project_text(text, _NOWHERE, opens_page=opens_page)


# -- F3: code regions as markdown-it reads them --------------------------------


def test_a_fence_indented_four_columns_is_an_indented_block_and_vue_is_kept_out() -> None:
    """R2 case b: four spaces before a fence make it an indented code block."""
    text = "Intro.\n\n    ```\n    image: {{ .Values.image.tag }}\n    ```\n\nAfter.\n"
    assert _inert(text) == (
        "Intro.\n\n<div v-pre>\n\n    ```\n    image: {{ .Values.image.tag }}\n    ```\n"
        "\n</div>\n\n\nAfter.\n"
    )


def test_an_indented_fence_that_continues_a_paragraph_opens_nothing() -> None:
    """R2 case c: the indented fence is a lazy continuation, and the prose after it is prose."""
    text = "A paragraph line\n    ```\nstill {{ .Values.x }} prose\n"
    assert _inert(text) == "A paragraph line\n    ```\nstill {<!---->{ .Values.x }} prose\n"


def test_an_indented_fence_inside_a_list_item_is_wrapped_inside_the_item() -> None:
    """R2 case g: six columns in an item whose content starts at two is indented code."""
    text = "- item\n\n      ```yaml\n      tag: {{ .Values.image.tag }}\n      ```\n"
    assert _inert(text) == (
        "- item\n\n  <div v-pre>\n\n      ```yaml\n      tag: {{ .Values.image.tag }}\n"
        "      ```\n\n  </div>\n\n"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (  # R2 case h
            "- item:\n\n      helm install {{ .Release.Name }}\n",
            "- item:\n\n  <div v-pre>\n\n      helm install {{ .Release.Name }}\n\n  </div>\n\n",
        ),
        (  # R2 case o
            "* a\n\n  para\n\n        {{ .Values.deep }}\n",
            "* a\n\n  para\n\n  <div v-pre>\n\n        {{ .Values.deep }}\n\n  </div>\n\n",
        ),
    ],
)
def test_indented_code_inside_a_list_item_is_kept_from_vue(text: str, expected: str) -> None:
    assert _inert(text) == expected


def test_indented_code_inside_a_block_quote_is_wrapped_inside_the_quote() -> None:
    """R2 addendum to F3: the quote's own marker carries every line of the wrapper."""
    text = "> Note:\n>\n>     helm install {{ .Release.Name }}\n"
    assert _inert(text) == (
        "> Note:\n>\n> <div v-pre>\n>\n>     helm install {{ .Release.Name }}\n>\n> </div>\n>\n"
    )


def test_a_fence_ends_with_its_list_item_and_the_next_item_is_prose() -> None:
    """R2 case q: an unclosed fence closes where its list item does."""
    text = "- item\n  ```\n  code\n- next item {{ .Values.n }}\n"
    assert _inert(text) == "- item\n  ```\n  code\n- next item {<!---->{ .Values.n }}\n"


def test_front_matter_is_code_only_where_the_text_opens_its_page() -> None:
    """R2 case i: below another block, a front matter block is a rule and a heading."""
    text = "---\ntitle: x {{ .Values.a }}\n---\n\n# Head\n"
    assert _inert(text, opens_page=True) == text
    assert _inert(text, opens_page=False) == (
        "---\ntitle: x {<!---->{ .Values.a }}\n---\n\n# Head\n"
    )


def test_an_unclosed_front_matter_is_the_whole_text_as_gray_matter_reads_it() -> None:
    """VitePress's gray-matter takes everything after an unclosed ``---`` as front matter."""
    text = "---\ntitle: {{ x }}\n"
    assert _inert(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "> quote with fence\n> ```\n> {{ .Values.q }}\n> ```\n",  # R2 case k
        "1. step\n   ```sh\n   echo {{ .Values.s }}\n   ```\n",  # R2 case l
    ],
)
def test_a_fence_in_a_quote_or_an_ordered_item_is_left_to_vitepress(text: str) -> None:
    assert _inert(text) == text


def test_a_tab_indented_block_is_kept_from_vue() -> None:
    """R2 case n."""
    text = "Line one\n\n\t{{ .Values.tabbed }}\n"
    assert _inert(text) == "Line one\n\n<div v-pre>\n\n\t{{ .Values.tabbed }}\n\n</div>\n\n"


def test_an_interpolation_between_two_code_spans_is_prose() -> None:
    """R2 case j."""
    assert _inert("Use `a`{{ .Values.b }}`c` here.") == "Use `a`{<!---->{ .Values.b }}`c` here."


def test_a_table_cell_is_read_as_markdown_it_splits_the_row() -> None:
    """R2 case p: a pipe splits the row even inside a code span; a surplus cell is dropped."""
    text = "| a | b |\n|---|---|\n| `x|{{ .Values.t }}` | <T> |\n"
    assert _inert(text) == "| a | b |\n|---|---|\n| `x|{<!---->{ .Values.t }}` | <T> |\n"


def test_an_interpolation_that_crosses_an_emphasis_is_broken_where_it_starts() -> None:
    """The ``<span v-pre>`` wrapper this replaces left ``<em>`` closing inside the span."""
    assert _inert("*a {{ b* }}\n") == "*a {<!---->{ b* }}\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-     {{ x }}\n", "- <div v-pre>\n\n      {{ x }}\n\n  </div>\n\n"),
        ("> 1.      {{ x }}\n", "> 1. <div v-pre>\n>\n>         {{ x }}\n>\n>    </div>\n>\n"),
    ],
)
def test_an_indented_block_on_the_line_of_its_list_marker_is_wrapped_after_the_marker(
    text: str, expected: str
) -> None:
    """The item's marker stays first on its line, and the wrapper opens the item."""
    assert _inert(text) == expected


# -- F4: raw HTML as Vue's template compiler reads it --------------------------


def test_a_generic_type_inside_an_html_block_is_text() -> None:
    """R2 case d: ``<String,`` opens an element to Vue, so it is shown as text."""
    text = "<details>\n<summary>Map<String, Integer> config</summary>\n\nBody.\n\n</details>\n"
    assert _inert(text) == (
        "<details>\n<summary>Map&lt;String, Integer> config</summary>\n\nBody.\n\n</details>\n"
    )


def test_an_interpolation_and_a_generic_inside_a_div_are_text() -> None:
    """R2 case m."""
    text = "<div>\nMap<K,V> and {{ .Values.d }}\n</div>\n"
    assert _inert(text) == "<div>\nMap&lt;K,V> and {<!---->{ .Values.d }}\n</div>\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('<div @click="go">hi</div>\n', "<div>hi</div>\n"),  # R2 case e
        ('<div v-on:click="go">hi</div>\n', '<div v-on:click="go" v-pre>hi</div>\n'),
        ('<span :title="x">t</span>', '<span :title="x" v-pre>t</span>'),
        ('<p #slot .prop="x">t</p>\n', "<p>t</p>\n"),
    ],
)
def test_a_vue_directive_on_raw_html_never_runs(text: str, expected: str) -> None:
    """An attribute only Vue reads is dropped; a directive the DOM can hold gets v-pre."""
    assert _inert(text) == expected


def test_an_unclosed_comment_is_text() -> None:
    """R2 case f: CommonMark runs the comment to the end of the text, and Vue fails on it."""
    assert _inert("Text.\n\n<!-- todo: finish\n\nMore.\n") == (
        "Text.\n\n&lt;!-- todo: finish\n\nMore.\n"
    )


def test_a_raw_element_cannot_close_across_an_element_markdown_it_writes() -> None:
    """``<div>`` above a list and ``</div>`` inside an item would nest wrongly in the page."""
    assert _inert("<div>\n\n- item </div>\n") == "&lt;div>\n\n- item &lt;/div>\n"


def test_a_vue_component_tag_on_a_line_of_its_own_is_text() -> None:
    """VitePress reads an unknown tag at a line start as an HTML block (a component)."""
    assert _inert("<T>\n{{ x }}\n") == "&lt;T>\n{<!---->{ x }}\n"


def test_the_result_is_a_fixed_point() -> None:
    """Rendering what was rendered changes nothing: every edit is final."""
    cases = [
        "Intro.\n\n    ```\n    image: {{ .Values.image.tag }}\n    ```\n\nAfter.\n",
        "<details>\n<summary>Map<String, Integer> config</summary>\n\nBody.\n\n</details>\n",
        "Text.\n\n<!-- todo: finish\n\nMore.\n",
        '<Foo title="{{ x }}">\n',
        "<script>\nconst a = b<c && {{ d }};\n</script>\n",
        "> Note:\n>\n>     helm install {{ .Release.Name }}\n",
        "Run `` {{ a }} <b> & `c` `` now.",
    ]
    for text in cases:
        once = _inert(text)
        assert _inert(once) == once, text


# -- the re-review of R2's fixes (``beadloom-ujzb.23``) -----------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (  # M1: a Helm chart's host, as its README writes it
            "Chart host: <https://{{.Values.host}}/api>\n",
            "Chart host: [https://{<!---->{.Values.host}}/api](<https://{{.Values.host}}/api>)\n",
        ),
        (  # an e-mail autolink: markdown-it links it with mailto:
            "Mail <a{{b}}@x.test> now\n",
            "Mail [a{<!---->{b}}@x.test](<mailto:a{{b}}@x.test>) now\n",
        ),
        (  # what a label reads as Markdown is escaped, so it shows as written
            "See <https://a.test/{{x}}/*_y_*>\n",
            "See [https://a.test/{<!---->{x}}/\\*\\_y\\_\\*](<https://a.test/{{x}}/*_y_*>)\n",
        ),
    ],
)
def test_an_autolink_shows_its_address_as_written_and_vue_reads_no_interpolation(
    text: str, expected: str
) -> None:
    """M1: an autolink's text is the address, element text Vue reads like any other.

    An autolink cannot hold the empty comment that breaks a brace pair, so it is
    written as the link it renders: its address as the text, the same address as
    the destination. The destination is an attribute, which Vue does not read.
    """
    assert _inert(text) == expected


def test_an_autolink_with_no_brace_pair_is_left_as_written() -> None:
    text = "See <https://a.test/x> and <a@b.test>.\n"
    assert _inert(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("``` <span>x\ncode\n```\n", "``` &lt;span>x\ncode\n```\n"),  # n1
        ('```a"b\ncode\n```\n', "```a&quot;b\ncode\n```\n"),
        (  # a code group's tab title, which VitePress writes as the label's text
            "::: code-group\n```js [{{x}} <b>]\na\n```\n:::\n",
            "::: code-group\n```js [{&#123;x}} &lt;b>]\na\n```\n:::\n",
        ),
        ("> - ```<T>\n>   code\n>   ```\n", "> - ```&lt;T>\n>   code\n>   ```\n"),
    ],
)
def test_a_fence_info_string_vitepress_writes_raw_is_shown_as_written(
    text: str, expected: str
) -> None:
    """n1: VitePress writes the fence's language into the page as it is, and Vue compiles it.

    As entities the characters reach the page as written: markdown-it decodes the
    info string before it names the highlighter's language, so that is unchanged.
    """
    assert _inert(text) == expected


@pytest.mark.parametrize(
    "text", ["```js {1,3}\nconst a = 1\n```\n", "```yaml\na: {{ b }}\n```\n", "~~~\nx\n~~~\n"]
)
def test_a_fence_info_string_vue_does_not_misread_is_left_as_written(text: str) -> None:
    assert _inert(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (  # m2: the reviewer's three variants
            "-\t\t{{ .Values.j }}\n",
            "- <div v-pre>\n\n \t\t{{ .Values.j }}\n\n  </div>\n\n",
        ),
        (
            "1.\t\t{{ .Values.j }}\n",
            "1. <div v-pre>\n\n  \t\t{{ .Values.j }}\n\n   </div>\n\n",
        ),
        (
            "-\t\t{{ .Values.j }}\n\t\tline2\n",
            "- <div v-pre>\n\n \t\t{{ .Values.j }}\n\t\tline2\n\n  </div>\n\n",
        ),
        (
            "> -\t\t{{ .Values.j }}\n",
            "> - <div v-pre>\n>\n>  \t\t{{ .Values.j }}\n>\n>   </div>\n>\n",
        ),
        (  # a quote whose marker a tab follows: the quote's space comes from the tab
            ">\t-\t\t{{ .Values.j }}\n",
            ">\t- <div v-pre>\n>\n> \t \t\t{{ .Values.j }}\n>\n>     </div>\n>\n",
        ),
        (  # a quote marker with no space: a new line needs the space the quote takes
            ">-     {{ .Values.j }}\n",
            ">- <div v-pre>\n>\n>       {{ .Values.j }}\n>\n>   </div>\n>\n",
        ),
    ],
)
def test_a_tab_after_a_list_marker_keeps_the_wrapper_inside_the_item(
    text: str, expected: str
) -> None:
    """m2: the wrapper opened after the marker's tab, which moved the item's content column.

    The item then ended before the wrapper closed, and the page showed a literal
    ``<div v-pre>`` in the item and a stray ``</div>`` after the list. The wrapper now
    opens one space after the marker, the column the item had, and the tab moves
    to the code's own line, where it still reaches the column it reached.
    """
    assert _inert(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "---\ntitle: Setup: the first step\n---\n# Setup\n",  # m1: not YAML
        "---\na: 1\na: 2\n---\n# Twice\n",  # js-yaml refuses a duplicated key
        "---toml\na = 1\n---\n# Toml\n",  # gray-matter has no toml engine
        "---\nprose: with colon: again\n",  # unclosed: gray-matter parses all of it
    ],
)
def test_front_matter_gray_matter_cannot_read_is_moved_off_the_top_and_read_as_markdown(
    text: str,
) -> None:
    """m1: VitePress parses a page's leading front matter, and a parse error fails the build.

    A text that opens its page and starts with front matter gray-matter cannot
    read starts with a blank line instead, where gray-matter finds no front
    matter, and the block is Markdown: a rule, a paragraph, a heading.
    """
    assert _inert(text) == f"\n{text}"
    assert _inert(text, opens_page=False) == text


def test_front_matter_gray_matter_cannot_read_is_made_inert_as_markdown() -> None:
    text = "---\ntitle: x {{ y }}: z\n---\n# Doc\n"
    assert _inert(text) == "\n---\ntitle: x {<!---->{ y }}: z\n---\n# Doc\n"
