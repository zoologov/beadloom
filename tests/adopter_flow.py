"""A flow arrangement that is not this repository's, as a substitutable input.

BDL-068 S6's subject is the flow's own documents and roles, so its characteristic
risk is a check that passes because THIS repository happens to be arranged the
right way. BDL-UX #240 is the measured precedent: a defect in the typed leg's path
filter was invisible here because Beadloom is src-layout, and it survived the bead
that built the surface.

``tests/adopter_project.py`` already varies the PROJECT — its stack, its manifest,
its version. This module varies the FLOW: which tools a project composes adapters
for, where its planning documents live, which column of its bead table carries the
bead id, how it spells a table's alignment row, whether its graph is one file or
one per node, and whether it declares an issue log at all. Every value below is a
choice the shipped flow permits, so a check that only holds for one of them is a
check about this repository.

:data:`OURS` is what this repository does, named so a test can say which
arrangement a measurement was taken under. It is one row of the matrix and not
its centre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

#: The alignment row cell every document in this repository writes. GFM requires
#: one hyphen and this project writes six, so a reader that demands two is right
#: about every table here and wrong about a valid one.
LONG_ALIGNMENT = "------"

#: The shortest alignment cell GitHub Flavored Markdown accepts.
SHORT_ALIGNMENT = "-"

ONE_FILE = "one-file"
ONE_PER_NODE = "one-per-node"


@dataclass(frozen=True)
class FlowArrangement:
    """How a project spells the flow artifacts every S6 check reads.

    Each field is a decision an adopter makes and the shipped flow permits. A
    check whose verdict changes with one of them is reporting on the arrangement
    rather than on the project.
    """

    label: str
    #: The tools ``flow.yml`` declares. A project composing only Cursor adapters
    #: never writes a ``CLAUDE.md``.
    tools: tuple[str, ...] = ("claude",)
    #: Which column of the bead-status table carries the bead id, counting from
    #: zero. This repository writes it first; nothing requires that.
    bead_column: int = 0
    #: The body of each alignment-row cell.
    alignment: str = LONG_ALIGNMENT
    #: The glob ``.beadloom/config.yml`` declares for planning documents, or
    #: ``None`` to leave the shipped default in place.
    planning_glob: str | None = None
    #: ``ONE_FILE`` or ``ONE_PER_NODE``.
    graph_layout: str = ONE_PER_NODE
    #: Whether the project declares an ``issue_log:`` block.
    issue_log: bool = True

    @property
    def planning_dir(self) -> str:
        """The directory the arrangement's planning documents live in."""
        if self.planning_glob is None:
            return ".claude/development/docs/features"
        return self.planning_glob.split("*")[0].rstrip("/")


#: This repository's own arrangement, so a measurement can name it.
OURS = FlowArrangement(label="ours")

#: One variant per axis, each valid and none of them ours.
CURSOR_ONLY = FlowArrangement(label="cursor-only", tools=("cursor",))
BEAD_IN_THE_SECOND_COLUMN = FlowArrangement(label="bead-in-column-2", bead_column=1)
SHORT_ALIGNMENT_ROWS = FlowArrangement(label="short-alignment", alignment=SHORT_ALIGNMENT)
DOCS_ELSEWHERE = FlowArrangement(label="docs-elsewhere", planning_glob="docs/planning/*/*.md")
SINGLE_FILE_GRAPH = FlowArrangement(label="single-file-graph", graph_layout=ONE_FILE)
NO_ISSUE_LOG = FlowArrangement(label="no-issue-log", issue_log=False)

ARRANGEMENTS: tuple[FlowArrangement, ...] = (
    OURS,
    CURSOR_ONLY,
    BEAD_IN_THE_SECOND_COLUMN,
    SHORT_ALIGNMENT_ROWS,
    DOCS_ELSEWHERE,
    SINGLE_FILE_GRAPH,
    NO_ISSUE_LOG,
)


@dataclass(frozen=True)
class AdopterFlow:
    """A built project, with the paths a test asserts against."""

    root: Path
    arrangement: FlowArrangement
    work_item: str
    active: Path
    graph_dir: Path
    log: Path | None = None
    ledger: Path | None = None
    beads: tuple[str, ...] = field(default_factory=tuple)


