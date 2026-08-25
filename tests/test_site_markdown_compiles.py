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

from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


def _spans_that_spill_with_a_tag(path: Path) -> list[tuple[int, str]]:
    """Lines opening an inline-code span whose spilled half carries `<`."""
    lines = path.read_text(encoding="utf-8").splitlines()
    found: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if line.count("`") % 2 == 0 or "```" in line:
            continue
        following = lines[index + 1] if index + 1 < len(lines) else ""
        tail = line.rsplit("`", 1)[1]
        head = following.split("`", 1)[0] if "`" in following else following
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
            offenders.append(
                f"{path.relative_to(DOCS.parent)}:{line_number} — {excerpt}"
            )
    assert offenders == [], (
        "an inline-code span spills onto the next line carrying `<...>`; "
        "VitePress reads it as an HTML tag and `site-build` fails with a line "
        "number far from the cause. Keep the span on one line:\n  "
        + "\n  ".join(offenders)
    )
