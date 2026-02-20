"""Document scanner: extracts numeric fact mentions from markdown files.

Scans markdown documentation for numbers and version strings, matching them
to known fact types via keyword-proximity analysis.  Used by the docs-audit
feature to detect stale numeric claims in documentation.
"""

# beadloom:feature=docs-audit

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class Mention:
    """A numeric fact mention found in a markdown file."""

    fact_name: str
    value: str | int
    file: Path
    line: int
    context: str


# ---------------------------------------------------------------------------
# False-positive filter patterns
# ---------------------------------------------------------------------------

# ISO date: 2026-02-19
_DATE_ISO_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

# Month-year patterns: Feb 2026, February 2026
_DATE_MONTH_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{4}\b",
    re.IGNORECASE,
)

# Issue IDs: #123, BDL-021
_ISSUE_HASH_RE = re.compile(r"#\d+")
_ISSUE_PREFIX_RE = re.compile(r"[A-Z]+-\d+")

# Hex colors: #FF0000, #abc, #12345678
_HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")

# Hex literals: 0xFF, 0x1a2b
_HEX_LITERAL_RE = re.compile(r"0x[0-9a-fA-F]+\b")

# Version pinning: >=0.80, ^1.2.3, ~=1.0, <=2.0, <3.0, >1.0, ==1.0, !=1.0
_VERSION_PIN_RE = re.compile(r"(?:>=|<=|~=|!=|==|\^|[<>])\s*\d+(?:\.\d+)*")

# Line number references: file.py:15, line 42, L42
_LINE_REF_COLON_RE = re.compile(r":\d+\b")
_LINE_REF_WORD_RE = re.compile(r"\bline\s+\d+\b", re.IGNORECASE)
_LINE_REF_L_RE = re.compile(r"\bL\d+\b")

# Semantic version: v1.2.3, 1.7.0
_VERSION_RE = re.compile(r"\bv?\d+\.\d+\.\d+\b")

# Standalone 4-digit year: 2000-2099
_YEAR_STANDALONE_RE = re.compile(r"\b20[0-9]{2}\b")

# Bare number (integer) in text
_NUMBER_RE = re.compile(r"\b\d+\b")

# Directories to always exclude from path resolution
_EXCLUDE_DIRS = frozenset({"node_modules", ".git", "__pycache__", ".venv", "venv"})

# Glob patterns for files to exclude by default
_EXCLUDE_PATTERNS = (
    "_graph/features/*/SPEC.md",
    ".beadloom/_graph/features/*/SPEC.md",
)


