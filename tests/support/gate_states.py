"""The Gate run over one project per summary-fact state, and how its lines are read."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_project import IndexedProjectSpec, indexed_python_project

if TYPE_CHECKING:
    from pathlib import Path

#: ``rules.yml`` declaring `.1`'s rule alone, so the four Gate outputs differ in
#: the state of ONE rule and in nothing else.
SUMMARY_FACTS_ONLY = (
    "version: 3\n"
    "rules:\n"
    "  - name: graph-summary-facts\n"
    "    description: a number in a node summary matches what the project computes\n"
    "    summary_facts: {}\n"
)


#: The four states, as ``(id, kwargs)``. Each differs from ``agrees`` in one
#: field, so a difference in the Gate's output has one possible cause.
STATES: dict[str, IndexedProjectSpec] = {
    "agrees": {"summaries": {"billing-m0": "The billing module of release v3.7.0"}},
    "disagrees": {"summaries": {"billing-m0": "The billing module of release v9.9.9"}},
    "unverifiable": {
        "version": None,
        "summaries": {"billing-m0": "The billing module of release v3.7.0"},
    },
    "no-claim": {},
}


def gate_over_state(tmp_path: Path, state: str) -> tuple[str, dict[str, object]]:
    """``beadloom ci`` over one state: the text a reader sees, and the payload.

    The two are taken from separate invocations because they are separate
    formats, and both are asserted: the annotation stream is what a person
    reads in CI, the JSON is what a machine consumer reads, and a distinction
    that survives in one and not the other has still been lost.
    """
    spec: IndexedProjectSpec = {"rules": SUMMARY_FACTS_ONLY}
    spec.update(STATES[state])
    project = indexed_python_project(tmp_path / state, **spec)
    runner = CliRunner()
    human = runner.invoke(main, ["ci", "--project", str(project.root)])
    machine = runner.invoke(main, ["ci", "--project", str(project.root), "--format", "json"])
    payload = json.loads(machine.stdout)
    assert isinstance(payload, dict)
    return human.stdout, payload


def names_after(line: str, marker: str) -> set[str]:
    """The comma-separated fact names a Gate-line clause lists.

    The clauses are appended in a fixed order, so a clause ends at the next
    clause's marker or at the parenthetical that closes the line.
    """
    if marker not in line:
        return set()
    tail = line.split(marker, 1)[1]
    for stop in (", NOT VERIFIED:", ", NOT APPLICABLE to this project:", " ("):
        tail = tail.split(stop, 1)[0]
    return {name.strip() for name in tail.split(",") if name.strip()}
