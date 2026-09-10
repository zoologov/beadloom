# beadloom:domain=application
# beadloom:component=work-item-routing
"""The routes ``/task-init`` declares, derived from the composed command itself.

A work item's TYPE is a claim about how far the change ranges, and the route it
takes decides which documents get written and which approval gates it passes.
The documents EVERY route writes are derived here too, because a document no
route can avoid is one every bead of a work item writes and no bead's code owns
(:attr:`Routing.shared_kinds`, BDL-UX #257).
Until BDL-068 S1.5 the routing table was prose an agent read and nothing more:
BDL-067 was routed ``bug``, wrote one BRIEF, passed one approval gate and became
28 beads, and re-deriving its axes afterwards showed the change ranging over
four graph nodes.

The check that reports that now reads the SAME table the command states, rather
than a second copy of it declared in Python. A project layer that adds a type or
moves one between flows changes the check by the same act, and the command
cannot state a route the check does not police — which is the whole difference
between an instrument and advice.

The join happens in ``application`` for the reason
:mod:`beadloom.application.doc_shape` states: the composed command lives in
``onboarding``, the check that reads a document lives in ``doc_sync``, the two
are peer domains and neither may import the other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.doc_sync.tables import table_blocks
from beadloom.onboarding.composer import compose
from beadloom.onboarding.doc_templates import DEFAULT_DOC_CONFIG, doc_flow_config
from beadloom.onboarding.flow_config import FlowConfigError
from beadloom.onboarding.role_composer import ROLE_NAMES

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.doc_sync.tables import Table
    from beadloom.onboarding.flow_config import FlowConfig

#: The composed artifact the routing is read from.
TASK_INIT_COMMAND = ("commands", "task-init")

#: The two flows the command distinguishes. Lower-cased labels rather than the
#: cell's own words, because a cell reads ``Simplified: BRIEF → ACTIVE`` and the
#: label is the part a check compares.
SIMPLIFIED = "simplified"
FULL = "full"

#: The role whose deliverable the type decision is made from. Named here and
#: checked against the derived role population, so removing the fragment breaks
#: this derivation loudly instead of leaving a step nothing launches.
AXES_ROLE = "explore"

#: The routing table's header, matched by its first two columns. The third
#: column's title has changed once already ("Docs" -> "Docs created"), so the
#: match is on what identifies the table rather than on its full width.
#:
#: Matched against a TABLE'S HEADER ROW and not against any row that spells it
#: (BDL-UX #259). A command documenting its own routing quotes this row as an
#: example, and the reader that matched the first row anywhere took the example
#: for the table.
_HEADER = ("type", "flow")

#: The rows the routing table states that this derivation could not read as a
#: route, reported rather than dropped. A silent omission and a clean run read
#: alike, and the omission is the worse of the two directions here: the type's
#: document kinds leave :attr:`Routing.simplified_kinds`, so every work item of
#: that type falls out of the population `check_work_item_types` judges.
_UNREAD_ROWS = (
    "task-init's routing table states {count} row(s) this derivation could not "
    "read as a route ({rows}), so no flow and no document set is derived for them"
)

#: A ``##`` heading, and the launch of a subagent inside a step's body.
_HEADING_RE = re.compile(r"^#{2,3} +(?P<title>.+?)\s*$")
_SUBAGENT_RE = re.compile(r"subagent_type\s*[:=]\s*[\"']?(?P<role>[a-z-]+)")

#: A cell's contents reduced to the names it lists: ``PRD, RFC, CONTEXT`` and
#: ``BRIEF → ACTIVE`` are both lists of document kinds.
_NAME_RE = re.compile(r"\b([A-Z]{3,})\b")


@dataclass(frozen=True)
class Route:
    """One row of the routing table: a type, its flow, and the documents it writes."""

    type: str
    flow: str
    documents: tuple[str, ...]


@dataclass(frozen=True)
class Routing:
    """What ``/task-init`` declares about types, flows and the order of its steps.

    ``notes`` carries the honest skips, the way :class:`Composition` does: a
    command whose routing table this derivation could not find says so rather
    than returning an empty routing that reads as "no types are declared".
    """

    routes: tuple[Route, ...] = ()
    #: Line of the step that derives the axes, and its heading text.
    explore_line: int | None = None
    explore_step: str = ""
    #: Line of the heading the type decision is taken under.
    decision_line: int | None = None
    notes: tuple[str, ...] = ()

    def flow_of(self, work_item_type: str) -> str | None:
        """The flow a type is routed through, or ``None`` for a type not declared."""
        wanted = work_item_type.strip().lower()
        for route in self.routes:
            if route.type == wanted:
                return route.flow
        return None

    @property
    def simplified_kinds(self) -> frozenset[str]:
        """Document kinds written ONLY by types on the simplified route.

        A kind both routes write — ``ACTIVE`` — identifies neither, so it is not
        in here. What is left is the set that tells a work item's route from the
        documents on disk, which is the only evidence a check over a folder has.
        """
        return self._kinds_unique_to(SIMPLIFIED)

    @property
    def full_kinds(self) -> frozenset[str]:
        """Document kinds written ONLY by types on the full route."""
        return self._kinds_unique_to(FULL)

    @property
    def shared_kinds(self) -> frozenset[str]:
        """Document kinds EVERY route writes — the third face of one computation.

        The two properties above take a difference to answer *which route is this
        work item on*. This one takes the intersection to answer a question
        `beadloom waves` asks: which document does every bead of every work item
        write into, whatever its type. On this project's own routing table the
        answer is ``ACTIVE``, which the docstring above already names as the kind
        identifying neither route.

        It is the derived half of BDL-UX #257. A wave plan resolves a bead to the
        nodes and files its CODE occupies, so a document every route writes and
        no node owns is shared by every wave and compared by none of them. The
        population has to be derived or it rots (`beadloom-0mdo.51`), and this is
        where it is derived from: a project that adds a type, or moves a document
        between the two flows, changes this answer by the same act.

        Empty when no route was read, which is the honest answer rather than the
        vacuous intersection over nothing.
        """
        if not self.routes:
            return frozenset()
        kinds = [frozenset(route.documents) for route in self.routes]
        return frozenset.intersection(*kinds)

    @property
    def explore_precedes_the_decision(self) -> bool:
        """Whether the step that derives the axes is stated before the type decision."""
        if self.explore_line is None or self.decision_line is None:
            return False
        return self.explore_line < self.decision_line

    def _kinds_unique_to(self, flow: str) -> frozenset[str]:
        mine: set[str] = set()
        others: set[str] = set()
        for route in self.routes:
            (mine if route.flow == flow else others).update(route.documents)
        return frozenset(mine - others)


def _flow_label(cell: str) -> str:
    lowered = cell.lower()
    if SIMPLIFIED in lowered:
        return SIMPLIFIED
    if FULL in lowered:
        return FULL
    return ""


def _label(cell: str) -> str:
    """A cell reduced to the word it names, without its markdown emphasis."""
    return cell.strip("*_` ").lower()


def _routing_tables(lines: list[str]) -> list[Table]:
    """Every table whose own HEADER ROW names the routing columns.

    The boundary rule is :mod:`beadloom.doc_sync.tables`', because this is its
    third reader and the first two disagreed about it hours apart in one slice
    (BDL-UX #213, #244). ``table_blocks`` returns each contiguous table with its
    own header row leading, so a routing table is a table here rather than
    "everything below the first row that spelled the header".

    **A union, not the first match, and that was measured rather than chosen.**
    ``/task-init`` composes a project layer under the core, and a layer that adds
    a type states its own routing table under its own heading — the capability
    `beadloom-0mdo.5` built this derivation for. Reading only the first table
    would have dropped that type, and a route this reader loses removes every
    work item of it from the population `check_work_item_types` judges. It is
    also the rule the ``## Axes`` reader already follows for the same reason: a
    section holds one table per slice, and the answer is their union with each
    table's rows judged against its own header.
    """
    tables = []
    for table in table_blocks(enumerate(lines, start=1)):
        header = [_label(cell) for cell in table[0][1]]
        if tuple(header[: len(_HEADER)]) == _HEADER:
            tables.append(table)
    return tables


def _routes_in(
    lines: list[str],
) -> tuple[tuple[Route, ...], int | None, tuple[str, ...]]:
    """The routing tables' routes, the line the first starts on, and the rows lost.

    Membership is decided by the table and not by the words in a cell. The
    reader this replaced kept a row when its second cell contained ``simplified``
    or ``full``, which held on this project's own documents by arithmetic rather
    than by rule: of 5 122 table rows in 456 markdown files here, that test
    admits 27, and 17 of them belong to other tables in other documents.
    """
    tables = _routing_tables(lines)
    if not tables:
        return (), None, ()
    routes: list[Route] = []
    unread: list[str] = []
    for table in tables:
        for lineno, cells in table[1:]:
            flow = _flow_label(cells[1]) if len(cells) > 1 else ""
            if len(cells) < 3 or not flow:
                unread.append(f"line {lineno}: {_label(cells[0]) or '(unnamed)'}")
                continue
            routes.append(
                Route(
                    type=_label(cells[0]),
                    flow=flow,
                    documents=tuple(dict.fromkeys(_NAME_RE.findall(cells[2]))),
                )
            )
    return tuple(routes), tables[0][0][0], tuple(unread)


def _explore_step(lines: list[str]) -> tuple[int | None, str]:
    """The heading line and text of the step that launches the axes role."""
    heading_line: int | None = None
    heading_text = ""
    for lineno, line in enumerate(lines, start=1):
        heading = _HEADING_RE.match(line)
        if heading is not None:
            heading_line = lineno
            heading_text = heading.group("title")
            continue
        launch = _SUBAGENT_RE.search(line)
        if launch is not None and launch.group("role") == AXES_ROLE:
            return heading_line, heading_text
    return None, ""


def read_routing(text: str) -> Routing:
    """Derive the routing from a composed ``/task-init`` command's text."""
    lines = text.splitlines()
    routes, table_line, unread = _routes_in(lines)
    explore_line, explore_step = _explore_step(lines)
    notes: list[str] = []
    if table_line is None:
        notes.append(
            "task-init states no routing table (a header row of "
            f"{' | '.join(_HEADER)}), so no type is judged against its axes"
        )
    if unread:
        notes.append(_UNREAD_ROWS.format(count=len(unread), rows="; ".join(unread)))
    if AXES_ROLE not in ROLE_NAMES:
        notes.append(
            f"no role named {AXES_ROLE!r} ships a core fragment, so the step that "
            "derives the axes launches nothing"
        )
    elif explore_line is None:
        notes.append(
            f"task-init launches no {AXES_ROLE!r} subagent, so the type decision "
            "rests on nothing derived"
        )
    return Routing(
        routes=routes,
        explore_line=explore_line,
        explore_step=explore_step,
        decision_line=table_line,
        notes=tuple(notes),
    )


def task_init_routing(
    *,
    config: FlowConfig | None = None,
    project_root: Path | None = None,
) -> Routing:
    """The routing this project's composed ``/task-init`` declares.

    ``config`` defaults to the project's own ``flow.yml`` when a root is given
    and to :data:`DEFAULT_DOC_CONFIG` otherwise, the same fallback
    ``doc_flow_config`` makes: a project that never scaffolded the flow still
    has its documents checked against the shipped route.
    """
    if config is None:
        config = doc_flow_config(project_root) if project_root is not None else DEFAULT_DOC_CONFIG
    try:
        composed = compose(*TASK_INIT_COMMAND, config=config, project_root=project_root)
    except FlowConfigError as error:
        # Reported by name by ``config-check``; raising here would turn one
        # configuration fault into a document check that names the wrong file.
        return Routing(notes=(f"task-init could not be composed: {error}",))
    return read_routing(composed.text)
