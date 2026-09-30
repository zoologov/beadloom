"""Which of the portal's browser tests run on an adopter fixture, and why the others do not.

BDL-076 B3 (``beadloom-hmqn``). The Playwright suite ships in the scaffold, so it
runs on any built portal. Most cases compute what they expect from the data file
the portal serves, or serve a data file of their own; those run on every fixture.

A case whose precondition is a shape of the graph that a single adopter project
does not have is left out here, by name, with that shape as its reason. Leaving a
case out is a statement about the fixture, never about the viewer: each still runs
on this repository's portal in the ``site-e2e`` job. A test in
``tests/self_check/process/`` fails when a name below no longer matches a spec,
so the list cannot outlive what it names.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: The specs as they ship, in the scaffold.
SHIPPED_SPECS = REPO_ROOT / "src" / "beadloom" / "site_scaffold" / "e2e"

#: A single project's landscape is empty: services and contracts come from a
#: federation or from declared AMQP and GraphQL surfaces, and a fixture has neither.
_EMPTY_LANDSCAPE = "a single project's landscape has no service and no contract"

#: Spec files none of whose cases a fixture can hold.
FILES_NOT_RUN: Mapping[str, str] = {
    "landscape-impact.spec.js": (
        f"every case grows the served landscape from its first contract; {_EMPTY_LANDSCAPE}"
    ),
    "diagram-links.spec.js": (
        f"both cases read the links of the landscape diagram's nodes; {_EMPTY_LANDSCAPE}"
    ),
}

#: Single cases, by their title as the spec writes it.
TITLES_NOT_RUN: Mapping[str, str] = {
    "a domain filter keeps the domain's whole subtree": (
        "needs a domain whose subtree is two levels deep; `beadloom init` writes a domain "
        "and its parts, one level"
    ),
    "a selected service shows its neighbourhood and a card with every contract it takes part in": (
        f"selects the service with the most contracts; {_EMPTY_LANDSCAPE}"
    ),
    "the landscape resolves every colour it draws, and no style is rejected": (
        f"needs at least one drawn colour; {_EMPTY_LANDSCAPE}"
    ),
    "full screen holds the landscape's toolbar, canvas and card": (
        f"opens a service's card; {_EMPTY_LANDSCAPE}"
    ),
}

#: How ``beadloom init`` writes the Go fixture's graph (``microservices`` preset): each
#: package a service or a feature directly under the root service, every one tagged
#: with its own layer. So no node inherits a layer, nothing nests two levels deep, and
#: there is no domain and no page under ``other/``.
_FLAT_GO = "the Go graph is one level under its root service, with no domain"

#: Further cases left out on one stack only, by the shape its graph lacks.
TITLES_NOT_RUN_BY_STACK: Mapping[str, Mapping[str, str]] = {
    "go": {
        "the card names the node's layer and says it is inherited through part_of": (
            f"needs a node that inherits its layer through part_of; {_FLAT_GO}"
        ),
        "the card names the declared layer of a node whose layer is inherited": (
            f"needs a node that inherits its layer through part_of; {_FLAT_GO}"
        ),
        "a layer filter keeps every node in that layer, inherited or its own, "
        "with its containers": (
            f"needs a node that inherits its layer through part_of; {_FLAT_GO}"
        ),
        "the search box keeps the matching nodes and their containers": (
            f"needs a node two levels below the top; {_FLAT_GO}"
        ),
        "a drag inside a domain box pans the view and moves no node": (
            f"needs a container box inside another; {_FLAT_GO}"
        ),
        "a linked view opens in the state its query names": (
            f"needs a feature inside a domain; {_FLAT_GO}"
        ),
        "a change in the toolbar is written to the URL and survives a reload": (
            f"focuses a domain; {_FLAT_GO}"
        ),
        "a page under other/ opens focused on its node the same way": (
            f"needs a node whose page is under other/; {_FLAT_GO}"
        ),
        "clearing the selection shows the whole graph again": (
            "needs a node outside the subject's two-step neighbourhood; each of the Go graph's "
            "six nodes is within two steps of the entry point"
        ),
    },
}

#: Cases a known defect holds back on one stack, by title, with the bead that holds
#: it. They are left out of the stack's run and run on their own as a strict xfail,
#: so they are reported the day the defect is fixed.
TITLES_HELD_BY_DEFECT: Mapping[str, Mapping[str, str]] = {
    "go": {
        "a node with warn findings only is drawn as a warning, not as a violation": (
            "beadloom-ujzb.14: the fixture's warn rule is a deny rule, deny rules judge "
            "resolved imports, and no Go import resolves, so no node is warned"
        ),
        "an error finding draws a violation, in a look apart from a warning's": (
            "beadloom-ujzb.14: compares a violation with a warned node, and no Go node is warned"
        ),
    },
}

#: The characters a JavaScript regular expression reads as syntax.
_REGEX_SYNTAX = frozenset("\\^$.|?*+()[]{}/")


def _literal(text: str) -> str:
    """*text* as a JavaScript regular expression that matches it literally."""
    return "".join(f"\\{char}" if char in _REGEX_SYNTAX else char for char in text)


def titles_not_run(stack: str) -> dict[str, str]:
    """Every case left out of *stack*'s run, by title, with its reason."""
    return {
        **TITLES_NOT_RUN,
        **TITLES_NOT_RUN_BY_STACK.get(stack, {}),
        **TITLES_HELD_BY_DEFECT.get(stack, {}),
    }


def _any_of(titles: list[str]) -> str:
    return "|".join(_literal(title) for title in sorted(titles))


def playwright_selection(e2e: Path, stack: str) -> list[str]:
    """The ``playwright test`` arguments that run every case of *e2e* not left out on *stack*."""
    files = sorted(
        f"e2e/{path.name}" for path in e2e.glob("*.spec.js") if path.name not in FILES_NOT_RUN
    )
    return [*files, "--grep-invert", _any_of(list(titles_not_run(stack)))]


def playwright_defect_selection(stack: str) -> list[str]:
    """The ``playwright test`` arguments that run only the cases a defect holds back on *stack*."""
    return ["--grep", _any_of(list(TITLES_HELD_BY_DEFECT[stack]))]
