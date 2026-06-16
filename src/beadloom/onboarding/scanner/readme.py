"""README / documentation metadata ingestion (description, tech stack, notes)."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Technology keywords for README scanning (lowercase).
_TECH_KEYWORDS = frozenset(
    {
        "python",
        "javascript",
        "typescript",
        "react",
        "vue",
        "angular",
        "django",
        "flask",
        "fastapi",
        "express",
        "nestjs",
        "nextjs",
        "docker",
        "kubernetes",
        "postgres",
        "mysql",
        "redis",
        "mongodb",
        "graphql",
        "rest",
        "grpc",
        "golang",
        "rust",
        "swift",
        "kotlin",
        "java",
        "spring",
        "aws",
        "gcp",
        "azure",
        "terraform",
        "node",
        "deno",
        "bun",
        "vite",
        "webpack",
    }
)


def _extract_first_paragraph(text: str) -> str:
    """Extract the first non-heading, non-empty paragraph from markdown text."""
    lines = text.splitlines()
    paragraph_lines: list[str] = []
    found_content = False

    for line in lines:
        stripped = line.strip()
        # Skip blank lines before finding content.
        if not stripped:
            if found_content:
                break
            continue
        # Skip heading lines.
        if stripped.startswith("#"):
            if found_content:
                break
            continue
        # Found a content line.
        found_content = True
        paragraph_lines.append(stripped)

    return " ".join(paragraph_lines)


def _detect_tech_stack(text: str) -> list[str]:
    """Detect technology keywords in text using word boundary matching."""
    found: list[str] = []
    text_lower = text.lower()
    for kw in sorted(_TECH_KEYWORDS):
        if re.search(rf"\b{re.escape(kw)}\b", text_lower):
            found.append(kw)
    return found


def _extract_non_heading_content(text: str, max_chars: int) -> str:
    """Extract non-heading content from markdown, truncated to max_chars."""
    lines = text.splitlines()
    content_lines: list[str] = []
    total = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        content_lines.append(stripped)
        total += len(stripped) + 1  # +1 for joining space
        if total >= max_chars:
            break

    result = " ".join(content_lines)
    return result[:max_chars]


def _ingest_readme(project_root: Path) -> dict[str, str | list[str]]:
    """Extract project metadata from README and documentation files.

    Parses: README.md, CONTRIBUTING.md, ARCHITECTURE.md, docs/README.md

    Returns dict with:
    - readme_description: first non-heading paragraph from README
    - tech_stack: list of detected technology mentions
    - architecture_notes: summary from ARCHITECTURE.md if present
    """
    result: dict[str, str | list[str]] = {}

    # Find README content — try root first, then docs/README.md.
    readme_text = ""
    for readme_path in [
        project_root / "README.md",
        project_root / "docs" / "README.md",
    ]:
        if readme_path.is_file():
            readme_text = readme_path.read_text(encoding="utf-8")
            break

    if readme_text:
        # Extract first paragraph.
        desc = _extract_first_paragraph(readme_text)
        if desc:
            result["readme_description"] = desc

        # Detect tech stack from all readme content.
        tech = _detect_tech_stack(readme_text)
        if tech:
            result["tech_stack"] = tech

    # Also scan CONTRIBUTING.md for tech keywords.
    contributing_path = project_root / "CONTRIBUTING.md"
    if contributing_path.is_file():
        contrib_text = contributing_path.read_text(encoding="utf-8")
        extra_tech = _detect_tech_stack(contrib_text)
        existing_tech = list(result.get("tech_stack", []))
        merged = sorted(set(existing_tech) | set(extra_tech))
        if merged:
            result["tech_stack"] = merged

    # Extract architecture notes.
    arch_path = project_root / "ARCHITECTURE.md"
    if arch_path.is_file():
        arch_text = arch_path.read_text(encoding="utf-8")
        notes = _extract_non_heading_content(arch_text, 500)
        if notes:
            result["architecture_notes"] = notes

    return result
