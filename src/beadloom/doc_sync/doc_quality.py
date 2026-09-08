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
    A goal whose predicate is a quality and which names nothing an observer
    could go and look at. "Make it better" is not a goal; "the core shrinks
    from 440 to 376 lines" is.
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
a reader who trusted it: a reason is checked for EXISTENCE, not for explaining
rather than restating the decision, which no checker decides; and a mitigation
is judged against a named set of empty ones rather than on whether it would
work.

``measurable-goal`` was the fourth (BDL-061 `.70`). It shipped as a numeral
detector calling the absence of a digit "no measurable clause", and on this
repository that reported **154 of 235** goal statements at roughly 1-in-18
precision — including ``beadloom lint --strict fails (non-zero)`` and
``beadloom federate --fail-on ... exits non-zero``, which are the exit-code form
BDL-UX #148 exists to demand. A check satisfied by inserting a numeral into a
correct sentence teaches an author to write for the checker, which is the
failure #169 was fixed by NOT doing. So the criterion is now the one its three
siblings already use: name the EMPTY FORM rather than guess at the good one. A
goal is reported when both legs hold — its predicate is an unbounded improvement
(:func:`states_an_unbounded_improvement`) and it names no witness
(:func:`names_a_witness`). Measured on the same corpus: **4 of 232**, and the
four are the standard's own example ("Make Beadloom enjoyable and intuitive").

**Its limit, measured rather than asserted.** Precision was bought with recall.
Of the 150 statements the re-scope newly accepts, **27 name no witness either**
— they are accepted because their predicate is not an unbounded improvement, and
about those this check now decides nothing ("Turn prose into mechanisms",
"Clear separation between policy and fact sections"). That is deliberate: a
check firing on 66% of a corpus does not get satisfied, it gets excluded, and an
excluded check decides nothing about 100%. A goal this check accepts is not
thereby proved measurable.

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

from beadloom.doc_sync.tables import Table, cells_of, table_blocks

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
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

#: The header cells a table states its reasons under. One tuple, because the
#: check that reads a document and the derivation that reads the templates must
#: agree about what a reason column is or they classify different tables.
REASON_COLUMNS: tuple[str, ...] = ("reason", "rationale", "why")

#: Mitigations that name no action. Matched as the WHOLE cell, so "monitor the
#: queue depth and page above 80%" is a mitigation and "monitor it" is not.
_EMPTY_MITIGATION_RE = re.compile(
    r"^(?:monitor|watch|observe|be\s+careful|careful|tbd|todo|n/?a|none|-|—|\?)"
    r"(?:\s+(?:it|them|this|closely|carefully))?[.!]?$",
    re.IGNORECASE,
)

#: A number that is not part of an identifier. ``BDL-061`` and ``v2.2`` are
#: names with digits in them; ``440 -> 376 lines`` is a quantity.
_NUMBER_RE = re.compile(r"(?<![\w.\-])\d")

#: An artifact named in a way that leaves no doubt it IS one: an inline code
#: span, a command flag, a file name, a snake_case identifier. Prose is
#: deliberately not enough — this recognizer only ever ACCEPTS a goal, so a
#: loose one lowers the finding count silently, and that is the single way this
#: criterion could be worse than the numeral it replaces. ``e.g.``, ``i.e.``,
#: ``etc.`` and ``vs.`` are excluded by the two-character stem and by requiring
#: the suffix to follow the dot with no space. A bare slashed path is
#: deliberately NOT a branch of its own: it accepted the prose enumeration
#: "fresh/stale/missing docs", while every path this corpus states in a goal
#: carries a file name (``docs/guides/ci-setup.md``) or a code span anyway.
_ARTIFACT_RE = re.compile(
    r"`[^`\n]+`"
    r"|(?<![\w-])--[a-z][\w-]+"
    r"|\b\w{2,}\.[a-z]{2,4}\b"
    r"|\b[a-z][a-z0-9]*_[a-z0-9_]+\b"
)

#: An outcome a run or a reader can witness. Closed and listed rather than
#: inferred: a verb list that grows whenever a document is reported is a
#: tolerance wearing a criterion's name.
_OUTCOME_RE = re.compile(
    r"\b(?:exits?|non-zero|rc|fails?|passes|catches|detects?|reports?|renders?"
    r"|produces?|shows?|works?|builds?|generates?|blocks?|refuses?|emits?"
    r"|green|red|no longer)\b",
    re.IGNORECASE,
)

#: A quality — a word that says how good something is, not what it does. The
#: reader of "make it faster" cannot say whether it happened.
_QUALITY = (
    r"(?:better|best|fast(?:er)?|quick(?:er)?|simple(?:r)?|clean(?:er)?"
    r"|nice(?:r)?|easy|easier|useful|usable|user-friendly|enjoyable|intuitive"
    r"|robust|solid|seamless|smooth|powerful|comprehensive|modern|elegant"
    r"|pleasant|delightful|maintainable|readable|good|great)"
)

