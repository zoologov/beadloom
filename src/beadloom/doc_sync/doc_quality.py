# beadloom:domain=doc-sync
# beadloom:feature=doc-quality
"""Five checkable properties of a planning document (BDL-061 S4b).

CONTEXT's reason for these, kept in view because it is the whole argument:
*these planning documents read well because of conventions written down nowhere,
and a practice that is not a mechanism does not survive the session.* The
conventions are stated in every role's writing standard; until now nothing read
a document back to see whether they held.

The five, each ``warn``:

``measurable-goal``
    A goal with no number in it. "Make it better" is not a goal.
``decision-reason``
    A decision row whose reason cell is empty.
``risk-mitigation``
    A risk row with no mitigation, or one of the mitigations that are not
    mitigations — "monitor it" names no action anyone could take.
``pending-in-approved``
    An open question still answered ``Pending`` in a document whose status is
    ``Approved``. A plan approved with its design undecided is a plan that has
    not been made.
``unfilled-placeholder``
    A token the shipped template left for the author to replace, still present.
    The placeholder vocabulary is DERIVED from the shipped templates rather than
    listed here, so it cannot drift away from them.

**What each check can and cannot decide**, stated here rather than discovered by
a reader who trusted it: a number is necessary for a measurable clause and not
sufficient (``#142 and #146 close`` is checkable, ``we improved 3 things`` is
not, and nothing here can tell them apart); a reason is checked for EXISTENCE,
not for explaining rather than restating the decision, which no checker decides;
and a mitigation is judged against a named set of empty ones rather than on
whether it would work.

**Applicability is reported PER DOCUMENT KIND, not only per check.**
``checks_that_read_nothing`` is a global OR over the corpus, so it goes silent
the moment one document carries one row: it can see a check that is blind
everywhere and not one that is blind on an entire shipped document kind.
Measured on this repository, all eleven ``BRIEF.md`` contribute zero to all four
content checks by template construction, and that guard was green throughout —
the blind spot it was built to prevent, one level down (review BDL-061.15 M2).
:attr:`QualityReport.by_kind` states the population each kind entered, and
:attr:`QualityReport.kinds_that_read_nothing` names the ones no content check
enters at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

MEASURABLE_GOAL = "measurable-goal"
DECISION_REASON = "decision-reason"
RISK_MITIGATION = "risk-mitigation"
PENDING_IN_APPROVED = "pending-in-approved"
UNFILLED_PLACEHOLDER = "unfilled-placeholder"

#: Every check this module runs, in report order.
CHECK_NAMES: tuple[str, ...] = (
    MEASURABLE_GOAL,
    DECISION_REASON,
    RISK_MITIGATION,
    PENDING_IN_APPROVED,
    UNFILLED_PLACEHOLDER,
)

#: The four checks whose population is ITEMS a document states — a goal, a
#: decision row, a risk row, an open question. ``unfilled-placeholder`` is
#: deliberately not one: its population is documents OPENED, so it reads every
#: document by construction and can never tell one kind from another. Judging
#: "was this kind entered" over all five would report every kind as read, which
#: is a second vacuous guard in place of the first (review `.15` n1).
CONTENT_CHECKS: tuple[str, ...] = (
    MEASURABLE_GOAL,
    DECISION_REASON,
    RISK_MITIGATION,
    PENDING_IN_APPROVED,
)

#: A status whose first word means the document was agreed, not drafted. Only
#: these are held to "no ``Pending`` question": a Draft is *supposed* to have
#: open questions, and reporting them would train an author to ignore the check.
APPROVED_STATUSES: frozenset[str] = frozenset({"approved", "accepted"})

#: Section titles whose contents are read as goal statements.
_GOAL_SECTIONS = ("goal", "goals")

#: Mitigations that name no action. Matched as the WHOLE cell, so "monitor the
#: queue depth and page above 80%" is a mitigation and "monitor it" is not.
_EMPTY_MITIGATION_RE = re.compile(
    r"^(?:monitor|watch|observe|be\s+careful|careful|tbd|todo|n/?a|none|-|—|\?)"
    r"(?:\s+(?:it|them|this|closely|carefully))?[.!]?$",
    re.IGNORECASE,
)

#: A number that is not part of an identifier. ``BDL-061`` and ``v2.2`` do not
#: make a sentence measurable; ``440 -> 376 lines`` does.
_NUMBER_RE = re.compile(r"(?<![\w.\-])\d")

_HEADING_RE = re.compile(r"^(#{1,6}) +(.+?)\s*$")
_STATUS_RE = re.compile(r"^>\s*\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(?:\[[ xX]\]\s*)?(.*)$")
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_SEPARATOR_CELL_RE = re.compile(r"^:?-{2,}:?$")
_PENDING_RE = re.compile(r"^pending\b", re.IGNORECASE)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_TRAILING_PAREN_RE = re.compile(r"\s*\([^()]*\)\s*$")


@dataclass(frozen=True)
class QualityFinding:
    """One property a document does not hold.

    ``line`` is 1-based and points at the line the reader must open; ``excerpt``
    is the text that gave it away, so a report is actionable without the file.
    """

    check: str
    path: str
    line: int
    excerpt: str
    why: str
    remediation: str


@dataclass(frozen=True)
class KindCoverage:
    """What the checks read in one kind of document — ``PRD``, ``BRIEF``, ….

    ``documents`` counts the documents of this kind that were READ, and
    ``unreadable`` those that could not be decoded. They are separate because a
    file nobody read is not evidence about what its kind carries: counting an
    undecodable ``BRIEF.md`` as a BRIEF with nothing read would turn an encoding
    accident into a statement about the project's templates.
    """

    kind: str
    documents: int = 0
    applicable: dict[str, int] = field(default_factory=dict)
    unreadable: int = 0

    @property
    def checks_that_read_nothing(self) -> tuple[str, ...]:
        """Checks that found nothing to judge in any document of this kind."""
        return tuple(
            name for name in CHECK_NAMES if not self.applicable.get(name, 0)
        )

    @property
    def is_unread(self) -> bool:
        """Whether no CONTENT check enters this kind — a population never entered.

        Judged over :data:`CONTENT_CHECKS`, and only over documents that were
        actually read: a kind whose every document is undecodable is
        *unverified*, which is a different fact and has a different remedy.
        """
        return bool(self.documents) and not any(
            self.applicable.get(name, 0) for name in CONTENT_CHECKS
        )


@dataclass(frozen=True)
class QualityReport:
    """Findings over a set of documents, plus what the run could NOT judge.

    ``not_applicable`` names, per check, how many documents carried nothing for
    it to read — a green count over documents that state no risks is not a
    statement about risks, and this epic has shipped four counts that meant less
    than they said (BDL-UX #172, #173, #174, #175).
    """

    findings: tuple[QualityFinding, ...] = ()
    documents: int = 0
    applicable: dict[str, int] = field(default_factory=dict)
    by_kind: tuple[KindCoverage, ...] = ()
    """Applicability per document kind — the question the global count cannot ask.

    ``checks_that_read_nothing`` is an OR over the whole corpus and goes silent
    the moment ONE document carries ONE row, so it cannot see a check that is
    blind on an entire document kind. This is the same shape ``missing_sections``
    already reports (``Source (5/39)``), one level down.
    """

    unreadable: tuple[tuple[str, str], ...] = ()
    """Documents that could not be read, as ``(path, reason)``.

    A document nobody could read is UNVERIFIED, not absent. Dropping it would
    make every count in this report quietly smaller and still green -- the
    equation BDL-UX #174 and #175 turn on, and the one CONTEXT states as
    *unverifiable is not clean*.
    """

    @property
    def checks_that_read_nothing(self) -> tuple[str, ...]:
        """Checks that found no document with anything to judge."""
        return tuple(
            name for name in CHECK_NAMES if not self.applicable.get(name, 0)
        )

    @property
    def kinds_that_read_nothing(self) -> tuple[str, ...]:
        """Document kinds no CONTENT check enters — a population never entered."""
        return tuple(cov.kind for cov in self.by_kind if cov.is_unread)


# ---------------------------------------------------------------------------
# Reading a markdown document
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Section:
    """One heading and the lines under it, with 1-based line numbers."""

    title: str
    lines: tuple[tuple[int, str], ...]


def _sections(text: str) -> list[_Section]:
    """Split *text* into heading-led sections, skipping fenced code."""
    sections: list[_Section] = []
    title = ""
    body: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        heading = None if fenced else _HEADING_RE.match(line)
        if heading is not None:
            sections.append(_Section(title, tuple(body)))
            title = heading.group(2)
            body = []
            continue
        body.append((number, line))
    sections.append(_Section(title, tuple(body)))
    return sections


def document_status(text: str) -> str:
    """The document's declared status, lowercased, or ``""`` when undeclared."""
    match = _STATUS_RE.search(text)
    return match.group(1).strip().lower() if match else ""


def is_approved(text: str) -> bool:
    """Whether the document declares an agreed status rather than a draft."""
    status = document_status(text)
    return bool(status) and status.split()[0].strip("*_ ") in APPROVED_STATUSES


def _rows(lines: Iterable[tuple[int, str]]) -> list[tuple[int, list[str]]]:
    """Table rows as ``(line number, cells)``, separator rows dropped."""
    out: list[tuple[int, list[str]]] = []
    for number, line in lines:
        match = _TABLE_ROW_RE.match(line)
        if match is None:
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if all(_SEPARATOR_CELL_RE.match(c) for c in cells if c):
            continue
        out.append((number, cells))
    return out


def _column(header: Sequence[str], *names: str) -> int | None:
    """Index of the first header cell whose text names one of *names*."""
    for index, cell in enumerate(header):
        lowered = cell.strip("* ").lower()
        if any(re.search(rf"\b{re.escape(name)}\b", lowered) for name in names):
            return index
    return None


def _bullets(lines: Sequence[tuple[int, str]]) -> list[tuple[int, str]]:
    """Bullet items, each joined with the indented lines that continue it."""
    items: list[tuple[int, list[str]]] = []
    for number, line in lines:
        match = _BULLET_RE.match(line)
        if match is not None:
            items.append((number, [match.group(1)]))
        elif items and line.strip() and line.startswith((" ", "\t")):
            items[-1][1].append(line.strip())
        elif not line.strip():
            continue
    return [(number, " ".join(parts).strip()) for number, parts in items]


def _paragraphs(lines: Sequence[tuple[int, str]]) -> list[tuple[int, str]]:
    """Non-empty paragraphs, each as one joined string."""
    out: list[tuple[int, list[str]]] = []
    for number, line in lines:
        if not line.strip():
            out.append((0, []))
            continue
        if out and out[-1][1]:
            out[-1][1].append(line.strip())
        else:
            out.append((number, [line.strip()]))
    return [(n, " ".join(parts)) for n, parts in out if parts]


# ---------------------------------------------------------------------------
# The five checks
# ---------------------------------------------------------------------------


def _check_goals(path: str, sections: Sequence[_Section]) -> tuple[list[QualityFinding], int]:
    findings: list[QualityFinding] = []
    read = 0
    for section in sections:
        if section.title.strip().lower() not in _GOAL_SECTIONS:
            continue
        statements = _bullets(section.lines) or _paragraphs(section.lines)
        for number, statement in statements:
            if statement.startswith(">"):
                continue
            read += 1
            if _NUMBER_RE.search(statement) is None:
                findings.append(
                    QualityFinding(
                        check=MEASURABLE_GOAL,
                        path=path,
                        line=number,
                        excerpt=_excerpt(statement),
                        why="the goal states no measurable clause",
                        remediation=(
                            "name the quantity the goal moves and the value it "
                            "moves to, so the goal can be shown to be met"
                        ),
                    )
                )
    return findings, read


def _check_table(
    path: str,
    sections: Sequence[_Section],
    *,
    check: str,
    column_names: tuple[str, ...],
    empty: re.Pattern[str] | None,
    why: str,
    remediation: str,
) -> tuple[list[QualityFinding], int]:
    """One row-with-an-empty-cell check, shared by decisions and risks."""
    findings: list[QualityFinding] = []
    read = 0
    for section in sections:
        rows = _rows(section.lines)
        if len(rows) < 2:
            continue
        index = _column(rows[0][1], *column_names)
        if index is None:
            continue
        for number, cells in rows[1:]:
            read += 1
            value = cells[index].strip() if index < len(cells) else ""
            blank = not value or value in {"-", "—"}
            weak = empty is not None and bool(empty.match(value))
            if blank or weak:
                findings.append(
                    QualityFinding(
                        check=check,
                        path=path,
                        line=number,
                        excerpt=_excerpt(" | ".join(cells)),
                        why=why,
                        remediation=remediation,
                    )
                )
    return findings, read


def _check_pending(
    path: str, text: str, sections: Sequence[_Section]
) -> tuple[list[QualityFinding], int]:
    if not is_approved(text):
        return [], 0
    findings: list[QualityFinding] = []
    read = 0
    for section in sections:
        if "open question" not in section.title.lower():
            continue
        rows = _rows(section.lines)
        index = _column(rows[0][1], "decision", "answer", "status") if rows else None
        for number, cells in rows[1:] if rows else []:
            read += 1
            value = cells[index].strip() if index is not None and index < len(cells) else ""
            if _PENDING_RE.match(value):
                findings.append(
                    QualityFinding(
                        check=PENDING_IN_APPROVED,
                        path=path,
                        line=number,
                        excerpt=_excerpt(" | ".join(cells)),
                        why=(
                            "the document is Approved and this question is still "
                            "Pending"
                        ),
                        remediation=(
                            "record the decision and the reason for it here, or "
                            "move the document back out of Approved"
                        ),
                    )
                )
        for number, bullet in _bullets(section.lines):
            read += 1
            if _PENDING_RE.match(bullet.strip("*_ ")):
                findings.append(
                    QualityFinding(
                        check=PENDING_IN_APPROVED,
                        path=path,
                        line=number,
                        excerpt=_excerpt(bullet),
                        why=(
                            "the document is Approved and this question is still "
                            "Pending"
                        ),
                        remediation=(
                            "record the decision and the reason for it here, or "
                            "move the document back out of Approved"
                        ),
                    )
                )
    return findings, read


def _check_placeholders(
    path: str, text: str, placeholders: Sequence[str]
) -> tuple[list[QualityFinding], int]:
    if not placeholders:
        return [], 0
    findings: list[QualityFinding] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            # A fenced block is a QUOTED template, not an unfilled document.
            # Without this the shipped `/templates` command reports every
            # placeholder it exists to define (`.13` met the same shape when a
            # fenced Gherkin template read as a scenario reference).
            continue
        # Symmetric with the derivation: a token inside an inline code span is a
        # command's metavariable (`beadloom ctx <ref-id>`), not a field nobody
        # filled in, and reporting it would flag correct documentation.
        scanned = _INLINE_CODE_RE.sub(" ", line)
        items = _line_items(scanned)
        for token in placeholders:
            if _is_unfilled(token, scanned, items):
                findings.append(
                    QualityFinding(
                        check=UNFILLED_PLACEHOLDER,
                        path=path,
                        line=number,
                        excerpt=_excerpt(line.strip()),
                        why=f"the template placeholder {token!r} was never filled in",
                        remediation="replace it with the document's own content",
                    )
                )
                break
    return findings, 1


def _line_items(line: str) -> list[str]:
    """The self-contained items a line holds: the whole line, its bullet, its cells.

    Each is stripped of markdown decoration and of a trailing parenthetical, so
    ``- [ ] Goal 1 (measurable)`` yields ``Goal 1``.
    """
    candidates = [line.strip()]
    bullet = _BULLET_RE.match(line)
    if bullet is not None:
        candidates.append(bullet.group(1).strip())
    heading = _HEADING_RE.match(line.strip())
    if heading is not None:
        candidates.append(heading.group(2).strip())
    row = _TABLE_ROW_RE.match(line)
    if row is not None:
        candidates.extend(c.strip() for c in row.group(1).split("|"))
    items = []
    for candidate in candidates:
        text = candidate.strip("*_` ").strip()
        text = _TRAILING_PAREN_RE.sub("", text).strip()
        if text:
            items.append(text)
    return items


def _is_unfilled(token: str, line: str, items: list[str]) -> bool:
    """Whether *token* appears in *line* as an unfilled placeholder.

    A bracketed token (``[Name]``, ``<ref-id>``) cannot be mistaken for prose
    and is matched anywhere. An ENUMERATED stub (``Goal 1``, ``Step 2``) can:
    measured on this repository, substring matching reported three real headings
    ("Step 1 (12.12.1): Detection"). It counts only when it is the WHOLE item —
    the entire bullet, cell or heading, bar a trailing parenthetical.
    """
    if token.startswith(("[", "<")):
        return token in line
    return any(item == token for item in items)


def _excerpt(text: str, limit: int = 90) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def check_document(
    text: str,
    *,
    path: str,
    placeholders: Sequence[str] = (),
) -> QualityReport:
    """Run all five checks over one document."""
    sections = _sections(text)
    findings: list[QualityFinding] = []
    applicable: dict[str, int] = {}

    goals, read = _check_goals(path, sections)
    findings.extend(goals)
    applicable[MEASURABLE_GOAL] = read

    decisions, read = _check_table(
        path,
        sections,
        check=DECISION_REASON,
        column_names=("reason", "rationale", "why"),
        empty=None,
        why="the decision carries no reason",
        remediation=(
            "state why this was decided, in terms that do not restate the "
            "decision itself"
        ),
    )
    findings.extend(decisions)
    applicable[DECISION_REASON] = read

    risks, read = _check_table(
        path,
        sections,
        check=RISK_MITIGATION,
        column_names=("mitigation", "remediation"),
        empty=_EMPTY_MITIGATION_RE,
        why="the risk carries no concrete mitigation",
        remediation="name the action that would be taken, and by whom",
    )
    findings.extend(risks)
    applicable[RISK_MITIGATION] = read

    pending, read = _check_pending(path, text, sections)
    findings.extend(pending)
    applicable[PENDING_IN_APPROVED] = read

    unfilled, read = _check_placeholders(path, text, placeholders)
    findings.extend(unfilled)
    applicable[UNFILLED_PLACEHOLDER] = read

    findings.sort(key=lambda f: (f.path, f.line, f.check))
    return QualityReport(
        findings=tuple(findings), documents=1, applicable=applicable
    )


def document_kind(path: str) -> str:
    """The kind of document a path names — ``PRD.md`` is a ``PRD``.

    The stem, because that is how the shipped flow names a document and it needs
    no configuration to derive. A project whose documents are ``prd.md`` gets
    ``prd`` as a kind of its own, which is honest: nothing here was told the two
    are the same thing.
    """
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    stem, _, _ = name.rpartition(".")
    return (stem or name).strip()


def check_documents(
    paths: Iterable[Path],
    *,
    project_root: Path,
    placeholders: Sequence[str] = (),
) -> QualityReport:
    """Run all five checks over every document in *paths*, and per document kind."""
    findings: list[QualityFinding] = []
    applicable: dict[str, int] = dict.fromkeys(CHECK_NAMES, 0)
    unreadable: list[tuple[str, str]] = []
    per_kind: dict[str, dict[str, int]] = {}
    kind_documents: dict[str, int] = {}
    kind_unreadable: dict[str, int] = {}
    documents = 0
    for path in sorted(paths):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # A planning document is a UTF-8 CONTRACT, so a decode failure is a
            # real answer about the document -- not a reason to abandon the run.
            # `UnicodeDecodeError` is a `ValueError`, so the old `except OSError`
            # let it escape `beadloom ci` entirely: one such file produced a
            # traceback and NO step results at all, for every check in the gate.
            # Fifth instance of this family in BDL-061 (.36, .37, .40, .42).
            try:
                where = str(path.relative_to(project_root))
            except ValueError:
                where = str(path)
            unreadable.append((where, f"{type(exc).__name__}: {exc}"))
            kind = document_kind(where)
            kind_unreadable[kind] = kind_unreadable.get(kind, 0) + 1
            per_kind.setdefault(kind, dict.fromkeys(CHECK_NAMES, 0))
            continue
        documents += 1
        try:
            relative = str(path.relative_to(project_root))
        except ValueError:
            relative = str(path)
        kind = document_kind(relative)
        kind_documents[kind] = kind_documents.get(kind, 0) + 1
        counts = per_kind.setdefault(kind, dict.fromkeys(CHECK_NAMES, 0))
        report = check_document(text, path=relative, placeholders=placeholders)
        findings.extend(report.findings)
        for name, count in report.applicable.items():
            applicable[name] = applicable.get(name, 0) + count
            counts[name] = counts.get(name, 0) + count
    findings.sort(key=lambda f: (f.path, f.line, f.check))
    return QualityReport(
        findings=tuple(findings),
        documents=documents,
        applicable=applicable,
        by_kind=tuple(
            KindCoverage(
                kind=kind,
                documents=kind_documents.get(kind, 0),
                applicable=per_kind[kind],
                unreadable=kind_unreadable.get(kind, 0),
            )
            for kind in sorted(per_kind)
        ),
        unreadable=tuple(unreadable),
    )
