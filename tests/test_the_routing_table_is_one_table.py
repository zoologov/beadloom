"""BDL-068 S6 / BDL-UX #259 — the routing table ends where the routing table ends.

The third reader of one boundary. ``doc-quality`` (BDL-UX #213) and
``axes-section`` (BDL-UX #244) were the same sentence found hours apart in one
slice, and ``beadloom-0mdo.46`` lifted the rule into
:mod:`beadloom.doc_sync.tables` so the two could not disagree again. It filed
this reader rather than fixing it: ``_routes_in`` matched the FIRST row whose
leading cells spelled the header and then read every table row anywhere below it
as a route.

**No instance fired, and that is the finding.** The reader survived on a
vocabulary guard — a row whose second cell names neither ``simplified`` nor
``full`` was discarded — and #213's measured cause was precisely that vocabulary
cannot decide this. Measured over this repository: 456 markdown documents, 5 122
table data rows, 27 admitted by the guard. Ten are the routing table itself, in
``.claude/commands/task-init.md`` and the shipped template; the other seventeen
sit in fifteen other documents and would be read as routes named ``D4``,
``BEAD-05``, ``Q1``, ``12.8.3`` and ``Local proxy``. A filter that rejects 99.5%
of a corpus is sparse, not sound.

**A phantom route DELETES, which is why the failure direction was not the benign
one the entry assumed.** :attr:`Routing.shared_kinds` is an INTERSECTION over
every route, and it is where BDL-UX #257's focus document comes from. Measured
before the fix on the shipped command with one extra table appended: 7 routes
read where 5 exist, and ``shared_kinds`` falls from ``{ACTIVE}`` to the empty
set — the document every bead of every work item writes stops being derivable.

**Which of these were verified red, and which are guards.** Nine assertions here
and in ``tests/acceptance/steps/test_work_item_routing_steps.py`` were run
against the pre-fix reader and failed: the three scenarios, and the six tests in
:class:`TestATableEndsWhereItsRowsStop` and
:class:`TestARowTheTableStatesAndTheReaderCannotUse` that name a table boundary
or an unread row. The rest are green in BOTH directions and are stated as
guards rather than as checks — the regression set over the shipped command, the
twenty composable shapes, this project's own routing, the separator rule, and
the union a project layer's own routing table contributes. That last one is a
guard over a real capability rather than a hypothetical: reading only the FIRST
matching table was tried here and dropped exactly that route.
"""

from __future__ import annotations

import pytest

from beadloom.application.work_item_routing import (
    TASK_INIT_COMMAND,
    read_routing,
    task_init_routing,
)
from beadloom.onboarding.composer import compose
from beadloom.onboarding.doc_templates import DEFAULT_DOC_CONFIG
from beadloom.onboarding.flow_config import (
    SUPPORTED_ARCHITECTURES,
    SUPPORTED_STACKS,
    FlowConfig,
)

#: The routes the shipped command states, in the order it states them.
_STATED = (
    ("epic", "full"),
    ("feature", "full"),
    ("bug", "simplified"),
    ("task", "simplified"),
    ("chore", "simplified"),
)

_ROUTING = """\
| Type | Flow | Docs created |
|------|------|--------------|
| `epic` | Full: PRD → RFC → CONTEXT+PLAN → ACTIVE | PRD, RFC, CONTEXT, PLAN, ACTIVE |
| `bug` | Simplified: BRIEF → ACTIVE | BRIEF, ACTIVE |
"""


def _shipped() -> str:
    return compose(*TASK_INIT_COMMAND, config=DEFAULT_DOC_CONFIG).text


def _types(text: str) -> tuple[tuple[str, str], ...]:
    return tuple((route.type, route.flow) for route in read_routing(text).routes)


def _unread_note(notes: tuple[str, ...]) -> str:
    """The note about rows the reader could not use, isolated from the others.

    A fragment carrying only a routing table launches no ``explore`` subagent, so
    the routing honestly carries that note too; indexing the tuple would make
    these assertions depend on which honest skip happens to come first.
    """
    found = [note for note in notes if "could not read as a route" in note]
    assert len(found) == 1, notes
    return found[0]


class TestNoRouteThatExistsTodayDisappears:
    """The change alters which rows contribute, so both directions are measured."""

    def test_the_shipped_command_reads_the_five_routes_it_states(self) -> None:
        assert _types(_shipped()) == _STATED

    @pytest.mark.parametrize("architecture", SUPPORTED_ARCHITECTURES)
    @pytest.mark.parametrize("stack", SUPPORTED_STACKS)
    @pytest.mark.parametrize("language", ["en", "ru"])
    def test_every_composable_shape_reads_the_same_routes(
        self, architecture: str, stack: str, language: str
    ) -> None:
        """The routing table lives in the core fragment, so no overlay moves it.

        Twenty of the twenty-one shapes this project can compose; the twenty-first
        is its own ``flow.yml``, covered by ``task_init_routing`` below.
        """
        config = FlowConfig(
            tools=("claude",),
            architecture=architecture,
            stack=(stack,),
            language=language,
        )
        composed = compose(*TASK_INIT_COMMAND, config=config)
        assert _types(composed.text) == _STATED

    def test_this_projects_own_routing_is_unchanged(self, tmp_path: object) -> None:
        routing = task_init_routing()
        assert tuple((r.type, r.flow) for r in routing.routes) == _STATED
        assert routing.shared_kinds == frozenset({"ACTIVE"})
        assert routing.full_kinds == frozenset({"PRD", "RFC", "CONTEXT", "PLAN"})
        assert routing.simplified_kinds == frozenset({"BRIEF"})
        assert routing.notes == ()


