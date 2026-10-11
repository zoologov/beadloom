"""A document of this repository may name Steiger's version (BDL-082 S2b, from S1W).

The FSD overlays and guides name the rule set of ``@feature-sliced/steiger-plugin``
0.8.0, measured on the scaffold's lock, and the scaffold pins ``steiger`` 0.7.0. Neither
package is a dependency this repository's ``pyproject.toml`` declares, so the version
vocabulary cannot derive them, and ``docs audit`` would compare both numbers against
Beadloom's own version. They are named once in ``docs_audit.subjects``; these cases hold
the declaration and the attribution it buys.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.doc_sync.scanner import DocScanner
from beadloom.doc_sync.version_subjects import derive_version_subjects
from tests.support.repository_root import REPO_ROOT

_STEIGER = ("steiger", "@feature-sliced/steiger-plugin")


@pytest.mark.parametrize("name", _STEIGER)
def test_the_package_is_a_declared_subject(name: str) -> None:
    subjects = derive_version_subjects(REPO_ROOT)

    assert (name, "docs_audit.subjects") in subjects.origins


@pytest.mark.parametrize(
    ("line", "subject"),
    [
        ("The scaffold pins steiger 0.7.0 beside the portal.", "steiger"),
        (
            "Its rules, read from `@feature-sliced/steiger-plugin` 0.8.0, are 17.",
            "@feature-sliced/steiger-plugin",
        ),
        (
            "The rule set of @feature-sliced/steiger-plugin 0.8.0 turns 17 on.",
            "@feature-sliced/steiger-plugin",
        ),
    ],
)
def test_a_version_beside_the_package_is_the_packages(line: str, subject: str) -> None:
    scanner = DocScanner(derive_version_subjects(REPO_ROOT))

    found = [
        m.subject
        for m in scanner.scan_line(line, origin=Path("doc.md"))
        if m.fact_name == "version"
    ]

    assert found == [subject]
