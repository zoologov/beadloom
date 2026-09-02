# beadloom:domain=application
# beadloom:component=planning-report
"""One composition of every check that reads a planning document.

Before BDL-068 S1.4 the Gate step and the ``docs quality`` command each
assembled the run themselves — find the documents, derive the placeholder
vocabulary, call the checks. Two assemblies of one report is two things that can
disagree about what was checked, and this epic exists to remove that class. So
the assembly lives here, once, and both surfaces render what it returns.

Three families of check read the same corpus and answer different questions:

* the five WRITING-standard checks (:mod:`beadloom.doc_sync.doc_quality`) — a
  goal with no witness, a decision with no reason, a risk with no mitigation, a
  pending question in an approved document, an unfilled placeholder;
* the two STRUCTURAL checks (:mod:`beadloom.doc_sync.doc_shape`) — a document
  missing a section its template carries and its peers keep, and a required
  section whose heading is there with nothing under it;
* the two AXES checks (:mod:`beadloom.doc_sync.axes_section`) — axes stated
  without the seed they were derived from, and an axis with no scope decision.

The requirements the structural checks are held to are DERIVED from the composed
templates, so a project that adds a section to its own template layer makes it
required by the same act and tells nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.doc_sync import axes_section
from beadloom.doc_sync.doc_quality import CHECK_NAMES as WRITING_CHECK_NAMES
from beadloom.doc_sync.doc_quality import QualityReport, check_documents
from beadloom.doc_sync.doc_shape import (
    EMPTY_SECTION,
    MISSING_SECTION,
    PlanningShapeReport,
    check_planning_sections,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.doc_sync.doc_quality import QualityFinding

#: Every check that reads a planning document, in report order. One list, so a
#: summary that counts findings per check cannot silently omit a family.
CHECK_NAMES: tuple[str, ...] = (
    *WRITING_CHECK_NAMES,
    MISSING_SECTION,
    EMPTY_SECTION,
    *axes_section.CHECK_NAMES,
)


@dataclass(frozen=True)
class PlanningReport:
    """What every check found, and what the run could not judge.

    The two halves are kept apart rather than merged into one count:
    ``quality`` carries the applicability the writing checks report (a check
    that read nothing has verified nothing), and ``structure`` carries the
    conventions and the kinds no template describes. A single number over both
    would say "clean" about populations neither entered.
    """

    quality: QualityReport
    structure: PlanningShapeReport
    axes: tuple[QualityFinding, ...] = ()
    #: Documents carrying an ``## Axes`` section with at least one row — the
    #: population the axes checks ENTERED, which is not the corpus size.
    axes_read: int = 0

    @property
    def findings(self) -> tuple[QualityFinding, ...]:
        """Every finding, ordered by the file a reader would open."""
        return tuple(
            sorted(
                (*self.quality.findings, *self.structure.findings, *self.axes),
                key=lambda finding: (finding.path, finding.line, finding.check),
            )
        )

    @property
    def documents(self) -> int:
        """How many documents the writing checks read."""
        return self.quality.documents

    @property
    def applicable(self) -> dict[str, int]:
        """The population each check entered, per check.

        Stated for all nine rather than for the five that already had it,
        because a check reported as ``0 finding(s)`` over a population of zero
        has verified nothing and must not read as a pass.
        """
        counts = dict(self.quality.applicable)
        counts[MISSING_SECTION] = self.structure.documents
        counts[EMPTY_SECTION] = self.structure.documents
        for name in axes_section.CHECK_NAMES:
            counts[name] = self.axes_read
        return counts

    @property
    def checks_that_read_nothing(self) -> tuple[str, ...]:
        """Checks that found no document with anything to judge."""
        applicable = self.applicable
        return tuple(name for name in CHECK_NAMES if not applicable.get(name, 0))


def planning_report(paths: list[Path], *, project_root: Path) -> PlanningReport:
    """Run every planning-document check over *paths*.

    The texts are read here for the structural checks and again inside
    :func:`check_documents`, which owns the decode-failure reporting: a document
    nobody could read is UNVERIFIED and says so there, and duplicating that
    judgement to save one read would be a second answer to one question.
    """
    from beadloom.application.doc_shape import (
        document_section_requirements,
        shipped_placeholders,
    )

    quality = check_documents(
        paths,
        project_root=project_root,
        placeholders=shipped_placeholders(project_root),
    )
    documents: list[tuple[str, str]] = []
    for path in sorted(paths):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Already reported by `check_documents` as unreadable, with the
            # reason. Reporting it twice under two names would double one fault.
            continue
        try:
            relative = str(path.relative_to(project_root))
        except ValueError:
            relative = str(path)
        documents.append((relative, text))

    structure = check_planning_sections(
        documents, document_section_requirements(project_root)
    )
    axes: list[QualityFinding] = []
    axes_read = 0
    for relative, text in documents:
        section = axes_section.read_axes_section(text)
        if section is not None and section.axes:
            axes_read += 1
        axes.extend(axes_section.check_axes_section(relative, text))
    return PlanningReport(
        quality=quality,
        structure=structure,
        axes=tuple(axes),
        axes_read=axes_read,
    )
