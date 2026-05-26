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


# ---------------------------------------------------------------------------
# BDL-046 BEAD-06 — holistic edge-case hardening (adversarial inputs)
# ---------------------------------------------------------------------------


def test_github_and_external_outputs_are_round_trip_stable() -> None:
    """GitHub-blob + external + dropped outputs are stable under a second pass.

    The fallback (``{repo}/blob/main/...``) and external URLs both start with a
    scheme, so a second pass leaves them untouched — those rewrites round-trip.
    (The ``/docs/<slug>`` site link does NOT round-trip; see the next test — it
    is a documented one-way transform applied once during generation.)
    """
    text = (
        "the [license](LICENSE), the [draft](docs/draft.md), "
        "and [site](https://example.com).\n"
    )
    once = render_about(text, published_doc_slugs={"getting-started"}, repo_url=_REPO)
    twice = render_about(once, published_doc_slugs={"getting-started"}, repo_url=_REPO)
    assert twice == once


def test_published_site_link_is_a_one_way_transform() -> None:
    """``docs/<slug>.md`` -> ``/docs/<slug>`` is applied once, not round-trip-safe.

    On a second pass the leading-``/`` ``/docs/<slug>`` is an absolute-internal
    path (it does NOT start with ``docs/``), so it falls through to the GitHub
    blob fallback. ``site.py`` applies the transform exactly once on the raw
    README, so this is correct in practice — documented here so a refactor that
    accidentally double-applies it is caught.
    """
    once = render_about(
        "[guide](docs/getting-started.md)",
        published_doc_slugs={"getting-started"},
        repo_url=_REPO,
    )
    assert once == "[guide](/docs/getting-started)"
    twice = render_about(once, published_doc_slugs={"getting-started"}, repo_url=_REPO)
    assert twice == f"[guide]({_REPO}/blob/main//docs/getting-started)"


def test_already_rebased_site_link_is_left_untouched() -> None:
    """A ``/docs/<slug>`` site link (no http scheme, starts with /) is not docs/-relative.

    It does not start with ``docs/`` (it starts with ``/docs/``), so it is an
    unknown internal link — but it must NOT be doubled into the GitHub blob URL
    on a second pass; the rebaser routes it to the GitHub fallback exactly once.
    """
    out = render_about(
        "[guide](/docs/getting-started)",
        published_doc_slugs={"getting-started"},
        repo_url=_REPO,
    )
    # Leading-/ absolute-internal links fall through to the GitHub blob URL.
    assert out == f"[guide]({_REPO}/blob/main//docs/getting-started)"


def test_readme_cross_link_image_drops_link_keeps_alt() -> None:
    """An image whose target is a README cross-link drops to its alt text."""
    out = render_about(
        "![English](README.md)",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == "English"


def test_readme_cross_link_case_insensitive() -> None:
    """README cross-link matching is case-insensitive (``Readme.MD``)."""
    out = render_about(
        "[en](Readme.MD) and [ru](README.RU.MD)",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == "en and ru"


def test_readme_cross_link_with_dot_slash_dropped() -> None:
    """A leading ``./`` before a README cross-link is stripped before matching."""
    out = render_about(
        "Read in [Russian](./README.ru.md).",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == "Read in Russian."


def test_nested_docs_subpath_published_slug() -> None:
    """A published nested slug (``domains/application``) rebases extension-less."""
    out = render_about(
        "[app](docs/domains/application.md)",
        published_doc_slugs={"domains/application"},
        repo_url=_REPO,
    )
    assert out == "[app](/docs/domains/application)"


def test_reference_style_link_left_untouched() -> None:
    """Reference-style links (``[text][ref]`` + a separate definition) are not
    inline ``[text](target)`` links, so the rebaser leaves them verbatim."""
    text = "See [the guide][gs].\n\n[gs]: docs/getting-started.md\n"
    out = render_about(text, published_doc_slugs={"getting-started"}, repo_url=_REPO)
    assert out == text


def test_protocol_relative_url_treated_as_internal() -> None:
    """A ``//host/...`` URL has no http/https scheme, so it is rebased (defensive:
    READMEs use explicit schemes; this documents the no-scheme behaviour)."""
    out = render_about(
        "[cdn](//cdn.example.com/x.png)",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == f"[cdn]({_REPO}/blob/main///cdn.example.com/x.png)"


def test_empty_input_returns_empty() -> None:
    assert render_about("", published_doc_slugs=set(), repo_url=_REPO) == ""


def test_prose_with_no_links_unchanged() -> None:
    text = "# Title\n\nJust prose, a (parenthetical), and [unclosed bracket.\n"
    out = render_about(text, published_doc_slugs={"x"}, repo_url=_REPO)
    assert out == text


def test_link_inside_double_backtick_span_untouched() -> None:
    """A two-backtick code span protects its contents from rewriting."""
    text = "Use ``[x](LICENSE)`` literally."
    out = render_about(text, published_doc_slugs=set(), repo_url=_REPO)
    assert out == text


def test_link_outside_code_span_rewritten_while_span_protected() -> None:
    """A real link is rebased even when a protected span sits on the same line."""
    out = render_about(
        "Run `[x](LICENSE)` then see [license](LICENSE).",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == f"Run `[x](LICENSE)` then see [license]({_REPO}/blob/main/LICENSE)."


def test_multiple_fenced_blocks_protected_prose_between_rewritten() -> None:
    """Prose between two fenced blocks is rewritten; both fences stay verbatim."""
    text = (
        "```\n[a](LICENSE)\n```\n"
        "See [lic](LICENSE).\n"
        "```\n[b](docs/x.md)\n```\n"
    )
    out = render_about(text, published_doc_slugs={"x"}, repo_url=_REPO)
    expected = (
        "```\n[a](LICENSE)\n```\n"
        f"See [lic]({_REPO}/blob/main/LICENSE).\n"
        "```\n[b](docs/x.md)\n```\n"
    )
    assert out == expected


def test_target_with_surrounding_whitespace_trimmed() -> None:
    """A target padded with spaces is trimmed before classification (anchor here)."""
    text = "Jump [here](  #usage  )."
    out = render_about(text, published_doc_slugs=set(), repo_url=_REPO)
    # Anchors are left untouched (original target preserved verbatim).
    assert out == text


def test_image_with_empty_alt_rebased() -> None:
    out = render_about(
        "![](docs/assets/x.png)",
        published_doc_slugs=set(),
        repo_url=_REPO,
    )
    assert out == f"![]({_REPO}/blob/main/docs/assets/x.png)"