class TestATableEndsWhereItsRowsStop:
    """The boundary, read through the one component that owns it."""

    def test_a_later_table_contributes_no_row(self) -> None:
        text = (
            _ROUTING + "\nprose\n\n| Kind | Flow | Note |\n|---|---|---|\n"
            "| `spike` | Full: nothing | NOTES |\n"
        )

        assert _types(text) == (("epic", "full"), ("bug", "simplified"))

    def test_a_later_tables_header_row_is_not_a_route(self) -> None:
        text = _ROUTING + "\nprose\n\n| Type | Flow | Docs created |\n|---|---|---|\n"

        assert "type" not in {route.type for route in read_routing(text).routes}

    def test_a_separator_row_does_not_end_the_table(self) -> None:
        """The one rule that is not "a non-row ends it", asserted where it matters."""
        assert _types(_ROUTING) == (("epic", "full"), ("bug", "simplified"))

    def test_an_earlier_table_quoting_the_header_does_not_become_the_table(self) -> None:
        text = (
            "| Artifact | Read for | Notes |\n|---|---|---|\n"
            "| Type | Flow | Docs created |\n"
            "| `epic` | Full: PRD → RFC | the example row |\n"
            "\nprose\n\n" + _ROUTING
        )

        routing = read_routing(text)

        assert tuple((r.type, r.flow) for r in routing.routes) == (
            ("epic", "full"),
            ("bug", "simplified"),
        )
        assert routing.decision_line == 8
        assert routing.shared_kinds == frozenset({"ACTIVE"})

    def test_a_document_stating_no_routing_table_says_so(self) -> None:
        routing = read_routing("# a command\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")

        assert routing.routes == ()
        assert any("no routing table" in note for note in routing.notes)


class TestARowTheTableStatesAndTheReaderCannotUse:
    """Under-reporting a route was the failure direction the entry named."""

    def test_a_row_naming_neither_flow_is_reported(self) -> None:
        text = _ROUTING + "| `spike` | Timeboxed: NOTES | NOTES |\n"

        routing = read_routing(text)

        assert tuple(r.type for r in routing.routes) == ("epic", "bug")
        assert routing.flow_of("spike") is None
        assert "NOTES" not in routing.simplified_kinds
        note = _unread_note(routing.notes)
        assert "spike" in note
        assert "line 5" in note

    def test_a_row_too_narrow_to_state_documents_is_reported(self) -> None:
        text = _ROUTING + "| `spike` | Full |\n"

        routing = read_routing(text)

        assert tuple(r.type for r in routing.routes) == ("epic", "bug")
        assert "spike" in _unread_note(routing.notes)

    def test_the_note_counts_every_row_it_could_not_read(self) -> None:
        text = _ROUTING + "| `spike` | Timeboxed |\n| `chore` | Ad hoc | NOTES |\n"

        note = _unread_note(read_routing(text).notes)

        assert "2 row(s)" in note
        assert "spike" in note
        assert "chore" in note


class TestAProjectLayerStatesItsOwnRoutingTable:
    """The union, because ``/task-init`` composes a project layer under the core.

    Reading only the FIRST matching table was the shape this bead started with,
    and it dropped a route that exists today: `beadloom-0mdo.5` built this
    derivation so that a layer adding a type is policed by the same act, and
    `tests/test_the_explore_role_is_composed_like_the_others.py` states that
    capability against a real scaffolded project. A route lost here removes every
    work item of that type from the population `check_work_item_types` judges,
    which is the direction BDL-UX #259 warned is worse than a phantom.
    """

    _LAYER = (
        "\n## Local routes\n\n"
        "| Type | Flow | Docs created |\n|---|---|---|\n"
        "| `spike` | Simplified: NOTE → ACTIVE | NOTE, ACTIVE |\n"
    )

    def test_a_second_routing_table_contributes_its_rows(self) -> None:
        assert _types(_ROUTING + self._LAYER) == (
            ("epic", "full"),
            ("bug", "simplified"),
            ("spike", "simplified"),
        )

    def test_the_second_tables_header_row_is_not_read_as_a_route(self) -> None:
        """BDL-UX #244's shape, one reader over: a header came back as data."""
        types = {route.type for route in read_routing(_ROUTING + self._LAYER).routes}

        assert "type" not in types

    def test_the_decision_is_located_at_the_first_routing_table(self) -> None:
        routing = read_routing(_ROUTING + self._LAYER)

        assert routing.decision_line == 1

    def test_a_second_routing_tables_rows_are_judged_against_its_own_header(self) -> None:
        """A layer stating a narrower table loses its rows to the note, not to silence."""
        text = _ROUTING + "\n| Type | Flow |\n|---|---|\n| `spike` | Simplified |\n"

        routing = read_routing(text)

        assert tuple(r.type for r in routing.routes) == ("epic", "bug")
        assert "spike" in _unread_note(routing.notes)
