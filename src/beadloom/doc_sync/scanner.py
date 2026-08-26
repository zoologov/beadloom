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
    from collections.abc import Callable, Iterator
    from pathlib import Path


@dataclass(frozen=True)
class Mention:
    """A numeric fact mention found in a markdown file."""

    fact_name: str
    value: str | int
    file: Path
    line: int
    context: str


@dataclass(frozen=True)
class ExcludedDoc:
    """A markdown file the scanner did not read, and the reason it did not."""

    path: Path
    reason: str


@dataclass(frozen=True)
class ScanSurface:
    """Which documents the audit actually read — the audit's own surface.

    A scan reports numbers found in the files it read; nothing in that report
    used to say which files it never opened.  On this repo that was 32 of 78
    markdown files (every ``docs/**/features/*/SPEC.md``), plus one whose counts
    are suppressed by the file-type heuristic — a third of the documentation,
    silently outside the audit (BDL-UX #173).

    - ``scanned``          — files read for mentions.
    - ``excluded``         — files never opened, each with its reason.
    - ``count_suppressed`` — files read for versions only, because their
      file type (``SPEC.md`` / ``CONTRIBUTING.md``) makes count matches
      unreliable.  They are a SUBSET of ``scanned``.
    """

    scanned: tuple[Path, ...] = ()
    excluded: tuple[ExcludedDoc, ...] = ()
    count_suppressed: tuple[Path, ...] = ()


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

# Backtick-enclosed inline code: `mcp-server`, `depth=2`
_BACKTICK_RE = re.compile(r"`[^`]+`")

# Numeric range pattern: 0-100, 1-10, etc.
_RANGE_RE = re.compile(r"\b\d+-\d+\b")

# ---------------------------------------------------------------------------
# Token boundary policy (BDL-UX #169)
# ---------------------------------------------------------------------------
#
# A number that is part of a LARGER TOKEN is an identifier, not a claim: the
# bead reference ``BDL-061.33``, the version ``v2.2.0``, the language version
# ``Python 3.10``, the reference ``PR #33``, the location ``cli.py:645`` and the
# ratio ``33/40`` all end in digits that mean nothing on their own.  Scanning for
# digits near a keyword read those tails as facts and failed the Gate twice.
#
# THE BOUNDARY IS WHITESPACE, and only whitespace.  Reason: whitespace is the one
# separator every prose convention agrees on, whereas ``.``  ``-`` ``/`` ``:``
# ``#`` and ``=`` are exactly the characters that hold those identifiers
# together — treating them as boundaries is the defect, not the fix.
#
# A token's CORE is the token with *wrapping* characters removed: markdown
# emphasis and bracket/quote punctuation at either end, plus sentence
# punctuation at the END only (``33.``, ``33,``, ``33:``).  Sentence punctuation
# is deliberately NOT stripped from the START, because a leading ``.`` ``#`` or
# ``-`` is what an identifier tail looks like once its prefix is masked
# (``BDL-061`` masked leaves ``.33``), and stripping it would restore the bug.
#
# A token is a fact candidate only when its whole core is a number.  This one
# rule subsumes the per-pattern skips it replaced (``0xFF``, ``>=0.80``,
# ``limit=10``, ``20+``, ``33%``, ``0-100``, ``L42``, ``file.py:15``) — those
# cores are not numbers, so they are never candidates.
_TOKEN_RE = re.compile(r"\S+")
# Typographic quotes are spelled as escapes so the source stays ASCII:
# \u00ab/\u00bb guillemets, \u201c/\u201d double quotes, \u2018/\u2019 single quotes.
_QUOTE_OPEN = "\u00ab\u201c\u2018"
_QUOTE_CLOSE = "\u00bb\u201d\u2019"
_TOKEN_LEAD_STRIP = "([{<\"'`*_~|" + _QUOTE_OPEN
_TOKEN_TRAIL_STRIP = ")]}>\"'`*_~|" + _QUOTE_CLOSE + ",;:.!?"

