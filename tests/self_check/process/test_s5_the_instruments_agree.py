"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/integration/services/bd_seam/test_s5_the_instruments_agree.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from beadloom.services.bd_seam import population as bd_population
from beadloom.services.bd_seam.assumptions import (
    ASSUMPTION_ALLOCATED_ID,
    ASSUMPTION_ECHOED_TITLES,
    ASSUMPTION_INTENDED_ID,
    ASSUMPTION_UNMEASURED_SUBCOMMAND,
    BD_MEASURED_VERSION,
    VERDICT_UNMEASURED,
)
from beadloom.services.bd_seam.invocations import (
    CHANNEL_PYTHON,
    SEAM_FUNCTION,
)

if TYPE_CHECKING:
    from pathlib import Path


def _instructing_texts(root: Path) -> tuple[tuple[str, str], ...]:
    """Every artifact the derived population reads under *root*, as ``(label, text)``.

    Taken from the population's own collectors rather than from a list of paths, so an
    artifact added to the flow is swept here by being added there.
    """
    return (
        *bd_population.flow_artifacts(root),
        *bd_population.shipped_templates(),
        *bd_population.package_python(),
    )


def _seam_calls_in_the_package() -> list[tuple[str, int]]:
    """Every ``run_bd(...)`` call in the installed package, as ``(label, line)``.

    Read from the package root the population itself resolves, and by the same AST the
    reader uses, so this counts CALLS where the reader counts calls-it-could-read. The
    difference between the two is the whole subject of the test below.
    """
    found: list[tuple[str, int]] = []
    for label, text in bd_population.package_python():
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name == SEAM_FUNCTION:
                found.append((label, node.lineno))
    return found


def test_the_ready_cap_measurement_is_stated_with_one_rig_size_across_the_tree(
    self_check_snapshot: Path
) -> None:
    """Two beads measured one cap on two rigs and the tree kept both numbers.

    RED WHEN WRITTEN. ``beadloom-0mdo.51`` measured ``bd ready`` returning 100 of 135;
    ``beadloom-0mdo.52`` re-measured it as 100 of 120 on a rig built with ``bd create
    --graph`` and updated the module docstring, ``answers.py``, the shared ``_tracker``
    role fragment, five composed role files, five vendored template snapshots and two
    tests. The one statement it did not own kept 135: the ``untruncated-population``
    detail, which is the sentence ``beadloom bd-calls`` prints at every unsecured ``bd
    ready`` site. An agent reading its role core is told one number and the report it is
    pointed at prints another, about one measurement.

    Re-measured for this test on bd 1.0.4 in an isolated 120-bead rig: 100 rows returned,
    ``Showing 100 of 120 ready issues.`` on stderr, stdout silent about it, and 120 rows
    under ``--limit 0``. The rig size is a property of the rig, so neither number is
    false — what cannot be true is both, in one tree, about one sentence.
    """
    # Arrange
    cap_sentence = re.compile(r"100 of (\d+)")

    # Act
    stated: dict[str, set[str]] = {}
    for label, text in _instructing_texts(self_check_snapshot):
        for size in cap_sentence.findall(text):
            stated.setdefault(size, set()).add(label)

    # Assert
    assert stated, "no artifact states the `bd ready` cap measurement at all"
    assert len(stated) == 1, "one measurement is stated with more than one rig size: " + "; ".join(
        f"100 of {size} in {sorted(labels)[0]}"
        + (f" and {len(labels) - 1} more" if len(labels) > 1 else "")
        for size, labels in sorted(stated.items())
    )


def test_every_sentence_pinning_a_measurement_to_a_bd_release_names_the_measured_one(
    self_check_snapshot: Path
) -> None:
    """The release is pinned in one constant and RESTATED in prose the constant cannot reach.

    ``BD_MEASURED_VERSION`` is compared against the installed bd, so a bd upgrade reddens
    one test. It cannot see the sentences that say "measured on bd 1.0.4" in the seam's
    module docstrings, in the wave plan's landing module and in the shared role fragments
    five composed roles carry to an adopter. Bumping the constant without moving those
    turns thirty measured statements into claims about a release nobody took them on.

    Limited by construction to the ``bd <version>`` shape, which is how every one of them
    is written today; a sentence pinning a release some other way is outside this guard
    and is named here rather than implied.
    """
    # Arrange
    pinned = re.compile(r"\bbd (\d+\.\d+\.\d+)")

    # Act
    stated: dict[str, list[str]] = {}
    for label, text in _instructing_texts(self_check_snapshot):
        for version in pinned.findall(text):
            stated.setdefault(version, []).append(label)

    # Assert
    assert stated, "no artifact pins a measurement to a bd release at all"
    assert set(stated) == {BD_MEASURED_VERSION}, (
        f"the table is measured on bd {BD_MEASURED_VERSION} and prose in this tree "
        f"pins a measurement to another release: "
        + "; ".join(
            f"bd {version} in {sorted(set(labels))[0]}"
            for version, labels in sorted(stated.items())
            if version != BD_MEASURED_VERSION
        )
    )


