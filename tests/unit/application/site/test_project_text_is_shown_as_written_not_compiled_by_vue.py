"""A project's own text on a portal page is the author's text, never a Vue template.

BDL-076 (``beadloom-ujzb.12``). VitePress compiles every Markdown page as a Vue
template. Measured on VitePress 1.6.4 with a fixture project, each form below in
a README or a published document, one build per form:

- ``{{ .Values.image.tag }}`` and ``{{ user.name | upper }}`` failed the build in
  prose, in inline code, in an indented block, in a table cell, in a heading and
  inside an HTML block; ``{{ name }}`` rendered as nothing and ``{{ 1 + 1 }}`` as
  ``2``. A fenced block was safe, because VitePress wraps it in ``v-pre``.
- ``List<String>`` and an unclosed ``<details>`` failed the build.
- ``<script>`` failed it; ``<style>`` vanished and restyled the whole page;
  ``<div v-if="false">`` was hidden by Vue; ``<MyWidget />`` vanished.
- ``a < b``, a closed ``<p align="center">``, ``<br>`` and an HTML comment built
  and rendered as written.

:func:`render_project_text` keeps each form as the author wrote it: a brace pair
Vue would read is broken by an empty comment (``{<!---->{``), a tag it cannot
compile or must not run becomes text, and a tag it can compile is kept.

``beadloom-ujzb.21`` changed the mechanism for prose from ``<span v-pre>`` around
the interpolation to an empty comment between its braces, because the span was
measured to fail the build on its own when it crossed an emphasis
(``*a {{ b* }}``); the expectations below that name ``<span v-pre>`` changed with
it, and nothing else about them did.
"""

from __future__ import annotations

import pytest

from beadloom.application.site.markdown_links import PortalLinks
from beadloom.application.site.project_text import render_project_text
from beadloom.application.site.repository_link import RepositoryLink

_NOWHERE = PortalLinks()


def _inert(text: str) -> str:
    return render_project_text(text, _NOWHERE)


# -- an interpolation in prose ------------------------------------------------


@pytest.mark.parametrize(
    "mustache",
    ["{{ .Values.image.tag }}", "{{ name }}", "{{ 1 + 1 }}", "{{ user.name | upper }}"],
)
def test_an_interpolation_in_prose_is_left_alone_by_vue(mustache: str) -> None:
    assert _inert(f"Set {mustache} here.") == f"Set {{<!---->{mustache[1:]} here."


def test_each_interpolation_on_a_line_is_left_alone() -> None:
    out = _inert("{{ a }} and {{ b }}")
    assert out == "{<!---->{ a }} and {<!---->{ b }}"


def test_an_interpolation_that_does_not_close_on_its_line_is_left_alone_from_its_braces() -> None:
    assert _inert("Open {{ x\nand y }}.") == "Open {<!---->{ x\nand y }}."


def test_braces_that_markdown_turns_into_an_interpolation_are_left_alone() -> None:
    assert _inert("A \\{\\{ x") == "A \\{<!---->\\{ x"


@pytest.mark.parametrize("braces", ["&#123;&#123;", "&lbrace;&lbrace;"])
def test_braces_written_as_entities_stay_entities_vue_does_not_read(braces: str) -> None:
    """Measured (``beadloom-ujzb.21``): VitePress writes an entity back as written.

    The page holds ``&#123;&#123;``, which Vue's tokenizer does not take for a
    delimiter; the earlier expectation wrapped it in ``<span v-pre>`` for nothing.
    """
    assert _inert(f"A {braces} x") == f"A {braces} x"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("| a |\n|---|\n| {{ x.y }} |\n", "| a |\n|---|\n| {<!---->{ x.y }} |\n"),
        ("## Set {{ .Values.tag }}\n", "## Set {<!---->{ .Values.tag }}\n"),
        ("[{{ x }}](https://a.test)", "[{<!---->{ x }}](https://a.test)"),
    ],
)
def test_an_interpolation_in_a_table_a_heading_or_link_text_is_left_alone(
    text: str, expected: str
) -> None:
    assert _inert(text) == expected


def test_an_interpolation_inside_an_html_block_is_left_alone() -> None:
    text = '<p align="center">\n  {{ .Values.x }}\n</p>\n'
    assert _inert(text) == '<p align="center">\n  {<!---->{ .Values.x }}\n</p>\n'


@pytest.mark.parametrize(
    "text",
    [
        '<img alt="{{ x }}" src="https://a.test/a.png">',
        "<!-- a {{ .Values.x }} comment -->",
        "```yaml\ntag: {{ .Values.image.tag }}\n```\n",
        "~~~\n{{ x }}\n~~~\n",
        "---\ntitle: '{{ x }}'\n---\n# Doc\n",
    ],
)
def test_an_interpolation_vue_does_not_read_is_left_as_written(text: str) -> None:
    assert _inert(text) == text


