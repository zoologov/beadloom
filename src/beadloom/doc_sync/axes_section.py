# beadloom:domain=doc-sync
# beadloom:feature=axes-section
"""The ``## Axes`` section of a work item's document: one grammar, read both ways.

BDL-068 S1.3 measured, at ``af26750d``, that the same derivations list **2**
writers and **4** branches seeded from the commit point and **0** writers and
**3** branches seeded from the function the bead was changing — one tree, one
day, one derivation. The axes are therefore a property of the SEED. A section
that states axes without naming the seed they came from is a clean, confident
number with no way to tell which of those two runs produced it, so naming the
seed is the one thing this module refuses to let a document leave out.

**One home, three renderings.** CONTEXT Q1 decides that the axes are DERIVED by
``beadloom impact``, that the document records the derivation's output and the
human's scope decision, and that the bead's ``refs:`` is GENERATED from the
document. The grammar therefore lives here, in the domain whose subject is
documents: :mod:`beadloom.application.impact.section` renders a section using
these names, and :func:`read_axes_section` reads one back. A round-trip test
holds the two together, which is what stops the writer and the reader becoming
two things that can disagree — the class this epic exists to remove.

**An absent seed is not an empty axis.** ``beadloom impact`` reports a target it
finds no seed for as ``none``, with every axis below it unresolved rather than
empty, and this section must not flatten that: :data:`NO_SEED` is a stated seed
and satisfies the check, while a missing ``Seed`` field does not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.doc_sync.doc_quality import QualityFinding
from beadloom.doc_sync.doc_shape import read_sections, table_cells

if TYPE_CHECKING:
    from collections.abc import Sequence

#: The section's heading, and the name the templates carry.
AXES_HEADING = "Axes"

#: The blockquote fields the derivation writes above the table. ``Seed`` is the
#: one a check reads; the other two are the run's provenance, and a reader who
#: wants to re-run the derivation needs the target it was run on.
DERIVED_BY_FIELD = "Derived by"
SEED_FIELD = "Seed"
UNRESOLVED_FIELD = "Unresolved"

#: What a resolved absence is spelled as — the word ``impact`` itself reports
#: when the seed rule finds no sink. Stating it IS naming the seed.
NO_SEED = "none"

#: The table's columns, in order. The first three are the derivation's output;
#: the last two are the person's scope decision, and the split is deliberate —
#: a section carrying only the first three records a run nobody has ruled on.
COLUMNS: tuple[str, ...] = ("Axis", "Node", "Sites", "In scope", "Why")

#: The section states axes and does not name the seed they were derived from.
AXES_WITHOUT_A_SEED = "axes-without-a-seed"

#: A row carrying the derivation's half and no decision in the ``In scope``
#: cell. The empty ``Why`` cell is deliberately NOT reported here: the
#: ``decision-reason`` check already reports a table row whose reason cell is
#: empty, and a second reporter of one fault is a second thing to keep in step.
AXIS_WITHOUT_A_SCOPE_DECISION = "axis-without-a-scope-decision"

#: Every check this module runs, in report order.
CHECK_NAMES: tuple[str, ...] = (AXES_WITHOUT_A_SEED, AXIS_WITHOUT_A_SCOPE_DECISION)

_FIELD_RE = re.compile(r"^>\s*\*\*(?P<name>[A-Za-z ]+):\*\*\s*(?P<value>.*)$")
_QUOTE_RE = re.compile(r"^>\s?(.*)$")

#: Cells that decide the scope, exactly. Matched whole so the shipped skeleton's
#: ``yes / no`` — which offers both and chooses neither — is undecided rather
#: than read as a "yes" because the word occurs in it.
_IN_SCOPE = frozenset({"yes", "y", "in", "in scope"})
_OUT_OF_SCOPE = frozenset({"no", "n", "out", "out of scope"})

#: A node cell that names nothing: the em dash a derivation writes for an
#: unresolved axis, and the token the skeleton leaves for the author.
_NAMES_NO_NODE = frozenset(
    {"", "-", "\u2014", "\u2013", "[ref-id]", "n/a"}
)


@dataclass(frozen=True)
class Axis:
    """One row: what the derivation found, and what a person decided about it."""

    axis: str
    node: str
    sites: str
    #: ``None`` when the cell decides nothing — the state a rendered section is
    #: born in, and the one the check exists to report.
    in_scope: bool | None
    why: str
    line: int


@dataclass(frozen=True)
class AxesSection:
    """A document's ``## Axes`` section, as read."""

    line: int
    seed: str = ""
    derived_by: str = ""
    unresolved: str = ""
    axes: tuple[Axis, ...] = ()

    @property
    def names_a_seed(self) -> bool:
        """Whether the section says what the axes below it were derived from."""
        return bool(self.seed.strip())

    @property
    def kept(self) -> tuple[Axis, ...]:
        """The rows a person decided are inside this work item's scope."""
        return tuple(axis for axis in self.axes if axis.in_scope)


