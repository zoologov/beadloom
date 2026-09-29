"""An inline-code span that spills onto the next line carrying `<...>`.

VitePress compiles every markdown page as a Vue SFC, so a `<base>` or `<ref>`
that is NOT inside a closed inline-code span on ONE line reaches the Vue
compiler as an HTML tag: `Attribute name cannot contain U+0022 ("), U+0027 ('),
and U+003C (<)`. The error names the line where the tokenizer finally gives up,
which in the case that motivated this file was 29 lines below the actual cause —
a `` `git diff `` opening at the end of one line and closing after `<base>` on
the next.

Nothing else in this repository could see it: the markdown is valid, `sync-check`
compares pairs, `docs audit` reads facts, and the failure lives in a build step
that runs only in CI. This test is the mechanism, so the next one fails here
rather than in a red `site-build` job (BDL-061 S6).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

DOCS = REPO_ROOT / "docs"


#: A fenced block's opening or closing line; its contents are code, not prose.
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def _ends_the_paragraph(line: str) -> bool:
    """A line no inline-code span can run onto: blank, a fence, or a table row."""
    return not line.strip() or bool(_FENCE.match(line)) or line.lstrip().startswith("|")


def _spans_that_spill_with_a_tag(path: Path) -> list[tuple[int, str]]:
    """Lines whose inline-code span runs onto the next line with `<` in either half.

    Whether a span is open is STATE carried from line to line within a
    paragraph, not a line's own backtick parity: a line that closes one span and
    opens another has an even count and still spills (PR #86). A blank line, a
    fence or a table row ends the paragraph, and a fenced block is not read.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    found: list[tuple[int, str]] = []
    fence: str | None = None
    open_span = False
    for index, line in enumerate(lines):
        marker = _FENCE.match(line)
        if fence is not None or marker:
            if marker and fence in (None, marker.group(1)[0]):
                fence = None if fence else marker.group(1)[0]
            open_span = False
            continue
        if _ends_the_paragraph(line):
            open_span = False
            continue
        parts = line.split("`")
        open_span ^= (len(parts) - 1) % 2 == 1
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if not open_span or _ends_the_paragraph(following):
            continue
        tail = parts[-1]
        head = following.split("`", 1)[0]
        if "<" in tail or "<" in head:
            found.append((index + 1, f"{tail} / {head}"[:80]))
    return found


def test_no_inline_code_span_spills_a_tag_onto_the_next_line() -> None:
    """Every `<...>` sits inside a span that opens and closes on one line."""
    offenders: list[str] = []
    for path in sorted(DOCS.rglob("*.md")):
        for line_number, excerpt in _spans_that_spill_with_a_tag(path):
            if "Errno" in excerpt:  # a bracketed errno, not a tag
                continue
            offenders.append(f"{path.relative_to(DOCS.parent)}:{line_number} — {excerpt}")
    assert offenders == [], (
        "an inline-code span spills onto the next line carrying `<...>`; "
        "VitePress reads it as an HTML tag and `site-build` fails with a line "
        "number far from the cause. Keep the span on one line:\n  " + "\n  ".join(offenders)
    )


class TestTheSpillIsFollowedAcrossLinesAndNotByParity:
    """PR #86's `site-build` failed on a spill this file did not report.

    `docs/domains/context-oracle/features/test-mapping/SPEC.md` had a line that
    CLOSED a span opened on the line above and OPENED another, whose second half
    began the next line with `<absent roots>`. Two backticks is an even count, so
    a reader that decides by each line's parity skipped the line, and VitePress,
    whose component rule lets a line that starts with a tag interrupt a
    paragraph, cut the span in two: `Element is missing end tag`. The open span
    is state carried from line to line, so it is read that way.
    """

    def test_a_line_that_closes_one_span_and_opens_another_is_read(self, tmp_path: Path) -> None:
        page = tmp_path / "page.md"
        page.write_text(
            "With none recorded it says `and it lies beside a node's\n"
            "code, since none exists`, or `under a root, and none of the roots\n"
            "<absent roots> exists` when tests beside the code are not read.\n",
            encoding="utf-8",
        )
        assert [line for line, _ in _spans_that_spill_with_a_tag(page)] == [2]

    def test_a_span_does_not_cross_a_blank_line_or_a_fence(self, tmp_path: Path) -> None:
        """A backtick left open at a paragraph's end is a literal backtick, and a
        fenced block is code whatever its backticks are."""
        page = tmp_path / "page.md"
        page.write_text(
            "An unclosed ` backtick ends with its paragraph.\n"
            "\n"
            "<details> opens a block on purpose.\n"
            "\n"
            "```bash\n"
            "echo `date` and a stray ` backtick\n"
            "echo <file>\n"
            "```\n",
            encoding="utf-8",
        )
        assert _spans_that_spill_with_a_tag(page) == []
