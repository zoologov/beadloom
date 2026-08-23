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


#: How each supported architecture names its top-level units. A project that
#: declares none gets the neutral word: claiming a methodology the project never
#: chose is the same defect as claiming a version it never declared.
_ARCHITECTURE_UNITS: dict[str, str] = {
    "ddd": "DDD packages",
    "fsd": "FSD slices",
}

#: Display names for the stack overlays. Anything unmapped is rendered as the
#: declared tag itself rather than guessed at.
_STACK_NAMES: dict[str, str] = {
    "python": "Python",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "vuejs": "Vue.js",
}


def _declared_flow(project_root: Path) -> tuple[str | None, tuple[str, ...]]:
    """The architecture and stack THIS project declares in ``flow.yml``.

    ``(None, ())`` when the project declares nothing — the renderer then omits
    the claim rather than falling back to Beadloom's own answer.
    """
    from beadloom.onboarding.flow_config import load_flow_config

    try:
        config = load_flow_config(project_root)
    except (FileNotFoundError, ValueError):
        return None, ()
    return config.architecture, config.stack


def _render_project_info_section(project_root: Path) -> str:
    """Generate the content for the ``project-info`` section.

    Every bullet is a fact read out of **the target project** — its own
    manifest, its own ``src/`` layout, its own ``flow.yml``. A fact that cannot
    be read is omitted, never substituted: until BDL-UX #183 this function
    rendered ``get_actual_version()`` (Beadloom's ``__version__``) as the
    project's version, which read correctly on exactly one repository in the
    world and was false on every other.

    The returned string does NOT include the marker comments — only the
    bullet-list content that goes between markers.
    """
    from beadloom.onboarding.scanner.project_facts import (
        detect_declared_dependencies,
        detect_project_version,
        detect_requires_python,
        detect_source_packages,
        manifest_text,
    )

    architecture, stack = _declared_flow(project_root)
    manifest = manifest_text(project_root) or ""
    dep_lower = manifest.lower()
    lines: list[str] = []

    stack_parts = [_STACK_NAMES.get(name, name) for name in stack]
    requires_python = detect_requires_python(project_root)
    if requires_python is not None and stack_parts:
        stack_parts = [
            f"{part} ({requires_python})" if part == "Python" else part
            for part in stack_parts
        ]
    if stack_parts:
        dependencies = detect_declared_dependencies(project_root)
        detail = f" — {', '.join(dependencies)}" if dependencies else ""
        lines.append(f"- **Stack:** {', '.join(stack_parts)}{detail}")

    if "pytest" in dep_lower:
        cov = " + pytest-cov" if "pytest-cov" in dep_lower else ""
        lines.append(f"- **Tests:** pytest{cov}")
    if "ruff" in dep_lower:
        lines.append("- **Linter/formatter:** ruff (lint + format)")
    if "mypy" in dep_lower:
        lines.append("- **Type checking:** mypy --strict")

    packages = detect_source_packages(project_root)
    if packages:
        pkg_list = ", ".join(f"`{p}/`" for p in sorted(packages))
        units = _ARCHITECTURE_UNITS.get(architecture or "", "packages")
        lines.append(f"- **Architecture:** {units} -- {pkg_list}")

    version = detect_project_version(project_root)
    if version is not None:
        lines.append(f"- **Current version:** {version}")

    if not lines:
        # Unverifiable is not clean (BDL-061 S2b): an empty region reads as
        # "this project has no facts", which is a claim. Say what was looked at.
        lines.append(
            "- _No project facts read: Beadloom found no `pyproject.toml`, "
            "`package.json` or `Cargo.toml`, and no `.beadloom/flow.yml` "
            "declaring a stack._"
        )

    return "\n".join(lines) + "\n"


#: Display names for the language tags we can name; anything else is shown as
#: the tag itself rather than guessed at (BDL-UX #136).
_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "ru": "Russian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "it": "Italian",
    "pl": "Polish",
    "uk": "Ukrainian",
    "tr": "Turkish",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}


def _render_doc_language_section(project_root: Path) -> str:
    """The ``doc-language`` auto-region — derived from ``flow.yml``, not hardcoded.

    The scaffolded flow used to state "ALL documents MUST be written in English"
    as an unconditional core rule, so a team documenting in another language had
    to override the shipped default in prose (BDL-UX #136). The language is now a
    declared field and this sentence follows it.
    """
    from beadloom.onboarding.flow_config import DEFAULT_LANGUAGE, load_flow_config

    try:
        language = load_flow_config(project_root).language
    except (FileNotFoundError, ValueError):
        # No flow.yml (or an invalid one, reported by config-check) — state the
        # default rather than inventing a language for the project.
        language = DEFAULT_LANGUAGE
    name = _LANGUAGE_NAMES.get(language.split("-")[0], language)
    return (
        f"**Document language:** ALL documents (PRD, RFC, CONTEXT, PLAN, ACTIVE, "
        f"BRIEF) MUST be written in {name} — set by `language: {language}` in "
        "`.beadloom/flow.yml`.\n"
    )


def blank_auto_regions(text: str) -> str:
    """Replace every auto-managed region's BODY with a fixed token.

    The auto-regions are regenerated per project (version, packages, stack), so
    comparing them against a composition would report drift on facts that are
    supposed to move. Blanking them leaves exactly the composed part to compare,
    which is what ``config-check`` verifies; the regions themselves are checked
    separately by :func:`refresh_claude_md` in dry-run mode.
    """
    markers = _parse_markers(text)
    if not markers:
        return text
    out: list[str] = []
    cursor = 0
    for name, start, end, _content in markers:
        out.append(text[cursor:start])
        out.append(f"<!-- beadloom:auto-region {name} -->\n")
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


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
        elif section_name == "doc-language":
            renderers[section_name] = _render_doc_language_section(project_root)

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