# A core that is entirely digits, or digits in thousands groups (``6,390``).
# Grouped numbers are read WHOLE: splitting ``1,067`` at the comma used to yield
# ``067``, which then compared equal to a project count of 67 and stamped a false
# claim "verified" — a silent false negative, the worst outcome available here.
_PLAIN_NUMBER_RE = re.compile(r"\d+")
_GROUPED_NUMBER_RE = re.compile(r"\d{1,3}(?:,\d{3})+")

# ---------------------------------------------------------------------------
# Clause scope: a number's claim reaches only to the end of its own clause
# ---------------------------------------------------------------------------
#
# A modifier suppresses a number when it MODIFIES it, and a keyword names a
# number when it is the noun that number COUNTS.  A flat +/-N word window cannot
# tell either, and both directions were measured wrong (BDL-UX #173):
#
#   "The graph holds 316 edges, one per import."   -> "per" killed a true count
#   "exposes 18 tools: 14 over the graph"          -> "tools" bound the 14 too,
#                                                     so a BREAKDOWN read as a
#                                                     restatement of the TOTAL
#
# Both windows therefore stop at a phrase separator.  Punctuation is a coarse
# proxy for syntax, but it is the one every prose convention agrees on, and it
# is the cheapest thing that distinguishes "what this number counts" from "what
# the rest of the sentence talks about".
#
# The SET was chosen by measurement, not by taste.  Parentheses are deliberately
# NOT separators: they cost the true verification in ``MCP tools (18):`` — an
# appositive restates its noun rather than leaving it — and a lost true
# verification is the very silent false negative this rule exists to remove.
# With ``,;:`` and the dashes: 0 mentions gained repo-wide, 5 lost, and every
# one of the five a confirmed false positive that had needed a
# ``docs_audit.ignore`` entry to stay quiet.
_CLAUSE_SEPARATORS = frozenset(",;:\u2014\u2013")

# ---------------------------------------------------------------------------
# Extraction floors — what the scanner deliberately cannot read
# ---------------------------------------------------------------------------
#
# These are the audit's own blind spots, and they are DECLARED rather than
# implicit: :func:`unreadable_reason` turns each one into a sentence the audit
# prints against the affected fact, so a fact nobody can check never reads as a
# fact that checked out (BDL-UX #173).
#
# The single-digit floor was re-measured before being kept (BDL-061.45).
# Removing it and binding a small number to an immediately following keyword
# yields 14 extra mentions on this repo, of which 13 are ordinals ("5. Domain
# list"), table cells ("| 5 | tests |") and category breakdowns ("(4 tools):"),
# several of which would have failed the Gate.  Trading a silent false negative
# for a loud false positive that then needs a suppression entry is the wrong
# trade; the floor stays, and its cost is now reported instead of hidden.
MIN_READABLE_NUMBER = 2
MIN_READABLE_COUNT = 10

#: Count facts whose NAME says what they count rather than ending in
#: ``_count``. The suffix decides for every other fact, and a rename that drops
#: it would silently take the fact out of the MIN_READABLE_COUNT floor —
#: which is what ``framework_count`` -> ``nodes_with_framework`` would have
#: done (BDL-UX #193).
_COUNT_FACTS_WITHOUT_SUFFIX: frozenset[str] = frozenset({"nodes_with_framework"})


def is_count_fact(fact_name: str) -> bool:
    """Whether *fact_name*'s value is a count of things.

    A count is subject to the MIN_READABLE_COUNT floor: single-digit counts are
    not extracted, because ordinals, table cells and category breakdowns swamp
    genuine claims below ten. A version is not a count and is never floored.
    """
    return fact_name.endswith("_count") or fact_name in _COUNT_FACTS_WITHOUT_SUFFIX


# ---------------------------------------------------------------------------
# Layer 1: Blocklist modifier words — numbers near these are NOT factual claims
# ---------------------------------------------------------------------------

# Single-word modifiers: if any appears within ±3 tokens of the number, skip.
_FP_MODIFIER_WORDS: frozenset[str] = frozenset({
    "default", "defaults",
    "max", "maximum", "min", "minimum",
    "limit", "limits", "limited",
    "cap", "capped", "caps",
    "target", "targets", "targeting",
    "threshold", "thresholds",
    "about", "approximately",
    "per",
    "depth",
    "days", "day", "hours", "hour", "minutes", "seconds",
})