# -- an interpolation in code -------------------------------------------------


def test_a_code_span_holding_an_interpolation_becomes_code_vue_leaves_alone() -> None:
    out = _inert("Set `{{ .Values.image.tag }}` here.")
    assert out == "Set <code v-pre>{{ .Values.image.tag }}</code> here."


def test_such_a_code_span_keeps_its_characters_and_its_padding_rule() -> None:
    """A backtick inside is escaped: unescaped, markdown-it read `` `c` `` as a nested code span.

    Measured (``beadloom-ujzb.21``): the earlier output rendered
    ``<code v-pre>… <code>c</code></code>``, and the author's backticks were lost.
    """
    out = _inert("Run `` {{ a }} <b> & `c` `` now.")
    assert out == "Run <code v-pre>{{ a }} &lt;b&gt; &amp; \\`c\\`</code> now."


def test_a_code_span_with_no_interpolation_is_left_as_written() -> None:
    text = "Use `List<String>` and `a | b`."
    assert _inert(text) == text


def test_an_indented_block_holding_an_interpolation_is_wrapped_so_vue_leaves_it_alone() -> None:
    text = "Text.\n\n    {{ .Values.image.tag }}\n\nAfter.\n"
    expected = "Text.\n\n<div v-pre>\n\n    {{ .Values.image.tag }}\n\n</div>\n\n\nAfter.\n"
    assert _inert(text) == expected


def test_an_indented_block_with_no_interpolation_is_left_as_written() -> None:
    text = "Text.\n\n    plain code\n\nAfter.\n"
    assert _inert(text) == text


# -- a tag Vue cannot compile, or must not run --------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Returns List<String> items.", "Returns List&lt;String> items."),
        ("An Option<T>.", "An Option&lt;T>."),
        ("Use <MyWidget /> here.", "Use &lt;MyWidget /> here."),
        ("<Details>x</Details>", "&lt;Details>x&lt;/Details>"),
    ],
)
def test_a_tag_that_is_not_lowercase_html_is_text(text: str, expected: str) -> None:
    assert _inert(text) == expected


def test_an_unclosed_element_is_text_and_its_closed_neighbours_are_kept() -> None:
    text = "<details><summary>More</summary>\n\nHidden."
    assert _inert(text) == "&lt;details><summary>More</summary>\n\nHidden."


def test_a_stray_closing_tag_is_text() -> None:
    assert _inert("Text.</div>") == "Text.&lt;/div>"


def test_misnested_elements_keep_the_outer_pair_and_show_the_rest_as_text() -> None:
    assert _inert("<b><i>x</b></i>") == "<b>&lt;i>x</b>&lt;/i>"


def test_an_inline_element_cannot_close_in_a_later_paragraph() -> None:
    assert _inert("a <b>x\n\ny</b> z") == "a &lt;b>x\n\ny&lt;/b> z"


def test_a_block_element_closes_across_paragraphs_on_a_line_of_its_own() -> None:
    text = "<details>\n<summary>More</summary>\n\nHidden **text**.\n\n</details>\n"
    assert _inert(text) == text


def test_a_block_element_cannot_close_inside_a_later_paragraph() -> None:
    text = "<details>\n\nHidden.</details>\n"
    assert _inert(text) == "&lt;details>\n\nHidden.&lt;/details>\n"


@pytest.mark.parametrize("name", ["script", "style", "template", "iframe", "textarea"])
def test_an_element_that_would_run_or_restyle_the_page_is_text(name: str) -> None:
    out = _inert(f"<{name}>\nbody {{ color: red }}\n</{name}>\n")
    assert out == f"&lt;{name}>\nbody {{ color: red }}\n&lt;/{name}>\n"


def test_an_escaped_tag_shows_its_interpolation_as_written_too() -> None:
    out = _inert('<Foo title="{{ x }}">')
    assert out == '&lt;Foo title="{<!---->{ x }}">'


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('<div v-if="false">shown</div>', '<div v-if="false" v-pre>shown</div>'),
        ('<span :title="x">t</span>', '<span :title="x" v-pre>t</span>'),
        ('<img v-bind:src="x" />', '<img v-bind:src="x" v-pre />'),
        # Vue already skips what a v-pre element holds; the earlier reader wrapped it anyway.
        ("<p v-pre>{{ x }}</p>", "<p v-pre>{{ x }}</p>"),
    ],
)
def test_a_vue_directive_on_a_kept_element_is_shown_rather_than_run(
    text: str, expected: str
) -> None:
    assert _inert(text) == expected