#: The form the writing standard rejects: an unbounded improvement. Either a
#: verb whose completion nothing observes (``improve``, ``establish``, ``clean
#: up``) or ``make/keep <something> <quality>`` — the standard's own example.
_IMPROVEMENT_RE = re.compile(
    r"\b(?:improve|enhance|optimi[sz]e|polish|streamline|moderni[sz]e"
    r"|strengthen|establish|clean\s+up|tidy\s+up)\w*\b"
    r"|\b(?:make|makes|making|keep|keeps|keeping|render|leave)\b"
    r"[^.;:!?]{0,60}?\b" + _QUALITY + r"\b",
    re.IGNORECASE,
)

#: A markdown horizontal rule. Not a paragraph, and never a goal statement:
#: three of the 235 statements this check read on its own repository were
#: ``---`` closing a Goal section (review BDL-061.15 m1).
_HRULE_RE = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")

#: A heading's leading enumeration — ``9.``, ``5.2``, ``Step 3:``. Stripped
#: before a section title is compared with a name the templates declare, because
#: this corpus numbers its headings and the templates do not.
_SECTION_NUMBER_RE = re.compile(r"^[\d.\s)\-]+")

_HEADING_RE = re.compile(r"^(#{1,6}) +(.+?)\s*$")
_STATUS_RE = re.compile(r"^>\s*\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(?:\[[ xX]\]\s*)?(.*)$")
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
class UnclassifiedTable:
    """A table carrying a reason column that the document never declares as decisions.

    A verdict, not a finding. The check can see that the table states reasons
    and cannot see whether the rows are decisions, so it says which table it did
    not judge and where to look, and reports nothing against its rows.
    """

    path: str
    line: int
    section: str
    header: str
    rows: int


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

    unclassified: tuple[UnclassifiedTable, ...] = ()
    """Tables ``decision-reason`` could not classify, and therefore did not judge.

    Their rows are absent from :attr:`applicable` as well as from
    :attr:`findings`: a row nothing judged is not a row something read, and
    counting it would make the check's population look larger than the part of
    it that was verified.
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


def _tables(lines: Iterable[tuple[int, str]]) -> list[Table]:
    """The tables under one heading, each as its own ``(line number, cells)`` rows.

    The boundary rule itself lives in :mod:`beadloom.doc_sync.tables`, because
    the ``## Axes`` reader needed the same answer and BDL-UX #244 is what a
    second copy of it costs. This name stays as the vocabulary this module's
    checks are written in.
    """
    return table_blocks(lines)


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
        if not line.strip() or _HRULE_RE.match(line):
            # A horizontal rule separates paragraphs; it is not one of them.
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


def names_a_witness(statement: str) -> bool:
    """Whether *statement* names something an observer could go and look at.

    Three kinds, and any one is enough: a QUANTITY (``440 -> 376 lines``), a
    named ARTIFACT (``beadloom lint --strict``, ``AGENTS.md``, ``scan_paths``),
    or an observable OUTCOME (``exits non-zero``, ``the build passes``).
    """
    return bool(
        _NUMBER_RE.search(statement)
        or _ARTIFACT_RE.search(statement)
        or _OUTCOME_RE.search(statement)
    )


def states_an_unbounded_improvement(statement: str) -> bool:
    """Whether *statement*'s predicate is a quality rather than an outcome.

    "Make the tool better", "improve the developer experience", "establish the
    architecture" — forms whose completion nobody can date.
    """
    return bool(_IMPROVEMENT_RE.search(statement))


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
            if states_an_unbounded_improvement(statement) and not names_a_witness(
                statement
            ):
                findings.append(
                    QualityFinding(
                        check=MEASURABLE_GOAL,
                        path=path,
                        line=number,
                        excerpt=_excerpt(statement),
                        why=(
                            "the goal states an improvement with no witness — it "
                            "names a quality, and no quantity, artifact or "
                            "outcome that would show it happened"
                        ),
                        remediation=(
                            "name the quantity the goal moves and the value it "
                            "moves to, the artifact it produces, or the outcome "
                            "a run would show"
                        ),
                    )
                )
    return findings, read


def declares_decisions(
    section_title: str,
    header: Sequence[str],
    *,
    declared_sections: Sequence[str] = (),
) -> bool:
    """Whether the DOCUMENT declares this table as a table of decisions.

    Two legs, and both read a declaration the document made about itself rather
    than guessing at what its rows mean:

    * a column naming the thing decided (``Decision``, ``Scope decision``), or
    * a section the shipped templates put a reason-carrying decision table
      under, which is where *declared_sections* comes from
      (:func:`beadloom.application.doc_shape.shipped_decision_sections`).

    Nothing here reads the CELLS, because nothing could. A row saying
    ``| 7341 passing | confirmed, 0 failed |`` and a row saying
    ``| guards are data | a shell script is not portable |`` are the same two
    strings to a checker, and BDL-UX #213 is what happens when one is judged as
    the other. Where neither leg holds the answer is ``not classified``, which
    the caller reports and does not turn into a finding.

    A leading number is stripped from the section title, so ``## 9. Decision
    Log`` is the section ``Decision Log``; documents in this corpus number their
    headings and the templates do not.
    """
    if _column(header, "decision", "decisions") is not None:
        return True
    title = _SECTION_NUMBER_RE.sub("", section_title.strip().lower())
    return any(
        re.search(rf"\b{re.escape(name)}\b", title)
        for name in declared_sections
        if name
    )


def sections_with_a_decision_table(text: str) -> tuple[str, ...]:
    """Section titles under which *text* states a table carrying a reason column.

    Used against the SHIPPED templates, to derive the sections this flow puts a
    decision table under. It lives here rather than beside that derivation
    because the answer must be given in the same vocabulary the check reads a
    real document in: a section title, a table boundary and a reason column,
    decided once.
    """
    titles: set[str] = set()
    for section in _sections(text):
        title = section.title.strip().lower()
        if not title:
            continue
        for rows in _tables(section.lines):
            if _column(rows[0][1], *REASON_COLUMNS) is not None:
                titles.add(title)
    return tuple(sorted(titles))


def _check_table(
    path: str,
    sections: Sequence[_Section],
    *,
    check: str,
    column_names: tuple[str, ...],
    empty: re.Pattern[str] | None,
    why: str,
    remediation: str,
    declares: Callable[[str, Sequence[str]], bool] | None = None,
) -> tuple[list[QualityFinding], int, list[UnclassifiedTable]]:
    """One row-with-an-empty-cell check, shared by decisions and risks.

    *declares* decides which tables carrying the column are this check's
    business. ``risk-mitigation`` passes none and judges every one of them: a
    ``Mitigation`` column names an action taken against a risk and has no
    homonym in another kind of table, so there is nothing to tell apart. A
    ``Reason`` column does have one, which is why ``decision-reason`` passes
    :func:`declares_decisions` and reports the tables it cannot place.
    """
    findings: list[QualityFinding] = []
    read = 0
    unclassified: list[UnclassifiedTable] = []
    for section in sections:
        for rows in _tables(section.lines):
            if len(rows) < 2:
                continue
            header_line, header = rows[0]
            index = _column(header, *column_names)
            if index is None:
                continue
            if declares is not None and not declares(section.title, header):
                unclassified.append(
                    UnclassifiedTable(
                        path=path,
                        line=header_line,
                        section=section.title,
                        header=" | ".join(header),
                        rows=len(rows) - 1,
                    )
                )
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
    return findings, read, unclassified


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
        # Each table under the heading is read against ITS OWN header. The
        # reader this replaced took the first table's column index and applied
        # it to every later table's rows (BDL-UX #213), which in this section
        # would judge a second table's cells under a heading they never had.
        for rows in _tables(section.lines):
            index = _column(rows[0][1], "decision", "answer", "status")
            for number, cells in rows[1:]:
                read += 1
                value = (
                    cells[index].strip()
                    if index is not None and index < len(cells)
                    else ""
                )
                if not _PENDING_RE.match(value):
                    continue
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
    row = cells_of(line)
    if row is not None:
        candidates.extend(row)
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
    decision_sections: Sequence[str] = (),
) -> QualityReport:
    """Run all five checks over one document.

    *decision_sections* names the sections the shipped templates put a
    reason-carrying decision table under. Passed in rather than derived here for
    the reason *placeholders* is: this module is a domain and the templates are
    composed one layer up.
    """
    sections = _sections(text)
    findings: list[QualityFinding] = []
    applicable: dict[str, int] = {}

    goals, read = _check_goals(path, sections)
    findings.extend(goals)
    applicable[MEASURABLE_GOAL] = read

    def _declares(title: str, header: Sequence[str]) -> bool:
        return declares_decisions(title, header, declared_sections=decision_sections)

    decisions, read, unclassified = _check_table(
        path,
        sections,
        check=DECISION_REASON,
        column_names=REASON_COLUMNS,
        empty=None,
        why="the decision carries no reason",
        remediation=(
            "state why this was decided, in terms that do not restate the "
            "decision itself"
        ),
        declares=_declares,
    )
    findings.extend(decisions)
    applicable[DECISION_REASON] = read

    risks, read, _ = _check_table(
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
        findings=tuple(findings),
        documents=1,
        applicable=applicable,
        unclassified=tuple(unclassified),
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
    decision_sections: Sequence[str] = (),
) -> QualityReport:
    """Run all five checks over every document in *paths*, and per document kind."""
    findings: list[QualityFinding] = []
    applicable: dict[str, int] = dict.fromkeys(CHECK_NAMES, 0)
    unclassified: list[UnclassifiedTable] = []
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
        report = check_document(
            text,
            path=relative,
            placeholders=placeholders,
            decision_sections=decision_sections,
        )
        findings.extend(report.findings)
        unclassified.extend(report.unclassified)
        for name, count in report.applicable.items():
            applicable[name] = applicable.get(name, 0) + count
            counts[name] = counts.get(name, 0) + count
    findings.sort(key=lambda f: (f.path, f.line, f.check))
    return QualityReport(
        findings=tuple(findings),
        documents=documents,
        applicable=applicable,
        unclassified=tuple(unclassified),
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