# Multi-word modifier phrases (checked as consecutive tokens).
_FP_MODIFIER_PHRASES: tuple[list[str], ...] = (
    ["up", "to"],
    ["at", "least"],
    ["at", "most"],
    ["no", "more", "than"],
    ["capped", "at"],
)

# Regex-based modifier: % sign immediately after or near the number
_FP_PERCENT_RE = re.compile(r"\b\d+\s*%")

# ---------------------------------------------------------------------------
# Layer 3: File-type heuristics — paths with lower/higher FP risk
# ---------------------------------------------------------------------------

# Files matching these name patterns suppress count-type facts (not versions).
_LOW_CONFIDENCE_FILENAMES: frozenset[str] = frozenset({
    "SPEC.md",
    "CONTRIBUTING.md",
})

# Directories to always exclude from path resolution
_EXCLUDE_DIRS = frozenset({"node_modules", ".git", "__pycache__", ".venv", "venv"})

# Default glob patterns for files to scan.
DEFAULT_SCAN_GLOBS: tuple[str, ...] = ("*.md", "docs/**/*.md", ".beadloom/*.md")

# Glob patterns for files to exclude by default
_EXCLUDE_PATTERNS = (
    "_graph/features/*/SPEC.md",
    ".beadloom/_graph/features/*/SPEC.md",
    "docs/**/features/*/SPEC.md",
    "docs/**/features/**/SPEC.md",
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
        # Every keyword names NODES that declare a framework, never a
        # framework on its own. "12 web frameworks" is a sentence about
        # frameworks and is not a claim about how many nodes declare one
        # (BDL-UX #193). Matching is prefix-based per word, so "node" covers
        # "nodes" and "declar" covers "declare"/"declares"/"declaring".
        "nodes_with_framework": [
            "node with framework",
            "node with a framework",
            "node with a test framework",
            "node declar a framework",
            "node declar a test framework",
        ],
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

            mentions.extend(self.scan_line(line, origin=file_path, line_number=line_num))

        return mentions

    def scan_line(
        self, line: str, *, origin: Path, line_number: int = 1
    ) -> list[Mention]:
        """Every fact mention one line of prose states.

        The seam :meth:`scan_file` is written in terms of, and the entry point
        for prose that is not in a file at all — a node ``summary`` in the
        architecture graph is one line of exactly this kind, and the
        ``graph-summary-facts`` lint rule reads it here (BDL-062 ``.1``).

        It exists so there is ONE notion of "a version" and ONE keyword table in
        this codebase. A second extractor built beside this one would agree with
        it on the day it was written and diverge on the first token-boundary or
        clause-scope repair that landed on only one of the two, which is how the
        next drift class starts.

        *origin* is what the returned :class:`Mention` records as its source and
        the only thing the low-confidence filename check reads. A caller whose
        prose has no file passes the identifier the reader needs to find it.
        """
        return [
            # Version strings: matched by pattern, no proximity needed.
            *self._extract_versions(line, origin, line_number),
            # Counts: matched by keyword proximity within the number's clause.
            *self._extract_number_mentions(line, origin, line_number),
        ]

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

        # Layer 3: suppress count facts for low-confidence file types
        is_low_confidence_file = file_path.name in _LOW_CONFIDENCE_FILENAMES

        # Strip markdown bold/italic markers for word extraction
        text_for_words = re.sub(r"\*{1,3}|_{1,3}", "", cleaned)

        # Mask backtick-enclosed code references — keywords inside inline
        # code (e.g. `mcp-server`, `node_count`) are identifiers, not
        # natural-language claims about facts.
        text_for_words = _BACKTICK_RE.sub(
            lambda m: " " * len(m.group()), text_for_words,
        )

        for start, end, number_val in self._iter_number_tokens(text_for_words):
            # Skip 0 and 1 — too common and ambiguous
            if number_val < MIN_READABLE_NUMBER:
                continue

            # Skip a number written as a share, not a count: "50 %" (the
            # no-space form "50%" is not a number token at all).
            rest = text_for_words[start:]
            share_match = _PLAIN_NUMBER_RE.match(rest)
            if share_match is not None and re.match(
                r"\s*%", rest[share_match.end():share_match.end() + 3]
            ):
                continue

            # Find position of the number in the raw text to locate nearby words
            word_positions = list(re.finditer(r"[a-zA-Z]+|\d+", text_for_words))

            # Find index of this number in word_positions (matched on offset:
            # a grouped number such as "6,390" starts one word-position run)
            num_idx = -1
            for i, wp in enumerate(word_positions):
                if wp.start() == start:
                    num_idx = i
                    break

            if num_idx == -1:
                continue

            # Every window below is scoped to the number's own clause: a word
            # on the far side of a phrase separator neither modifies it nor
            # names what it counts (see _CLAUSE_SEPARATORS).
            in_clause = self._clause_scope(
                text_for_words, word_positions, num_idx, span=(start, end)
            )

            # Layer 1c: skip if modifier word is within ±3 tokens of number
            modifier_window_start = max(0, num_idx - 3)
            modifier_window_end = min(
                len(word_positions), num_idx + 3 + 1
            )
            modifier_tokens = [
                word_positions[i].group().lower()
                for i in range(modifier_window_start, modifier_window_end)
                if re.match(r"[a-zA-Z]", word_positions[i].group()) and in_clause(i)
            ]

            if self._has_modifier(modifier_tokens):
                continue

            # Layer 3: suppress count facts for low-confidence files
            if is_low_confidence_file:
                continue

            # Layer 2: find the closest matching fact type keyword
            # (disambiguates when multiple fact keywords appear nearby)
            # Score is (distance, is_before_number) — lower distance wins;
            # on ties, keywords AFTER the number (is_before=0) beat BEFORE (1).
            # The third component breaks a distance tie in favour of the LONGER
            # keyword phrase: "84 nodes declare a test framework" is one word
            # from both `node` and `node declar a test framework`, and the
            # phrase that accounts for more of the sentence is the one the
            # sentence is about. Without it the winner was whichever fact the
            # keyword table happened to list first (BDL-UX #193).
            best_fact: str | None = None
            best_score: tuple[int, int, int] = (self.PROXIMITY_WINDOW + 1, 1, 0)

            for fact_name, keywords in self.FACT_KEYWORDS.items():
                if fact_name == "version":
                    continue  # handled separately

                # Skip small numbers for count-type facts — measured to be
                # ordinals, table cells and category breakdowns far more often
                # than counts (see MIN_READABLE_COUNT).  The cost is reported
                # per fact by :func:`unreadable_reason`, never silent.
                if number_val < MIN_READABLE_COUNT and is_count_fact(fact_name):
                    continue

                for keyword in keywords:
                    kw_words = keyword.lower().split()
                    distance = self._keyword_distance(
                        kw_words, word_positions, num_idx, in_clause=in_clause,
                    )
                    if distance is None:
                        continue
                    score = (*distance, -len(kw_words))
                    if score < best_score:
                        best_score = score
                        best_fact = fact_name

            if best_fact is not None:
                results.append(
                    Mention(
                        fact_name=best_fact,
                        value=number_val,
                        file=file_path,
                        line=line_num,
                        context=line.strip(),
                    )
                )

        return results

    @staticmethod
    def _iter_number_tokens(text: str) -> Iterator[tuple[int, int, int]]:
        """Yield ``(start, end, value)`` for tokens that are entirely a number.

        Implements the token boundary policy documented at the top of this
        module: split on whitespace, strip wrapping punctuation, and accept a
        token only when its whole core is a number.  A number embedded in a
        larger token (``BDL-061.33``, ``v2.2.0``, ``Python 3.10``, ``PR #33``,
        ``33/40``) is an identifier and yields nothing.

        ``start`` is the position of the number's first digit in *text* and
        ``end`` the position just past its last, so callers can both locate it
        among the surrounding words and know how much of the line it OWNS — the
        separator inside ``6,390`` belongs to the number, not between it and the
        next word.
        """
        for token in _TOKEN_RE.finditer(text):
            raw = token.group()
            lstripped = raw.lstrip(_TOKEN_LEAD_STRIP)
            core = lstripped.rstrip(_TOKEN_TRAIL_STRIP)
            if not core:
                continue
            start = token.start() + (len(raw) - len(lstripped))
            end = start + len(core)
            if _PLAIN_NUMBER_RE.fullmatch(core):
                yield start, end, int(core)
            elif _GROUPED_NUMBER_RE.fullmatch(core):
                yield start, end, int(core.replace(",", ""))

    @staticmethod
    def _clause_scope(
        text: str,
        word_positions: list[re.Match[str]],
        num_idx: int,
        *,
        span: tuple[int, int],
    ) -> Callable[[int], bool]:
        """Return a predicate: is word *i* in the same clause as the number?

        Two words share a clause when no phrase separator stands between them.
        The predicate is built once per number so both the modifier window and
        the keyword window are scoped identically — scoping one and not the
        other would let a noun bind across a boundary the qualifier could not
        cross, which is a false positive wearing the fix's clothes.
        """
        anchor_start, anchor_end = span

        def in_clause(i: int) -> bool:
            other = word_positions[i]
            if other.start() >= anchor_start and other.end() <= anchor_end:
                return True  # a digit group of the number itself
            between = (
                text[other.end():anchor_start]
                if other.end() <= anchor_start
                else text[anchor_end:other.start()]
            )
            return not any(ch in _CLAUSE_SEPARATORS for ch in between)

        return in_clause

    @staticmethod
    def _has_modifier(tokens: list[str]) -> bool:
        """Check if any modifier word or phrase appears in the token window.

        Layer 1 of false-positive reduction: numbers near modifiers like
        'default', 'max', 'limit', 'per', 'about', etc. are configuration
        parameters or thresholds, not factual claims.
        """
        # Single-word modifiers
        if any(tok in _FP_MODIFIER_WORDS for tok in tokens):
            return True

        # Multi-word modifier phrases
        for phrase in _FP_MODIFIER_PHRASES:
            phrase_len = len(phrase)
            for i in range(len(tokens) - phrase_len + 1):
                if all(tokens[i + j] == phrase[j] for j in range(phrase_len)):
                    return True

        return False

    @classmethod
    def _keyword_distance(
        cls,
        kw_words: list[str],
        word_positions: list[re.Match[str]],
        num_idx: int,
        *,
        in_clause: Callable[[int], bool],
    ) -> tuple[int, int] | None:
        """Return (distance, before_flag) from a number to a keyword match.

        Layer 2 of false-positive reduction: when multiple fact keywords
        appear near a number, the closest one wins.  On ties, keywords
        appearing *after* the number are preferred (``before_flag=0``)
        over those before it (``before_flag=1``), because natural English
        typically writes "63 edges" (number then noun).

        *in_clause* bounds the search to the number's own clause: a noun on the
        far side of a phrase separator is what the SENTENCE talks about, not
        what the NUMBER counts.

        Returns ``None`` if the keyword is not found within the proximity
        window.
        """
        window_size = cls.PROXIMITY_WINDOW
        start = max(0, num_idx - window_size)
        end = min(len(word_positions), num_idx + window_size + 1)

        best: tuple[int, int] | None = None

        if len(kw_words) == 1:
            kw = kw_words[0]
            for i in range(start, end):
                if not in_clause(i):
                    continue
                w = word_positions[i].group().lower()
                if re.match(r"[a-zA-Z]", w) and (w == kw or w.startswith(kw)):
                    dist = abs(i - num_idx)
                    before_flag = 1 if i < num_idx else 0
                    score = (dist, before_flag)
                    if best is None or score < best:
                        best = score
            return best

        # Multi-word keyword: find consecutive matches
        kw_len = len(kw_words)
        for i in range(start, min(end, len(word_positions) - kw_len + 1)):
            if not all(in_clause(i + j) for j in range(kw_len)):
                continue
            words_at = [word_positions[i + j].group().lower() for j in range(kw_len)]
            if all(
                re.match(r"[a-zA-Z]", words_at[j])
                and (words_at[j] == kw_words[j] or words_at[j].startswith(kw_words[j]))
                for j in range(kw_len)
            ):
                dist = abs(i - num_idx)
                before_flag = 1 if i < num_idx else 0
                score = (dist, before_flag)
                if best is None or score < best:
                    best = score
        return best

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

        # Mask numeric ranges: 0-100, 1-10 (Layer 2 — not factual counts)
        result = _RANGE_RE.sub(lambda m: " " * len(m.group()), result)

        return result

    def resolve_paths(
        self,
        project_root: Path,
        scan_globs: list[str] | None = None,
        *,
        config_path: Path | None = None,
    ) -> list[Path]:
        """Resolve glob patterns to the markdown files that will be scanned.

        Thin projection of :meth:`resolve_surface` — the files it did NOT
        resolve are on the surface record, which is what the audit reports.
        """
        return list(
            self.resolve_surface(
                project_root, scan_globs, config_path=config_path
            ).scanned
        )

    def resolve_surface(
        self,
        project_root: Path,
        scan_globs: list[str] | None = None,
        *,
        config_path: Path | None = None,
    ) -> ScanSurface:
        """Resolve glob patterns into the scan surface: read, skipped, and why.

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
        ScanSurface
            Deduplicated, sorted files to scan, plus every candidate file left
            out and the reason it was left out.
        """
        globs = scan_globs or list(DEFAULT_SCAN_GLOBS)

        reasons = self._exclusion_reasons(project_root, config_path)

        seen: set[Path] = set()
        scanned: list[Path] = []
        excluded: list[ExcludedDoc] = []

        for pattern in globs:
            for path in sorted(project_root.glob(pattern)):
                if not path.is_file():
                    continue

                # Whole directories that never hold project documentation.
                if any(part in _EXCLUDE_DIRS for part in path.parts):
                    continue

                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)

                if path.name == "CHANGELOG.md":
                    excluded.append(
                        ExcludedDoc(path, "CHANGELOG.md is excluded by default")
                    )
                    continue

                reason = reasons.get(resolved)
                if reason is not None:
                    excluded.append(ExcludedDoc(path, reason))
                    continue

                scanned.append(path)

        return ScanSurface(
            scanned=tuple(scanned),
            excluded=tuple(excluded),
            count_suppressed=tuple(
                p for p in scanned if p.name in _LOW_CONFIDENCE_FILENAMES
            ),
        )

    def _exclusion_reasons(
        self, project_root: Path, config_path: Path | None
    ) -> dict[Path, str]:
        """Map each excluded file to the pattern that excluded it."""
        reasons: dict[Path, str] = {}
        for pattern in _EXCLUDE_PATTERNS:
            for path in project_root.glob(pattern):
                reasons.setdefault(
                    path.resolve(), f"built-in exclude pattern {pattern}"
                )
        for pattern in self._load_exclude_paths(project_root, config_path):
            for path in project_root.glob(pattern):
                reasons.setdefault(
                    path.resolve(), f"docs_audit.exclude_paths pattern {pattern}"
                )
        return reasons

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


