"""What `impact` answers when its target is a file it cannot read as Python.

BDL-UX #255, and the way it was found is the point. `beadloom-0mdo.72` hit it
while deriving S6's axes -- by using the instrument for the job that slice exists
to do -- and the crash is why that derivation reaches 0 of its subject's 862
`beadloom <subcommand>` instruction sites across 68 non-Python artifacts. S5's
equivalent ratio was 14 of about 261.

The asymmetry is what makes it worth a module of its own. An ABSENT target has
always been reported in one sentence and exit 1; a target that EXISTS and is not
Python reached `ast.parse` and ended the command in a traceback. So the worse
failure belonged to the more plausible request -- a reader pointing the tool at
`CLAUDE.md`, an issue log or a role template -- and a typo got the sentence.

Both classes are checked here, because the suffix is the only thing separating
them and both reach the same call: a document, and a `.py` file saved half-way
through an edit. The second has been reachable since the package was written.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.impact import impact_of, render_impact

#: The kind the answer carries for a target it could not read. Spelled here as
#: the literal a consumer would match on, exactly as every other kind in this
#: suite is spelled: the vocabulary is a contract with the JSON, so a test that
#: imported the constant could not fail when the wire spelling changed.
UNREADABLE_TARGET = "unreadable-target"

if TYPE_CHECKING:
    from pathlib import Path

_MEASURE = '''\
"""A module whose axes live entirely inside it."""


def note(what):
    return what


def measure(a, b):
    if a:
        note("a")
        return 1
    note("neither")
    return 0
'''

#: A file saved half-way through an edit: the right suffix, and no tree.
_HALF_SAVED = '''\
"""A module saved half-way through an edit."""


def broken(
'''

#: The document a reader of this flow would most plausibly point the command at.
_DOCUMENT = "# CLAUDE.md\n\nRun `beadloom impact <path|symbol>` before a change.\n"


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A source tree, one document beside it and one half-saved module in it."""
    root = tmp_path / "proj"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "pkg" / "measure.py").write_text(_MEASURE, encoding="utf-8")
    (root / "src" / "pkg" / "half_saved.py").write_text(_HALF_SAVED, encoding="utf-8")
    (root / "CLAUDE.md").write_text(_DOCUMENT, encoding="utf-8")
    return root


def _gaps(answer: object, kind: str) -> list[str]:
    return [gap.where for gap in answer.unresolved if gap.kind == kind]  # type: ignore[attr-defined]


def test_a_document_is_a_verdict_rather_than_a_syntax_error(project: Path) -> None:
    """The reproduction from #255, one directory smaller."""
    answer = impact_of("CLAUDE.md", project_root=project)

    assert _gaps(answer, UNREADABLE_TARGET) == ["CLAUDE.md"]
    assert answer.co_writers.resolved is False
    assert answer.callers.resolved is False
    assert answer.commands == ()


def test_the_verdict_names_what_it_could_not_read_and_why(project: Path) -> None:
    """`unresolved` is only better than a traceback if it says the same things."""
    answer = impact_of("CLAUDE.md", project_root=project)

    gap = next(gap for gap in answer.unresolved if gap.kind == UNREADABLE_TARGET)
    assert "CLAUDE.md" in gap.detail
    assert ".md" in gap.detail
    assert "CLAUDE.md" in answer.callers.reason
    assert f"[{UNREADABLE_TARGET}]" in render_impact(answer)


def test_a_half_saved_module_is_the_same_verdict(project: Path) -> None:
    """The right suffix and no tree: one keystroke from the reported shape."""
    answer = impact_of("src/pkg/half_saved.py", project_root=project)

    gap = next(gap for gap in answer.unresolved if gap.kind == UNREADABLE_TARGET)
    assert gap.where == "src/pkg/half_saved.py"
    assert "SyntaxError" in gap.detail
    assert answer.callers.resolved is False


def test_the_readable_files_of_a_directory_target_still_answer(project: Path) -> None:
    """One unreadable file costs the answer that file and no other.

    Recall over precision, applied to the fix itself: refusing the whole answer
    because one file of a package did not parse would trade a traceback for a
    silence, which is the trade this epic exists to refuse.
    """
    answer = impact_of("src/pkg", project_root=project)

    assert _gaps(answer, UNREADABLE_TARGET) == ["src/pkg/half_saved.py"]
    branches = {command.name: len(command.branches) for command in answer.commands}
    assert branches["measure"] == 2


def test_an_absent_target_is_still_the_error_it_always_was(project: Path) -> None:
    """The clean failure that already existed is not widened into a verdict.

    A path nobody can resolve is a mistake in the invocation; a path this
    derivation cannot READ is a limit of the derivation. Answering the first one
    with an answer would hide a typo behind four unresolved axes.
    """
    from beadloom.application.impact import NoSuchTargetError

    with pytest.raises(NoSuchTargetError):
        impact_of("CLAUD.md", project_root=project)