def test_every_call_to_the_seam_in_this_package_is_visible_to_the_derivation(
    self_check_snapshot: Path
) -> None:
    """A call site the reader cannot follow leaves NO trace, which reads as clean.

    ``beadloom-0mdo.53`` built this exact defect by tidying: its first version put the
    scaffold's argv behind a ``graph_argv()`` helper, and because the reader resolves a
    list literal handed to ``run_bd`` and cannot follow a function call, the creation
    site vanished from the report rather than appearing in it unsecured. The guard that
    bead left behind names ONE call site by module, function and test, which is the
    hand-written list this slice's own description forbids and which covers nothing about
    the twelve other call sites or the thirteenth somebody adds.

    This is the derived form: the calls this package makes, counted against the calls the
    population reports. It is one-sided on purpose — a site the reader DID read but the
    population dropped for another reason would show here too, and that is also a defect.
    """
    # Arrange
    calls = _seam_calls_in_the_package()
    assert calls, "no `run_bd` call was found at all, so this test proves nothing"

    # Act
    seen = {
        (site.source, site.line)
        for site in bd_population.project_report(self_check_snapshot).sites
        if site.channel == CHANNEL_PYTHON
    }

    # Assert
    invisible = [f"{label}:{line}" for label, line in calls if (label, line) not in seen]
    assert invisible == [], (
        "a `run_bd` call is absent from the derived population rather than unsecured in "
        "it, so the report reads clean about a site nothing judged. Spell the argv as a "
        "list literal at the call: " + "; ".join(invisible)
    )


def test_the_two_command_families_the_coordinator_runs_are_still_unjudged(
    self_check_snapshot: Path
) -> None:
    """``bd swarm`` and ``bd gate`` are unmeasured, and nothing has quietly claimed them.

    They are the two commands ``/coordinator`` orchestrates every wave with and the two
    ``beadloom-0mdo.51`` deliberately did not guess at, because measuring two command
    families properly is its own bead and guessing is the false confidence this epic
    removes. Three beads landed on the table afterwards and each could have converted one
    into a claim by adding a key with an empty tuple — which is how the table records "a
    subcommand measured to carry no assumption", one keystroke from "a subcommand nobody
    looked at".

    Measured today: 26 ``swarm`` sites and 22 ``gate`` sites, every one in the
    instruction channel, every one carrying ``unmeasured-subcommand`` and nothing else.
    """
    # Arrange
    report = bd_population.project_report(self_check_snapshot)

    # Act
    orchestration = [site for site in report.sites if site.subcommand in ("swarm", "gate")]

    # Assert
    assert {site.subcommand for site in orchestration} == {"swarm", "gate"}, (
        "this project no longer instructs both command families, so the gap this test "
        "keeps open may have been closed by deletion rather than by measurement"
    )
    claimed = [
        f"{site.source}:{site.line} `{site.text}` -> "
        + ",".join(f"{a.name}={a.verdict}" for a in site.assumptions)
        for site in orchestration
        if [a.name for a in site.assumptions] != [ASSUMPTION_UNMEASURED_SUBCOMMAND]
        or [a.verdict for a in site.assumptions] != [VERDICT_UNMEASURED]
    ]
    assert claimed == [], (
        "an unmeasured subcommand now carries a verdict, so a site nobody measured reads "
        "as judged: " + "; ".join(claimed)
    )


def test_no_instruction_of_ours_leaves_a_creation_or_wiring_assumption_unsettled(
    self_check_snapshot: Path
) -> None:
    """The zero ``beadloom-0mdo.53`` asserted covers the channel that cannot hold a site.

    ``.53`` removed both of this project's Python ``create``/``dep add`` call sites — the
    scaffold makes ONE ``bd create --graph`` call now — and then asserted zero unsettled
    sites over the PYTHON channel. Every remaining place this project can get bead
    creation or wiring wrong is therefore an INSTRUCTION site, and no test covered them:
    measured by injecting ``bd create --parent proj-1 "some child"`` into
    ``.claude/commands/task-init.md``, where ``beadloom bd-calls`` judged it
    ``allocated-id=unsecured`` and the 132 tests of the four S5 suites passed.

    This is that gate. It reddens on an artifact of ours telling an agent to create a
    bead without asking bd for the id it allocated, or to wire an edge nothing verifies.
    """
    # Arrange
    report = bd_population.project_report(self_check_snapshot)
    owned = {ASSUMPTION_ALLOCATED_ID, ASSUMPTION_INTENDED_ID, ASSUMPTION_ECHOED_TITLES}

    # Act
    unsettled = [
        f"{site.source}:{site.line} `{site.text}` -> "
        + ",".join(f"{a.name}={a.verdict}" for a in site.unsettled if a.name in owned)
        for site in report.sites
        if any(a.name in owned for a in site.unsettled)
    ]

    # Assert
    assert unsettled == [], (
        "an artifact of ours instructs a bead creation or a wiring whose assumption "
        "nothing settles: " + "; ".join(unsettled)
    )
    judged = [site for site in report.sites if any(a.name in owned for a in site.assumptions)]
    assert judged, "no create or dep-add site was judged at all, so the zero above is vacuous"
