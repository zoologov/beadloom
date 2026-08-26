"""The distribution's one-line description, and what can be checked about it.

BDL-062 `.4`. `pyproject.toml`'s `description` is what PyPI shows on the project
page. It said "Context Oracle + Doc Sync Engine for AI-assisted development"
through three major versions -- the 1.x description, naming two of the product's
parts and none of the four added since -- and nothing anywhere compared it to
anything, because there is nothing to compare a sentence to.

**Half of this is checkable and half is not, and the two are kept apart here.**
The same sentence is written twice, in the manifest and in the package
docstring; that they agree IS checkable, and they can drift apart silently
otherwise. Whether the sentence is CURRENTLY TRUE of the product is not
checkable by any test: both copies were in perfect agreement while both were
three majors out of date. That is a judgement a reader makes at release, and
`CONTRIBUTING.md`'s release process is where it is asked for.

That last claim was measured rather than assumed. Reverting BOTH copies to the
1.x sentence leaves this module green, which is the whole reason the description
went three majors without anybody noticing. A blocklist of retired phrases was
written here and then removed: `Doc Sync v2 Engine` lived in the graph's root
summary, never in the manifest, so the check could not have fired on what it
guarded. An inert check reads as coverage it does not have, which is the defect
this whole feature exists to remove.
"""

from __future__ import annotations

import re
from pathlib import Path

import beadloom

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The manifest's `description` line. Read by pattern rather than by a TOML
#: parser because `tomllib` is 3.11+ and this project supports 3.10; the one
#: line this module is about is a plain top-level string, and the pattern is
#: anchored to the start of a line so a `description` indented under some other
#: table is not what it finds. The count is asserted, so a second top-level
#: `description` is a failure rather than a silent first match.
_DESCRIPTION_RE = re.compile(r'^description\s*=\s*"([^"]*)"', re.MULTILINE)


def _manifest_description() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    matches = _DESCRIPTION_RE.findall(text)
    assert len(matches) == 1, f"expected one top-level description, found {len(matches)}"
    description: str = matches[0]
    return description


def _docstring_description() -> str:
    """The package docstring's sentence, with its `Beadloom - ` prefix removed."""
    doc = beadloom.__doc__ or ""
    collapsed = re.sub(r"\s+", " ", doc).strip().rstrip(".")
    return re.sub(r"^Beadloom - ", "", collapsed)


class TestTheDescriptionIsWrittenOnceInEffect:
    def test_the_manifest_and_the_package_docstring_say_the_same_thing(self) -> None:
        manifest = _manifest_description()
        docstring = _docstring_description()
        assert docstring.casefold() == manifest.casefold(), (
            "pyproject.toml `description` and beadloom.__doc__ have drifted apart:\n"
            f"  manifest:  {manifest}\n"
            f"  docstring: {docstring}"
        )
