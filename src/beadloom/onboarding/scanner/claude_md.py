"""CLAUDE.md marker-based auto-refresh of auto-managed sections."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Marker patterns for auto-managed sections.
_MARKER_START_RE = re.compile(r"<!--\s*beadloom:auto-start\s+([\w-]+)\s*-->")
_MARKER_END_RE = re.compile(r"<!--\s*beadloom:auto-end\s*-->")

# Pattern to detect section 0.1 heading (for auto-insert).
_SECTION_01_RE = re.compile(r"^##\s+0\.1\s+", re.MULTILINE)


def _parse_markers(text: str) -> list[tuple[str, int, int, str]]:
    """Find all ``beadloom:auto-start`` / ``beadloom:auto-end`` marker pairs.

    Returns list of (section_name, start_pos, end_pos, current_content)
    where start_pos is the beginning of the start-marker line and
    end_pos is one past the end-marker line (suitable for slicing).
    """
    results: list[tuple[str, int, int, str]] = []
    pos = 0
    while pos < len(text):
        start_match = _MARKER_START_RE.search(text, pos)
        if start_match is None:
            break

        # Find the beginning of the start-marker line.
        line_start = text.rfind("\n", 0, start_match.start()) + 1
        content_start = start_match.end()
        # Skip the newline right after the start marker.
        if content_start < len(text) and text[content_start] == "\n":
            content_start += 1

        end_match = _MARKER_END_RE.search(text, content_start)
        if end_match is None:
            # Unclosed marker — skip.
            break

        # end_pos: one past the newline after the end marker.
        end_pos = end_match.end()
        if end_pos < len(text) and text[end_pos] == "\n":
            end_pos += 1

        # Content between markers (excluding the marker lines themselves).
        content_end = end_match.start()
        # Strip trailing newline before end marker.
        if content_end > 0 and text[content_end - 1] == "\n":
            content_end -= 1
        current_content = text[content_start:content_end]

        results.append((start_match.group(1), line_start, end_pos, current_content))
        pos = end_pos

    return results


def _auto_insert_markers(text: str) -> str:
    """If section 0.1 detected but no markers, wrap dynamic facts in markers.

    Finds the ``## 0.1 Project: ...`` heading, then identifies the bullet-list
    block that follows it and wraps it with ``beadloom:auto-start project-info``
    / ``beadloom:auto-end`` markers.  Returns the modified text, or the
    original text unchanged if conditions are not met.
    """
    # Bail out if markers already exist.
    if _MARKER_START_RE.search(text):
        return text

    heading_match = _SECTION_01_RE.search(text)
    if heading_match is None:
        return text

    # Find the end of the heading line.
    heading_line_end = text.find("\n", heading_match.start())
    if heading_line_end == -1:
        heading_line_end = len(text)

    # Skip blank lines between heading and first bullet.
    pos = heading_line_end + 1
    while pos < len(text) and text[pos] == "\n":
        pos += 1

    if pos >= len(text) or text[pos] != "-":
        return text

    # Find the end of the bullet block (contiguous lines starting with '-').
    block_start = pos
    block_end = pos
    while block_end < len(text):
        line_end = text.find("\n", block_end)
        if line_end == -1:
            line_end = len(text)
        line = text[block_end:line_end].strip()
        if not line.startswith("-"):
            break
        block_end = line_end + 1 if line_end < len(text) else line_end

    bullet_content = text[block_start:block_end]
    # Build replacement with markers.
    replacement = (
        f"<!-- beadloom:auto-start project-info -->\n{bullet_content}<!-- beadloom:auto-end -->\n"
    )

    return text[:block_start] + replacement + text[block_end:]


def _render_project_info_section(project_root: Path) -> str:
    """Generate the content for the ``project-info`` section.

    Uses actual project state: version, packages, stack info.
    The returned string does NOT include the marker comments — only
    the bullet-list content that goes between markers.
    """
    from beadloom.application.doctor import _get_actual_packages, get_actual_version

    version = get_actual_version()

    # Discover DDD packages under src/<project_name>/.
    # We look for any subdirectory under src/ that has __init__.py children.
    packages: set[str] = set()
    src_dir = project_root / "src"
    if src_dir.is_dir():
        for pkg_root in src_dir.iterdir():
            if pkg_root.is_dir() and (pkg_root / "__init__.py").is_file():
                for child in pkg_root.iterdir():
                    if child.is_dir() and (child / "__init__.py").is_file():
                        packages.add(child.name)
    # Fallback: try the doctor helper (beadloom-specific).
    if not packages:
        packages = _get_actual_packages(project_root)

    # Read pyproject.toml for additional metadata.
    pyproject_path = project_root / "pyproject.toml"
    pyproject_text = ""
    if pyproject_path.is_file():
        import contextlib

        with contextlib.suppress(OSError):
            pyproject_text = pyproject_path.read_text(encoding="utf-8")

    # Build bullet lines.
    lines: list[str] = []

    # Stack line — extract from pyproject deps if possible, else generic.
    stack_parts: list[str] = []
    dep_lower = pyproject_text.lower()
    if "python" in dep_lower:
        stack_parts.append("Python 3.10+")
    if "sqlite" in dep_lower or "sqlite3" in dep_lower:
        stack_parts.append("SQLite")
    if "click" in dep_lower:
        stack_parts.append("Click")
    if "rich" in dep_lower:
        stack_parts.append("Rich")
    if "tree-sitter" in dep_lower or "tree_sitter" in dep_lower:
        stack_parts.append("tree-sitter")
    if stack_parts:
        lines.append(f"- **Stack:** {', '.join(stack_parts)}")

    # Tests line.
    if "pytest" in dep_lower:
        cov = ""
        if "pytest-cov" in dep_lower:
            cov = " + pytest-cov"
        lines.append(f"- **Tests:** pytest{cov}")

    # Linter.
    if "ruff" in dep_lower:
        lines.append("- **Linter/formatter:** ruff (lint + format)")

    # Type checking.
    if "mypy" in dep_lower:
        lines.append("- **Type checking:** mypy --strict")

    # Architecture packages.
    if packages:
        pkg_list = ", ".join(f"`{p}/`" for p in sorted(packages))
        lines.append(f"- **Architecture:** DDD packages -- {pkg_list}")

    # Version.
    lines.append(f"- **Current version:** {version}")

    return "\n".join(lines) + "\n"


def refresh_claude_md(
    project_root: Path,
    *,
    dry_run: bool = False,
) -> list[str]:
    """Refresh auto-managed sections in ``.claude/CLAUDE.md``.

    Reads the file, finds ``<!-- beadloom:auto-start SECTION -->`` /
    ``<!-- beadloom:auto-end -->`` marker pairs, regenerates their content,
    and writes back.  Content outside markers is preserved verbatim.

    Parameters
    ----------
    project_root:
        Root of the project (where ``.claude/`` lives).
    dry_run:
        When *True*, return changed section names without writing the file.

    Returns
    -------
    list[str]
        Names of sections whose content changed (empty if nothing changed
        or file does not exist).
    """
    claude_md_path = project_root / ".claude" / "CLAUDE.md"
    if not claude_md_path.is_file():
        return []

    try:
        text = claude_md_path.read_text(encoding="utf-8")
    except OSError:
        return []

    # If no markers but section 0.1 is present, auto-insert markers first.
    markers = _parse_markers(text)
    if not markers and _SECTION_01_RE.search(text):
        text = _auto_insert_markers(text)
        markers = _parse_markers(text)

    if not markers:
        return []

    # Renderers for each known section.
    renderers: dict[str, str] = {}
    for section_name, _start, _end, _content in markers:
        if section_name == "project-info":
            renderers[section_name] = _render_project_info_section(project_root)

    # Rebuild the text, replacing changed sections.
    changed: list[str] = []
    # Process markers in reverse order so positions remain valid.
    for section_name, start, end, current_content in reversed(markers):
        new_content = renderers.get(section_name)
        if new_content is None:
            continue  # Unknown section — leave as is.

        # Normalize for comparison: strip trailing whitespace.
        if new_content.rstrip() == current_content.rstrip():
            continue

        changed.append(section_name)
        # Build replacement block.
        replacement = (
            f"<!-- beadloom:auto-start {section_name} -->\n"
            f"{new_content}"
            f"<!-- beadloom:auto-end -->\n"
        )
        text = text[:start] + replacement + text[end:]

    if not changed:
        return []

    if not dry_run:
        claude_md_path.write_text(text, encoding="utf-8")

    return changed