def unreadable_reason(fact_name: str, value: str | int) -> str | None:
    """Why no document could state *value* readably — or ``None`` if it could.

    The audit's declared fact list used to include facts the scanner is
    incapable of matching, and their zero findings read exactly like the zero
    findings of a fact nobody happened to mention (BDL-UX #173).  They are
    different situations: one is silence in the docs, the other is blindness in
    the checker, and only the second is a defect in this tool.  This function
    is the checker's own statement of the second.

    Returns a human sentence naming the limit, or ``None`` when a document
    stating this fact at this value would in fact be read.
    """
    if fact_name == "version":
        return None  # versions are matched by pattern, not by keyword or size

    if not DocScanner.FACT_KEYWORDS.get(fact_name):
        return (
            f"no scanner keywords are registered for {fact_name}, so no sentence "
            "in any document can be matched to it"
        )

    try:
        number = int(str(value))
    except (TypeError, ValueError):
        return None

    if number < MIN_READABLE_NUMBER:
        return (
            f"its value is {number}: 0 and 1 are too common in prose to be read "
            "as claims, so no statement of this fact can be verified"
        )

    if number < MIN_READABLE_COUNT and is_count_fact(fact_name):
        return (
            f"its value is {number}: single-digit counts are not extracted "
            "(measured: ordinals, table cells and category breakdowns swamp "
            "genuine claims below ten), so a correct statement of this fact "
            "cannot be verified"
        )

    return None
