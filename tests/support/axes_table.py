"""The `## Axes` table the declared-axes cases are judged against."""

from __future__ import annotations

HEADER = "| Axis | Node | Sites | In scope | Why |\n|---|---|---|---|---|\n"


#: The rows of BDL-068's own ``## Axes`` table that the cases below have an
#: opinion about, excerpted from
#: ``.claude/development/docs/features/BDL-068/RFC.md``. Axis, node and decision
#: are the document's; the ``Why`` prose is abridged to fit a line, and the
#: guard below compares neither it nor the site count.
#:
#: **READ THIS BEFORE YOU APPEND S5's OR S6's ROWS.** The RFC's per-slice rule
#: obliges that table to GROW at the start of every slice, and appending to it
#: is expected and free: nothing here reads the live table for an enumeration,
#: so an append cannot make these cases red. What is NOT free is editing or
#: removing one of the six rows below —
#: :meth:`TestTheRowsTheseCasesDependOn.test_every_pinned_row_is_still_the_ruling_the_rfc_carries`
#: goes red on that, and it is the case that will tell you so. If a slice takes
#: `graph`, `doc-generator` or `agent-prime` back INTO scope, the excerpt and
#: the expected finding list here both move, and they move together.
#:
#: Six rows and not fifty: each one is here because a case below depends on the
#: ruling it carries. Three ``yes`` rows put a node inside by name and carry the
#: three bounded contexts the commit's other paths sit in; three ``no`` rows are
#: the rulings the commit is reported for. ``Sites`` and ``Why`` are carried for
#: readability and are deliberately NOT compared by the guard — a site line
#: number is re-derived every slice, so comparing it would rebuild the very
#: coupling this shape removes.
ROWS_THESE_CASES_DEPEND_ON = (
    "| callers | `ci-gate` | 1, `_step_doc_spaces` (`application/gate.py:590`) | yes "
    "| The `## Axes` checks report through the Gate step |\n"
    "| callers | `cli-commands` | 1, `axes` (`services/commands/impact.py:88`) | yes "
    "| The command surface |\n"
    "| co-writers | `agentic-flow-setup` | 1, `scaffold` "
    "(`onboarding/agentic_flow_setup.py:360`) | yes | written by this epic |\n"
    "| callers | `graph` | 2, first `lint` (`graph/linter.py:103`) | no "
    "| read by this change and not written by it |\n"
    "| co-writers | `doc-generator` | 2, first `_load_graph_from_yaml` "
    "(`onboarding/doc_generator.py:28`) | no | read by this change and not written by it |\n"
    "| co-writers | `agent-prime` | 4, first `bootstrap_project` "
    "(`onboarding/scanner/bootstrap.py:36`) | no "
    "| read by this change and not written by it |\n"
)