# -- what never changes -------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "a < b and c > d",
        "one<br>two<br/>three<hr>",
        '<p align="center">\n  <img src="https://a.test/logo.png" width="200">\n</p>\n',
        "Press <kbd>Ctrl</kbd>+<kbd>C</kbd>, see<sup>1</sup>.",
        "<https://acme.test> and <team@acme.test>",
        "An escaped \\<String> tag.",
        "<!-- beadloom:note -->\n\nText.\n",
        "Use `<a href=x>` literally.",
        "```html\n<details>\n```\n",
        "# Title\n\nPlain prose with a [link](https://a.test) and `code`.\n",
        "{ single } braces and } }} closers",
    ],
)
def test_text_vue_already_reads_as_written_is_unchanged(text: str) -> None:
    assert _inert(text) == text


def test_a_line_with_several_forms_keeps_each_as_written() -> None:
    once = _inert("<b>{{ x }}</b> `{{ y }}` List<T>")
    assert once == "<b>{<!---->{ x }}</b> <code v-pre>{{ y }}</code> List&lt;T>"


# -- a raw link and a raw image -----------------------------------------------

_REPO = "https://gitlab.com/acme/orders"
#: The commit the site was generated from (BDL-076 B4: links are at it, not at `main`).
_REF = "fedcba9876543210fedcba9876543210fedcba98"
_PORTAL = PortalLinks(
    doc_slugs=frozenset({"guide", "other"}),
    page_routes={"readme.md": "/"},
    base="/orders/",
    mirrored_files=frozenset({"docs/guide.md", "docs/other.md", "docs/logo.png"}),
)
_WITH_REPO = PortalLinks(
    doc_slugs=_PORTAL.doc_slugs,
    page_routes=_PORTAL.page_routes,
    repository=RepositoryLink(url=_REPO, ref=_REF),
    base=_PORTAL.base,
    mirrored_files=_PORTAL.mirrored_files,
)


def _doc(text: str, portal: PortalLinks = _PORTAL) -> str:
    return render_project_text(text, portal, source_dir="docs", mirrored_dir="docs")


def test_a_raw_link_to_a_repository_file_goes_to_the_declared_repository() -> None:
    out = _doc('<a href="../LICENSE">license</a>', _WITH_REPO)
    assert out == f'<a href="{_REPO}/-/blob/{_REF}/LICENSE">license</a>'


def test_a_raw_link_with_nowhere_to_go_keeps_its_text() -> None:
    assert _doc('See <a href="../LICENSE" title="t">the <b>licence</b></a>.') == (
        "See the <b>licence</b>."
    )


def test_a_raw_link_to_a_published_document_reaches_its_page_under_the_base() -> None:
    assert (
        _doc("<a href='./other.md#x'>other</a>") == '<a href="/orders/docs/other.html#x">other</a>'
    )


def test_a_raw_image_with_nowhere_to_go_becomes_its_alt_text() -> None:
    assert _doc('<img src="missing.png" alt="a {{ x }} &amp; y">') == (
        "a {<!---->{ x }} &amp; y"
    )


def test_a_raw_image_the_portal_publishes_is_left_as_written() -> None:
    text = '<img src="./logo.png" alt="logo" width="80">'
    assert _doc(text) == text


def test_a_picture_follows_the_rule_in_every_source() -> None:
    text = (
        '<picture><source media="(prefers-color-scheme: dark)" srcset="../art/dark.png 2x">'
        '<img src="../art/light.png" alt="Logo"></picture>'
    )
    assert _doc(text, _WITH_REPO) == (
        f'<picture><source media="(prefers-color-scheme: dark)" '
        f'srcset="{_REPO}/-/raw/{_REF}/art/dark.png 2x">'
        f'<img src="{_REPO}/-/raw/{_REF}/art/light.png" alt="Logo"></picture>'
    )
    assert _doc(text) == '<picture><source media="(prefers-color-scheme: dark)">Logo</picture>'


def test_an_unclosed_raw_link_is_text_with_its_address_as_written() -> None:
    assert _doc('<a href="../LICENSE">license') == '&lt;a href="../LICENSE">license'


def test_an_inline_element_cannot_close_in_the_next_list_item() -> None:
    assert _inert("- a <b>x\n- y</b> z") == "- a &lt;b>x\n- y&lt;/b> z"


def test_a_tag_inside_a_code_span_after_an_unpartnered_backtick_is_left_as_written() -> None:
    text = "- an ``a `b`, `c``` d. `e`\n- the `<role>.md` file"
    assert _inert(text) == text
