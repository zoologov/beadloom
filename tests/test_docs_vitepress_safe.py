"""Guard: doc Markdown must not contain Vue-interpolation hazards.

VitePress compiles Markdown through Vue, which treats ``{{ ... }}`` as a
JavaScript interpolation expression — even inside *inline* code in a table cell
(see BDL-049: ``ai-techwriter-${{ PR number }}`` broke the published-site build
with "Error parsing JavaScript expression"). Only *fenced* code blocks (```` ``` ````)
are escaped. This guard fails fast in the PR test gate so a stray ``{{`` never
reaches ``main`` and breaks the deploy-site pipeline again.

Allowed: ``{{ ... }}`` inside a fenced code block (e.g. a GitHub Actions
``${{ ... }}`` example). Disallowed: ``{{`` anywhere else.
"""

from __future__ import annotations

from pathlib import Path

DOCS_ROOT = Path(__file__).resolve().parent.parent / "docs"


def _strip_fenced_code(text: str) -> str:
    """Remove ```-fenced code blocks (their contents are VitePress-safe)."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def test_docs_have_no_unfenced_vue_interpolation() -> None:
    """No ``{{`` outside fenced code in any shipped doc (VitePress build hazard)."""
    offenders: list[str] = []
    for md in sorted(DOCS_ROOT.rglob("*.md")):
        body = _strip_fenced_code(md.read_text(encoding="utf-8"))
        for line in body.splitlines():
            if "{{" in line:
                rel = md.relative_to(DOCS_ROOT.parent)
                offenders.append(f"{rel}: {line.strip()}")
    assert not offenders, (
        "Vue-interpolation hazard (`{{`) outside a fenced code block — "
        "VitePress will fail to build. Reword (e.g. `<PR-number>`) or move into "
        "a ```-fenced block:\n  " + "\n  ".join(offenders)
    )
