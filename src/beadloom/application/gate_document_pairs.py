# beadloom:domain=application
# beadloom:feature=ci-gate
"""The ``readme-pair`` leg: the declared document pairs, compared by SHAPE.

The comparison is :mod:`beadloom.doc_sync.document_pairs`'; this module is the
leg that runs it on every ``beadloom ci`` — its step, its line, and the
projection of what it found onto the shared finding shape.

**It is a module rather than four functions in the orchestrator, and the reason
is measured.** ``gate.py`` went 1362 → 1553 → 1624 → 1733 lines while a deferral
to lift per-leg rendering out of it stood, so the debt that deferral called
bounded grew every time the file was touched (``beadloom-qae9``, re-review).
This leg is the first one lifted (``beadloom-oew7``); the orchestrator composes
it and renders none of it.

**The line states the population it ran over, and the count is the findings the
STEP reports.** That is the correction this module ships with its own move: the
count was taken from the comparison, which folds over the pairs held, so a
refused declaration and a document nothing could read were findings the step
returned and the line did not count. The leg printed ``0 finding(s)`` in the
same run in which the Gate printed a finding about the leg — a check misstating
its own population, in the epic about checks stating their populations. One list
is built, the step carries it and the line counts it, so the two cannot disagree
without the same expression disagreeing with itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.gate_declarations import (
    refusal_finding,
    undetermined_declaration_step,
    unusable_phrase,
)
from beadloom.application.gate_step import Finding, GateStep

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from beadloom.doc_sync.document_pairs import (
        DocumentPair,
        PairComparison,
        PairReport,
    )
    from beadloom.doc_sync.document_pairs import (
        Finding as PairFinding,
    )

#: How many pairs the ``readme-pair`` line names before it stops listing. The
#: counts in front of the list are over ALL pairs, so the line never trades a
#: number for a name.
NAMED_PAIRS = 3


def step_readme_pair(project_root: Path) -> GateStep:
    """``readme-pair`` — the declared document pairs, compared by SHAPE; BLOCKS.

    **It cannot redden a project that has not opted in**, which is the epic's
    binding constraint. The pair is DECLARED under ``document_pairs:`` in
    ``.beadloom/config.yml`` — an adopter's translated README is their business
    and a check that guessed ``README.<lang>.md`` would turn somebody's green
    tree red on the upgrade that ships it. A project declaring none gets a named
    skip that states the key to add, exactly as ``issue-log`` does.

    **Declaring none and declaring badly are two verdicts, not one.** Four ways
    of mistyping the block reached the skip above word for word, and the two
    READMEs of a project that had opted in were never compared
    (``beadloom-rqma.7``). A refused entry is a finding now, and the line says
    how many entries were declared and how many were unusable: what tells the
    two apart has to be a count, because a skip reworded to "possibly nothing
    was declared" is the same defect in softer words.

    Where it BLOCKS it blocks for the ``issue-log`` reason rather than the
    ``docs-quality`` one: a block one document has and the other does not is not
    an opinion about prose, it is a statement one language makes and the other
    does not, and the repair fits in the commit that trips it. A declared file
    nothing could read fails for the same reason its ``issue-log`` twin does —
    a declaration pointing at nothing would otherwise report ``0 finding(s)``
    having compared no document at all.

    ``not_verified`` carries the honest half. Two readable files that hold no
    block between them produce no finding and compare nothing, and a clean
    result there describes the checker's own silence rather than the pair.
    """
    from beadloom.doc_sync.document_pairs import check_document_pairs

    report = check_document_pairs(project_root)
    if report.undetermined:
        return undetermined_declaration_step(
            "readme-pair", "a document pair", report.refusals
        )
    if not report.declared:
        return GateStep(
            "readme-pair",
            skipped=True,
            summary=(
                "skipped — no document pair is declared; add a `document_pairs:` block "
                "of `source:`/`follower:` entries to .beadloom/config.yml"
            ),
        )
    findings = _readme_pair_findings(project_root, report)
    return GateStep(
        "readme-pair",
        passed=not findings,
        not_verified=bool(_pairs_holding_nothing(report)),
        findings=findings,
        summary=_document_pair_summary(project_root, report, findings),
    )


def _readme_pair_findings(project_root: Path, report: PairReport) -> list[Finding]:
    """Everything this leg has to say about the run, in one list.

    Three populations, and the count in the line is the length of this list
    rather than of any one of them. The refusals and the unreadable documents
    used to be excluded from the count while being included in the step, which
    is how the leg reported ``0 finding(s)`` about a run the Gate reported a
    finding for (``beadloom-qae9``, re-review MAJOR 3).
    """
    findings = [refusal_finding("readme-pair", refusal) for refusal in report.refusals]
    findings += [_unreadable_document_finding(path) for path in report.unreadable]
    findings += [
        _document_pair_finding(project_root, comparison, finding)
        for comparison in report.comparisons
        for finding in comparison.findings
    ]
    return findings


def _pairs_holding_nothing(report: PairReport) -> tuple[PairComparison, ...]:
    """Pairs both of whose files were read and which hold no block at all.

    Separate from ``unreadable``: a file that could not be opened is a defect in
    the declaration, while two readable empty documents are a pair the check
    genuinely had nothing to say about. Reporting the second as a pass is the
    vacuity this project names rather than rounds off.
    """
    return tuple(
        comparison
        for comparison in report.comparisons
        if not comparison.unreadable and comparison.compared == 0
    )


def _document_pair_summary(
    project_root: Path, report: PairReport, findings: Sequence[Finding]
) -> str:
    """The readme-pair line, which states what it HELD and not only what it found.

    The three numbers lead because the finding count alone cannot distinguish a
    pair that agreed from a declaration that left nothing to compare — the shape
    every other line in this module was rewritten against.

    *findings* is the step's own list, passed in rather than recomputed. A line
    that derives its count a second way is a line that can contradict the
    findings it accompanies, and this one did.
    """
    line = (
        f"{len(report.comparisons)} pair(s) held, "
        f"{report.compared} block(s) compared, "
        f"{len(findings)} finding(s)"
    )
    named = [
        f"{_pair_label(project_root, comparison.pair)} "
        f"({comparison.compared} block(s))"
        for comparison in report.comparisons[:NAMED_PAIRS]
    ]
    if named:
        line += "; " + ", ".join(named)
    remaining = len(report.comparisons) - NAMED_PAIRS
    if remaining > 0:
        line += f", and {remaining} more pair(s) not named here"
    if report.unreadable:
        line += "; UNREADABLE: " + ", ".join(report.unreadable)
    nothing_held = _pairs_holding_nothing(report)
    if nothing_held:
        line += (
            f"; NOT COMPARED: {len(nothing_held)} pair(s) were read and hold no "
            "block at all, so nothing was held against anything"
        )
    return line + unusable_phrase(report.entries_declared, report.refusals)


def _pair_label(project_root: Path, pair: DocumentPair) -> str:
    """``source <-> follower``, both relative to the project."""
    source = _project_relative(project_root, pair.source)
    follower = _project_relative(project_root, pair.follower)
    return f"{source} <-> {follower}"


def _project_relative(project_root: Path, path: Path) -> str:
    """*path* as a project-relative string, or unchanged when it lies outside."""
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _unreadable_document_finding(path: str) -> Finding:
    """A declared document that could not be read, named against itself."""
    return {
        "kind": "readme-pair",
        "rule": "readme-pair",
        "severity": "error",
        "locations": [{"file": path}],
        "why": (
            f"{path} is declared in a `document_pairs:` entry and could not be read, "
            "so its pair was compared against nothing"
        ),
        "remediation": (
            "point the `document_pairs:` entry at the document, or remove the "
            "declaration if the pair no longer exists"
        ),
    }


#: What to do about each check the comparison runs. Keyed by the check name it
#: reports, so a check added there without a remediation here is a KeyError in
#: this project's own suite rather than a finding an agent cannot act on.
_PAIR_REMEDIATIONS = {
    "unpaired-block": (
        "add the missing block to the other document, or remove it from this one — "
        "the two are held to the same shape, never to the same words"
    ),
    "block-kind": (
        "give the two facing blocks the same kind, or the two headings the same level"
    ),
    "row-count": "give the list or table the same number of rows in both documents",
}


def _document_pair_finding(
    project_root: Path, comparison: PairComparison, finding: PairFinding
) -> Finding:
    """Project one shape divergence onto the shared finding shape.

    Both documents are located where both have a line, because the check says
    where the two sequences diverge rather than which side is wrong: an unpaired
    block is missing from one document or spurious in the other, and the
    comparison cannot tell those apart. The heading travels in ``why`` for the
    same reason — several paragraphs of one shape are indistinguishable, which
    is exactly why the comparison works across two languages.
    """
    locations: list[dict[str, object]] = []
    if finding.source_line is not None:
        locations.append(
            {
                "file": _project_relative(project_root, comparison.pair.source),
                "line": finding.source_line,
            }
        )
    if finding.follower_line is not None:
        locations.append(
            {
                "file": _project_relative(project_root, comparison.pair.follower),
                "line": finding.follower_line,
            }
        )
    where = f"under {finding.section!r}" if finding.section else "above the first heading"
    return {
        "kind": "readme-pair",
        "rule": finding.check,
        "severity": "error",
        "locations": locations,
        "why": f"{finding.detail} ({where})",
        "remediation": _PAIR_REMEDIATIONS[finding.check],
    }