def _scope_of(cell: str) -> bool | None:
    lowered = cell.strip().strip("*_` ").lower()
    if lowered in _IN_SCOPE:
        return True
    if lowered in _OUT_OF_SCOPE:
        return False
    return None


def _named(cell: str) -> str:
    """A node cell reduced to the ref-id it names, or ``""`` when it names none."""
    text = cell.strip().strip("*_` ")
    return "" if text.lower() in _NAMES_NO_NODE else text


def read_axes_section(text: str) -> AxesSection | None:
    """The document's ``## Axes`` section, or ``None`` when it carries none.

    ``None`` and an empty section are different answers and are kept apart: a
    document with no section at all is ``missing-section``'s finding, and one
    with a heading and nothing under it is ``empty-section``'s.
    """
    for section in read_sections(text):
        if section.title.strip() != AXES_HEADING:
            continue
        return _read_body(section.lineno, section.body)
    return None


def _read_body(lineno: int, body: Sequence[str]) -> AxesSection:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    axes: list[Axis] = []
    header: list[str] | None = None
    for offset, line in enumerate(body, start=1):
        field = _FIELD_RE.match(line)
        if field is not None:
            current = field.group("name").strip()
            fields.setdefault(current, []).append(field.group("value").strip())
            continue
        quoted = _QUOTE_RE.match(line)
        if quoted is not None and current is not None:
            # A field wrapped over several blockquote lines is one value: the
            # shipped skeleton wraps at 95 columns like every other document.
            fields[current].append(quoted.group(1).strip())
            continue
        current = None
        cells = table_cells(line)
        if cells is None:
            continue
        if header is None:
            header = [cell.strip("*_ ").lower() for cell in cells]
            continue
        axes.append(_row(cells, header, lineno + offset))
    return AxesSection(
        line=lineno,
        seed=" ".join(fields.get(SEED_FIELD, ())).strip(),
        derived_by=" ".join(fields.get(DERIVED_BY_FIELD, ())).strip(),
        unresolved=" ".join(fields.get(UNRESOLVED_FIELD, ())).strip(),
        axes=tuple(axes),
    )


def _row(cells: Sequence[str], header: Sequence[str], line: int) -> Axis:
    def column(name: str) -> str:
        wanted = name.lower()
        index = header.index(wanted) if wanted in header else -1
        return cells[index] if 0 <= index < len(cells) else ""

    return Axis(
        axis=column("axis"),
        node=_named(column("node")),
        sites=column("sites"),
        in_scope=_scope_of(column("in scope")),
        why=column("why"),
        line=line,
    )


def refs_line(section: AxesSection) -> str:
    """The bead's ``refs:`` line, generated from the rows kept in scope.

    Deduplicated in the table's own order: one node named by two axes is one
    ref, and the order a reader sees in the document is the order the bead
    carries, so the two can be compared by eye as well as by a check.
    """
    seen: list[str] = []
    for axis in section.kept:
        if axis.node and axis.node not in seen:
            seen.append(axis.node)
    return "refs: " + ", ".join(seen)


def check_axes_section(path: str, text: str) -> tuple[QualityFinding, ...]:
    """Report an ``## Axes`` section that answers less than it appears to."""
    section = read_axes_section(text)
    if section is None or not section.axes:
        return ()
    findings: list[QualityFinding] = []
    if not section.names_a_seed:
        findings.append(
            QualityFinding(
                check=AXES_WITHOUT_A_SEED,
                path=path,
                line=section.line,
                excerpt=f"{len(section.axes)} axis row(s) and no {SEED_FIELD} field",
                why=(
                    "the section states axes without naming the seed they were "
                    "derived from — the same derivation reports two writers under "
                    "one seed and none under another, so the axes cannot be "
                    "checked against the run that produced them"
                ),
                remediation=(
                    f"add the `> **{SEED_FIELD}:**` field with the seed "
                    f"`beadloom impact` named, or `{NO_SEED}` when the rule found "
                    f"none — in which case every axis below it is unresolved"
                ),
            )
        )
    findings.extend(
        QualityFinding(
            check=AXIS_WITHOUT_A_SCOPE_DECISION,
            path=path,
            line=axis.line,
            excerpt=f"{axis.axis} | {axis.node or '—'}",
            why=(
                "the axis carries the derivation's output and no scope decision "
                "— the section records what a change ranges over and how much of "
                "it this work item takes, and this row states only the first"
            ),
            remediation=(
                "decide the row: `yes` if this work item takes the axis, `no` "
                "with the reason if it does not"
            ),
        )
        for axis in section.axes
        if axis.in_scope is None
    )
    return tuple(findings)
