"""Tests for beadloom.application.site_about — README -> About transform.

BDL-046 BEAD-01: ``render_about`` rebases a README's Markdown link/image
targets so they resolve on the published VitePress site, leaving prose and
code spans/fences untouched. Pure + deterministic (no I/O, no DB).

Rebasing table:
- ``docs/<x>.md`` (or ``docs/<x>``) with ``<x>`` published -> ``/docs/<x>``.
- ``README.ru.md`` / ``README.md`` cross-links -> drop link, keep text.
- other internal/relative targets -> ``{repo_url}/blob/main/<path>``.
- absolute URLs (http/https, shields badges) + pure anchors -> unchanged.
"""

from __future__ import annotations

from beadloom.application.site_about import render_about

_REPO = "https://github.com/zoologov/beadloom"


def test_published_doc_link_becomes_extensionless_site_link() -> None:
    out = render_about(
        "See [the guide](docs/getting-started.md) here.",
        published_doc_slugs={"getting-started"},
        repo_url=_REPO,
    )
    assert out == "See [the guide](/docs/getting-started) here."


def test_published_doc_link_without_extension() -> None:
    out = render_about(
        "[guide](docs/getting-started)",
        published_doc_slugs={"getting-started"},
        repo_url=_REPO,
    )
    assert out == "[guide](/docs/getting-started)"


def test_published_doc_link_strips_leading_dot_slash() -> None:
    out = render_about(
        "[guide](./docs/getting-started.md)",
        published_doc_slugs={"getting-started"},
        repo_url=_REPO,
    )
    assert out == "[guide](/docs/getting-started)"


def test_readme_ru_cross_link_dropped_keeps_text() -> None:
    out = render_about(
        "Read this in [Russian](README.ru.md).",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == "Read this in Russian."


def test_readme_en_cross_link_dropped_keeps_text() -> None:
    out = render_about(
        "Read this in [English](README.md).",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == "Read this in English."


def test_unknown_internal_link_becomes_absolute_github_url() -> None:
    out = render_about(
        "See the [license](LICENSE) file.",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == f"See the [license]({_REPO}/blob/main/LICENSE) file."


def test_unpublished_docs_link_falls_back_to_github_url() -> None:
    out = render_about(
        "[draft](docs/draft.md)",
        published_doc_slugs={"getting-started"},
        repo_url=_REPO,
    )
    assert out == f"[draft]({_REPO}/blob/main/docs/draft.md)"


def test_relative_source_path_with_dot_slash_becomes_github_url() -> None:
    out = render_about(
        "[code](./src/beadloom/cli.py)",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == f"[code]({_REPO}/blob/main/src/beadloom/cli.py)"


def test_absolute_http_url_unchanged() -> None:
    text = "See [the site](https://example.com/page)."
    out = render_about(text, published_doc_slugs=set(), repo_url=_REPO)
    assert out == text


def test_shields_badge_image_unchanged() -> None:
    text = "![build](https://img.shields.io/badge/build-passing-green)"
    out = render_about(text, published_doc_slugs=set(), repo_url=_REPO)
    assert out == text


def test_pure_anchor_link_unchanged() -> None:
    text = "Jump to [usage](#usage)."
    out = render_about(text, published_doc_slugs=set(), repo_url=_REPO)
    assert out == text


def test_image_target_rebased_to_github_url() -> None:
    out = render_about(
        "![diagram](docs/assets/arch.png)",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == f"![diagram]({_REPO}/blob/main/docs/assets/arch.png)"


def test_image_target_published_doc_rebased() -> None:
    out = render_about(
        "![g](docs/getting-started.md)",
        published_doc_slugs={"getting-started"},
        repo_url=_REPO,
    )
    assert out == "![g](/docs/getting-started)"


def test_links_inside_inline_code_not_rewritten() -> None:
    text = "Run `[x](LICENSE)` to see it."
    out = render_about(text, published_doc_slugs=set(), repo_url=_REPO)
    assert out == text


def test_links_inside_fenced_code_not_rewritten() -> None:
    text = "```\n[x](LICENSE)\n![y](docs/a.md)\n```\n"
    out = render_about(text, published_doc_slugs={"a"}, repo_url=_REPO)
    assert out == text


def test_prose_untouched_and_multiple_links() -> None:
    text = (
        "# Beadloom\n\n"
        "A tool. See [guide](docs/getting-started.md), "
        "the [license](LICENSE), and [site](https://example.com).\n"
    )
    out = render_about(
        text, published_doc_slugs={"getting-started"}, repo_url=_REPO
    )
    expected = (
        "# Beadloom\n\n"
        "A tool. See [guide](/docs/getting-started), "
        f"the [license]({_REPO}/blob/main/LICENSE), "
        "and [site](https://example.com).\n"
    )
    assert out == expected


def test_deterministic_repeated_calls() -> None:
    text = "[guide](docs/getting-started.md) [lic](LICENSE)"
    first = render_about(
        text, published_doc_slugs={"getting-started"}, repo_url=_REPO
    )
    second = render_about(
        text, published_doc_slugs={"getting-started"}, repo_url=_REPO
    )
    assert first == second
