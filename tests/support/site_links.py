"""Links in the generated site and its data files, and whether each one resolves."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

# Markdown inline links: capture the URL inside (...). Excludes images is not
# needed here (the generator emits no images).
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _is_external(url: str) -> bool:
    """A link VitePress does not resolve against the emitted tree."""
    return "://" in url or url.startswith(("#", "mailto:", "tel:")) or url.strip() == ""


def _resolve_target(out: Path, page: Path, url: str) -> Path | None:
    """The file a markdown *url* on *page* should resolve to in the site tree.

    Mirrors VitePress link resolution: absolute (`/foo`) roots at the site root,
    relative resolves against the page's directory, a trailing `/` means the
    directory's `index.md`, and the `.md` suffix is optional (clean URLs).
    Returns ``None`` for external/anchor links (not our concern).
    """
    raw = url.split("#", 1)[0].split("?", 1)[0]
    if _is_external(raw):
        return None
    base = PurePosixPath(page.relative_to(out).as_posix()).parent
    target = PurePosixPath(raw.lstrip("/")) if raw.startswith("/") else base / raw
    # Directory link -> index page.
    if raw.endswith("/"):
        target = target / "index"
    # Try the path as-is, with .md, and as a dir index (clean-URL forms).
    candidates = [target, target.with_suffix(".md")]
    if target.suffix == "":
        candidates.append(target / "index.md")
    for cand in candidates:
        resolved = out / PurePosixPath(*cand.parts)
        if resolved.exists():
            return resolved
    return out / PurePosixPath(*target.parts)  # report the primary miss


# Directories VitePress does not render (so they are not part of the content
# tree whose links must resolve): the node toolchain and build/config dirs.
_NON_CONTENT_DIRS = frozenset({"node_modules", ".vitepress", "dist"})


def dead_links(out: Path) -> list[tuple[str, str]]:
    """Every internal markdown link in the *content* tree whose target is missing.

    Only the rendered content tree is walked (``node_modules`` / ``.vitepress``
    are excluded — VitePress does not render them). Links inside fenced code
    blocks (e.g. Mermaid ``click`` directives) AND inline code spans (e.g. a doc
    that shows ``[text](README.ru.md)`` syntax as an example) are ignored — they
    are not rendered as markdown links, so they cannot be dead.
    """
    dead: list[tuple[str, str]] = []
    for md in sorted(out.rglob("*.md")):
        if any(part in _NON_CONTENT_DIRS for part in md.relative_to(out).parts):
            continue
        body = md.read_text(encoding="utf-8")
        in_fence = False
        for line in body.splitlines():
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            # Strip inline code spans (`` `...` `` / ``` ``...`` ```) — link-like
            # syntax inside them is illustrative, not a real link (mirrors the
            # code-span protection in application/site_about.render_about).
            line = re.sub(r"``[^`]+``|`[^`]+`", "", line)
            for url in _LINK_RE.findall(line):
                resolved = _resolve_target(out, md, url)
                if resolved is not None and not resolved.exists():
                    dead.append((str(md.relative_to(out)), url))
    return dead


def iter_data_links(data: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield ``(owner_id, url)`` for every runtime link the payload carries."""
    for node in data.get("nodes", []):
        if node.get("url"):
            yield node["id"], node["url"]
        for link in node.get("doc_links", []):
            yield node["id"], link


def link_target_exists(site: Path, url: str) -> bool:
    """Resolve a site-absolute viz link against the generated tree.

    The payload carries what the BUILT site serves — a node page as an
    extension-less clean URL (``/domains/graph``) and a published doc as
    ``.html`` (``/docs/.../SPEC.html``) — while the generator writes markdown.
    Both forms therefore map back onto ``.md``.
    """
    raw = url.split("#", 1)[0].split("?", 1)[0]
    if not raw.startswith("/"):
        return False
    target = PurePosixPath(raw.lstrip("/"))
    if target.suffix == ".html":
        target = target.with_suffix(".md")
    candidates = [target, target.with_suffix(".md"), target / "index.md"]
    return any((site / PurePosixPath(*c.parts)).exists() for c in candidates)
