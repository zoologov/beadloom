"""README -> VitePress About page transform (BDL-046 BEAD-01).

:func:`render_about` rebases a README's Markdown link/image targets so they
resolve on the published VitePress site, while leaving prose, code spans, and
fenced code blocks untouched. It is pure and deterministic: no I/O, no DB,
same input -> same output.

Rebasing rules (applied to both ``[text](target)`` links and
``![alt](target)`` images):

- ``docs/<x>.md`` / ``docs/<x>`` whose slug ``<x>`` is published ->
  extension-less site link ``/docs/<x>``.
- ``README.ru.md`` / ``README.md`` cross-links -> link dropped, visible text
  kept (the VitePress locale switcher handles language).
- any other internal/relative target (``LICENSE``, source paths, an
  unpublished ``docs/<x>``) -> absolute GitHub URL
  ``{repo_url}/blob/main/<path>`` (a leading ``./`` is stripped).
- already-absolute URLs (http/https, including shields.io badges) and pure
  anchors (``#section``) -> unchanged.

Links inside inline code spans (``` `...` ```) and fenced code blocks
(```` ``` ````) are never rewritten.

The badge-link idiom ``[![alt](img)](target)`` (an image used as link text) is
handled too: the OUTER link ``target`` is rebased by the rules above, and the
INNER image is recursed through the same rules (so an absolute shields.io badge
URL stays untouched while a relative inner target would also be rebased).
"""

# beadloom:domain=application

from __future__ import annotations

import re

# Inline link/image:  optional leading "!" (image), [text], (target).
# The text group may itself contain a complete nested image — the badge-link
# idiom ``[![alt](img)](target)`` — so we allow either plain text (no brackets)
# or a whole ``![alt](url)`` token inside it. The target group stops at the
# first ")" — sufficient for README-style targets (no parenthesised titles).
_LINK_RE = re.compile(r"(!?)\[((?:[^\[\]]|!\[[^\]]*\]\([^)]*\))*)\]\(([^)]*)\)")

# Code spans and fenced blocks: protected regions we must not rewrite.
# Fenced blocks first (greedier) so they win over inline-span matching.
_PROTECT_RE = re.compile(r"(```.*?```|``.*?``|`[^`]*`)", re.DOTALL)

_README_CROSS_LINKS = frozenset({"readme.md", "readme.ru.md"})


def render_about(
    readme_text: str,
    *,
    published_doc_slugs: set[str],
    repo_url: str,
) -> str:
    """Transform README Markdown into the About-page body (link rebasing)."""
    segments = _PROTECT_RE.split(readme_text)
    # re.split with one capture group yields: prose, code, prose, code, ...
    # even indices are prose (rewrite); odd indices are protected (keep).
    out: list[str] = []
    for index, segment in enumerate(segments):
        if index % 2 == 1:
            out.append(segment)
        else:
            out.append(_rewrite_prose(segment, published_doc_slugs, repo_url))
    return "".join(out)


def _rewrite_prose(
    prose: str,
    published_doc_slugs: set[str],
    repo_url: str,
) -> str:
    def replace(match: re.Match[str]) -> str:
        bang, text, target = match.group(1), match.group(2), match.group(3)
        return _rebase_one(bang, text, target, published_doc_slugs, repo_url)

    return _LINK_RE.sub(replace, prose)


def _rebase_one(
    bang: str,
    text: str,
    target: str,
    published_doc_slugs: set[str],
    repo_url: str,
) -> str:
    # Badge-link idiom: the visible text is itself a nested image. Rebase its
    # (possibly relative) target by recursing through the prose rewriter so the
    # inner and outer targets are both handled by the same rules.
    if "![" in text:
        text = _rewrite_prose(text, published_doc_slugs, repo_url)

    stripped = target.strip()
    if _is_absolute_or_anchor(stripped):
        return f"{bang}[{text}]({target})"

    path = stripped[2:] if stripped.startswith("./") else stripped

    if path.lower() in _README_CROSS_LINKS:
        # Drop the link, keep the visible text (locale switcher handles this).
        return text

    site_link = _published_site_link(path, published_doc_slugs)
    if site_link is not None:
        return f"{bang}[{text}]({site_link})"

    return f"{bang}[{text}]({repo_url}/blob/main/{path})"


def _is_absolute_or_anchor(target: str) -> bool:
    return (
        target.startswith(("http://", "https://"))
        or target.startswith("#")
    )


def _published_site_link(
    path: str,
    published_doc_slugs: set[str],
) -> str | None:
    """Return ``/docs/<slug>`` if ``path`` is a published docs link, else None."""
    if not path.startswith("docs/"):
        return None
    rest = path[len("docs/") :]
    slug = rest[: -len(".md")] if rest.endswith(".md") else rest
    if slug in published_doc_slugs:
        return f"/docs/{slug}"
    return None
