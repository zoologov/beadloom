# beadloom:domain=graph
# beadloom:feature=rule-engine
"""The findings that report a rule's REACH, and the exit code they do not move.

Two of this package's findings are not about the graph being wrong. The
population statement (:mod:`.layer_reach`) says how much of its edge set a layer
rule judged, and the declaration statement (:mod:`.layer_declaration`) says
whether the rule's own declaration describes this project. Both are ``warn``,
neither decides anything about an edge, and both were added by BDL-070 Release A
to graphs nobody had changed.

**That is why they are excluded from what ``lint --fail-on-warn`` exits 1 on.**
The flag means "any finding, including the ones that are only warnings", and
before Release A every finding it could see was a rule's decision. The A8 review
measured the consequence: a fixture with two tagged edges and one untagged, clean
under every rule it declares, exits 0 on the code before Release A and 1 after
it. The epic's CONTEXT says no adopter's Gate may change verdict on upgrade, and
a pipeline turning red for a message whose whole purpose is to tell the reader
something they did not know is the worst version of that: the finding is not
actionable in the run that reddened, because tagging the ends is a change to the
graph, not to the commit under test.

The exclusion is BY RULE TYPE and not by severity. Every other ``warn`` — an
expired exemption, an inert rule, a scenario a node has no binding for — is a
statement about something a person chose, and ``--fail-on-warn`` goes on exiting
1 on it. :class:`~beadloom.graph.linter.LintResult.fails_on_warn` is where the
distinction is applied, so the CLI reads one property instead of re-deriving it.

**When this exclusion should be revisited.** Release B of BDL-070 makes the real
under-evaluation an ERROR from the rule itself, which is a verdict change the
release states and an adopter reads in its notes. The advisory exists to be
legible before that, not to be a permanent silence.

The neutrality differential in ``tests/the_lint_path_before_release_a.py`` keeps
a list of the same two types of its own. That duplication is deliberate: it is
an oracle, and an oracle that imports the value it checks cannot catch the value
being wrong.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.layer_declaration import LAYER_DECLARATION_RULE_TYPE
from beadloom.graph.rules.layer_reach import LAYER_POPULATION_RULE_TYPE

if TYPE_CHECKING:
    from beadloom.graph.rules.types import Violation

#: The rule types whose findings report reach rather than a defect. Adding a
#: type here removes it from what ``--fail-on-warn`` exits on, so an entry needs
#: the same justification the two above carry: the finding must decide nothing
#: about the graph, and must be capable of appearing on a project that changed
#: nothing.
ADVISORY_RULE_TYPES = frozenset({LAYER_POPULATION_RULE_TYPE, LAYER_DECLARATION_RULE_TYPE})


def is_advisory(violation: Violation) -> bool:
    """Whether *violation* states a rule's reach instead of deciding anything."""
    return violation.rule_type in ADVISORY_RULE_TYPES