class DocScanner:
    """Scans markdown files for fact mentions using keyword proximity."""

    FACT_KEYWORDS: ClassVar[dict[str, list[str]]] = {
        "version": [],  # special: handled by _VERSION_RE
        "language_count": ["language", "lang", "programming language"],
        "mcp_tool_count": ["MCP", "tool", "server tool"],
        "cli_command_count": ["command", "CLI", "subcommand"],
        "rule_type_count": ["rule type", "rule kind", "rule"],
        "node_count": ["node", "module", "domain", "component"],
        "edge_count": ["edge", "dependency", "connection"],
        "test_count": ["test", "spec", "assertion"],
        "framework_count": ["framework", "supported framework"],
    }

    PROXIMITY_WINDOW: ClassVar[int] = 5

    def scan(self, paths: list[Path]) -> list[Mention]:
        """Scan multiple markdown files for fact mentions."""
        mentions: list[Mention] = []
        for path in paths:
            mentions.extend(self.scan_file(path))
        return mentions

    def scan_file(self, file_path: Path) -> list[Mention]:
        """Extract fact mentions from a single markdown file."""
        if not file_path.is_file():
            return []

        content = file_path.read_text(encoding="utf-8")
        if not content.strip():
            return []

        mentions: list[Mention] = []
        in_code_block = False

        for line_num, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()

            # Track code block state
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            # Extract version strings (special handling, no proximity needed)
            mentions.extend(self._extract_versions(line, file_path, line_num))

            # Extract number-based mentions via keyword proximity
            mentions.extend(self._extract_number_mentions(line, file_path, line_num))

        return mentions

    def _extract_versions(
        self, line: str, file_path: Path, line_num: int
    ) -> list[Mention]:
        """Extract semantic version strings from a line."""
        results: list[Mention] = []
        cleaned = self._mask_false_positives(line)

        for match in _VERSION_RE.finditer(cleaned):
            version_str = match.group()
            # Skip if this version is part of a version pin (>=, ^, etc.)
            start = match.start()
            prefix = cleaned[:start].rstrip()
            if prefix and re.search(r"(?:>=|<=|~=|!=|==|\^|[<>])\s*$", prefix):
                continue
            results.append(
                Mention(
                    fact_name="version",
                    value=version_str,
                    file=file_path,
                    line=line_num,
                    context=line.strip(),
                )
            )
        return results

    def _extract_number_mentions(
        self, line: str, file_path: Path, line_num: int
    ) -> list[Mention]:
        """Extract numeric mentions matched via keyword proximity."""
        results: list[Mention] = []
        cleaned = self._mask_false_positives(line)

        # Strip markdown bold/italic markers for word extraction
        text_for_words = re.sub(r"\*{1,3}|_{1,3}", "", cleaned)

        for match in _NUMBER_RE.finditer(text_for_words):
            number_str = match.group()
            number_val = int(number_str)

            # Skip 0 and 1 — too common and ambiguous
            if number_val <= 1:
                continue

            # Check if this number is part of a version string in original
            # (already handled by _extract_versions)
            if _VERSION_RE.search(cleaned):
                # Check if this specific number position overlaps a version
                pos = match.start()
                is_in_version = False
                for vmatch in _VERSION_RE.finditer(text_for_words):
                    if vmatch.start() <= pos < vmatch.end():
                        is_in_version = True
                        break
                if is_in_version:
                    continue

            # Find position of the number in the raw text to locate nearby words
            word_positions = list(re.finditer(r"[a-zA-Z]+|\d+", text_for_words))

            # Find index of this number in word_positions
            num_idx = -1
            for i, wp in enumerate(word_positions):
                if wp.start() == match.start() and wp.group() == number_str:
                    num_idx = i
                    break

            if num_idx == -1:
                continue

            # Collect words within PROXIMITY_WINDOW positions
            window_start = max(0, num_idx - self.PROXIMITY_WINDOW)
            window_end = min(len(word_positions), num_idx + self.PROXIMITY_WINDOW + 1)
            window_tokens = [
                wp.group().lower()
                for wp in word_positions[window_start:window_end]
                if re.match(r"[a-zA-Z]", wp.group())
            ]

            # Check each fact type for keyword matches
            for fact_name, keywords in self.FACT_KEYWORDS.items():
                if fact_name == "version":
                    continue  # handled separately

                # Skip small numbers (<10) for count-type facts — too
                # many false positives from examples in SPEC docs.
                if number_val < 10 and fact_name.endswith("_count"):
                    continue

                for keyword in keywords:
                    kw_words = keyword.lower().split()
                    if self._keyword_in_window(kw_words, window_tokens):
                        results.append(
                            Mention(
                                fact_name=fact_name,
                                value=number_val,
                                file=file_path,
                                line=line_num,
                                context=line.strip(),
                            )
                        )
                        break
                else:
                    continue
                break  # one fact match per number

        return results

    @staticmethod
    def _word_matches_keyword(word: str, kw: str) -> bool:
        """Check if a window word matches a keyword (prefix match).

        "languages" matches keyword "language", "tools" matches "tool", etc.
        """
        return word == kw or word.startswith(kw)

    @staticmethod
    def _keyword_in_window(kw_words: list[str], window: list[str]) -> bool:
        """Check if keyword words appear in the window.

        Single-word keywords use prefix matching (e.g. "language" matches
        "languages").  Multi-word keywords require consecutive prefix matches.
        """
        if len(kw_words) == 1:
            kw = kw_words[0]
            return any(
                w == kw or w.startswith(kw) for w in window
            )

        # Multi-word keyword: check if words appear consecutively (prefix match)
        kw_len = len(kw_words)
        for i in range(len(window) - kw_len + 1):
            if all(
                window[i + j] == kw_words[j] or window[i + j].startswith(kw_words[j])
                for j in range(kw_len)
            ):
                return True
        return False

    @staticmethod
    def _mask_false_positives(line: str) -> str:
        """Replace false-positive patterns with spaces to prevent matching."""
        result = line

        # Mask ISO dates: 2026-02-19
        result = _DATE_ISO_RE.sub(lambda m: " " * len(m.group()), result)

        # Mask month-year dates: Feb 2026
        result = _DATE_MONTH_RE.sub(lambda m: " " * len(m.group()), result)

        # Mask issue IDs: #123
        result = _ISSUE_HASH_RE.sub(lambda m: " " * len(m.group()), result)

        # Mask project issue IDs: BDL-021
        result = _ISSUE_PREFIX_RE.sub(lambda m: " " * len(m.group()), result)

        # Mask hex colors: #FF0000
        result = _HEX_COLOR_RE.sub(lambda m: " " * len(m.group()), result)

        # Mask hex literals: 0xFF
        result = _HEX_LITERAL_RE.sub(lambda m: " " * len(m.group()), result)

        # Mask version pinning: >=0.80, ^1.2.3
        result = _VERSION_PIN_RE.sub(lambda m: " " * len(m.group()), result)

        # Mask line number references: :15, line 42, L42
        result = _LINE_REF_COLON_RE.sub(lambda m: " " * len(m.group()), result)
        result = _LINE_REF_WORD_RE.sub(lambda m: " " * len(m.group()), result)
        result = _LINE_REF_L_RE.sub(lambda m: " " * len(m.group()), result)

        # Mask standalone years: 2026, 2025, etc.
        result = _YEAR_STANDALONE_RE.sub(lambda m: " " * len(m.group()), result)

        return result

    def resolve_paths(
        self,
        project_root: Path,
        scan_globs: list[str] | None = None,
        *,
        config_path: Path | None = None,
    ) -> list[Path]:
        """Resolve glob patterns to actual file paths.

        Parameters
        ----------
        project_root:
            Root directory of the project.
        scan_globs:
            Optional list of glob patterns. Defaults to
            ``["*.md", "docs/**/*.md", ".beadloom/*.md"]``.
        config_path:
            Optional path to a config YAML file.  When ``None``, tries
            ``<project_root>/.beadloom/config.yml``.  The config may
            contain ``docs_audit.exclude_paths`` — a list of glob
            patterns to exclude.

        Returns
        -------
        list[Path]
            Deduplicated, sorted list of resolved markdown file paths.
        """
        default_globs = ["*.md", "docs/**/*.md", ".beadloom/*.md"]
        globs = scan_globs or default_globs

        # Build set of excluded resolved paths from default + config patterns
        excluded: set[Path] = set()
        for pattern in _EXCLUDE_PATTERNS:
            for p in project_root.glob(pattern):
                excluded.add(p.resolve())

        # Load additional exclude patterns from config
        extra_excludes = self._load_exclude_paths(project_root, config_path)
        for pattern in extra_excludes:
            for p in project_root.glob(pattern):
                excluded.add(p.resolve())

        seen: set[Path] = set()
        result: list[Path] = []

        for pattern in globs:
            for path in sorted(project_root.glob(pattern)):
                if not path.is_file():
                    continue

                # Exclude directories
                if any(part in _EXCLUDE_DIRS for part in path.parts):
                    continue

                # Exclude CHANGELOG.md by default
                if path.name == "CHANGELOG.md":
                    continue

                resolved = path.resolve()

                # Exclude default + config patterns
                if resolved in excluded:
                    continue

                if resolved not in seen:
                    seen.add(resolved)
                    result.append(path)

        return result

    @staticmethod
    def _load_exclude_paths(
        project_root: Path,
        config_path: Path | None,
    ) -> list[str]:
        """Load ``docs_audit.exclude_paths`` from config YAML.

        Returns an empty list when config is missing or has no relevant
        section.
        """
        import logging

        logger = logging.getLogger(__name__)

        cfg = config_path or (project_root / ".beadloom" / "config.yml")
        if not cfg.is_file():
            return []

        try:
            import yaml

            content = cfg.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
        except Exception:
            logger.warning("Failed to read %s for exclude paths", cfg)
            return []

        if not isinstance(data, dict):
            return []

        audit_section = data.get("docs_audit")
        if not isinstance(audit_section, dict):
            return []

        raw = audit_section.get("exclude_paths")
        if not isinstance(raw, list):
            return []

        return [str(p) for p in raw if isinstance(p, str)]