def status_table(arrangement: FlowArrangement, beads: Sequence[str]) -> str:
    """A bead-status table written the way *arrangement* writes one."""
    headers = ["Bead", "Role", "Status"]
    if arrangement.bead_column == 1:
        headers = ["Wave", "Bead", "Status"]
    rows = ["| " + " | ".join(headers) + " |"]
    rows.append("|" + "|".join(f" {arrangement.alignment} " for _ in headers) + "|")
    for index, bead in enumerate(beads, start=1):
        cells = ["dev", "done"] if arrangement.bead_column == 0 else [str(index), "done"]
        cells.insert(arrangement.bead_column, bead)
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows) + "\n"


def active_document(
    arrangement: FlowArrangement,
    work_item: str,
    beads: Sequence[str],
    *,
    deferred: Sequence[str] = (),
) -> str:
    """The focus document of *work_item*, with its status table and any second one.

    *deferred* renders a second table — the shape this repository's own ACTIVE.md
    carries and ``active-table`` documents: beads named in a table that is not the
    status table. It is separate because the two tables answer different
    questions, and a reader that takes the first cell of every row cannot tell
    them apart.
    """
    parts = [f"# ACTIVE: {work_item}\n", "## Beads\n", status_table(arrangement, beads)]
    if deferred:
        parts.append("\n## Deferred\n")
        parts.append("| Bead | Why it was not done here |")
        parts.append(f"| {arrangement.alignment} | {arrangement.alignment} |")
        parts.extend(f"| {bead} | out of this slice |" for bead in deferred)
        parts.append("")
    return "\n".join(parts)


def _beadloom_config(arrangement: FlowArrangement) -> dict[str, object]:
    config: dict[str, object] = {"languages": [".py"], "scan_paths": ["src"]}
    if arrangement.planning_glob is not None:
        config["doc_quality"] = {"paths": [arrangement.planning_glob]}
    if arrangement.issue_log:
        config["issue_log"] = {"path": "ISSUES.md", "ledger": "issues"}
    return config


def _write_graph(graph_dir: Path, arrangement: FlowArrangement, nodes: Sequence[str]) -> None:
    graph_dir.mkdir(parents=True, exist_ok=True)
    if arrangement.graph_layout == ONE_FILE:
        payload = {"nodes": [{"ref_id": ref, "kind": "component"} for ref in nodes]}
        (graph_dir / "graph.yml").write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )
        return
    for ref in nodes:
        payload = {"nodes": [{"ref_id": ref, "kind": "component"}]}
        (graph_dir / f"{ref}.yml").write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )


def build_flow(
    root: Path,
    arrangement: FlowArrangement,
    *,
    work_item: str = "ADOPT-1",
    beads: Sequence[str] = ("adopter-aaaa.1", "adopter-aaaa.2"),
    deferred: Sequence[str] = (),
    nodes: Sequence[str] = ("orders", "billing"),
    log_entries: int = 0,
) -> AdopterFlow:
    """Write a project arranged as *arrangement* says, and return its paths.

    The project is not Beadloom: it declares its own name and version, so a check
    that renders one of ours into its artifacts fails with the string that gave it
    away rather than passing by coincidence (``tests/adopter_project.py``).
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "orders-service"\nversion = "0.4.1"\n', encoding="utf-8"
    )
    beadloom_dir = root / ".beadloom"
    beadloom_dir.mkdir(exist_ok=True)
    (beadloom_dir / "flow.yml").write_text(
        yaml.safe_dump(
            {
                "tools": list(arrangement.tools),
                "architecture": ["ddd"],
                "stack": ["python"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (beadloom_dir / "config.yml").write_text(
        yaml.safe_dump(_beadloom_config(arrangement), sort_keys=False), encoding="utf-8"
    )
    graph_dir = beadloom_dir / "_graph"
    _write_graph(graph_dir, arrangement, nodes)

    folder = root / arrangement.planning_dir / work_item
    folder.mkdir(parents=True, exist_ok=True)
    active = folder / "ACTIVE.md"
    active.write_text(
        active_document(arrangement, work_item, beads, deferred=deferred),
        encoding="utf-8",
    )

    log: Path | None = None
    ledger: Path | None = None
    if arrangement.issue_log:
        log = root / "ISSUES.md"
        body = "# Issues\n\n" + "".join(f"{n}. entry {n}\n" for n in range(1, log_entries + 1))
        log.write_text(body, encoding="utf-8")
        ledger = root / "issues"
    return AdopterFlow(
        root=root,
        arrangement=arrangement,
        work_item=work_item,
        active=active,
        graph_dir=graph_dir,
        log=log,
        ledger=ledger,
        beads=tuple(beads),
    )
