"""Non-Beadloom project fixtures — the population none of our own checks can see.

Every check, review and dogfood run in this epic has measured Beadloom
measuring **Beadloom**. That makes a whole class of defect invisible: a fact the
tool computes about *itself* and renders into an *adopter's* file reads correct
here and is false everywhere else. BDL-UX #183 is the instance — the composed
``CLAUDE.md`` stated Beadloom's own ``__version__`` as the adopter's project
version, and it survived four slices because on this repository the two strings
are the same by coincidence.

This module builds projects that are **not** Beadloom (a TypeScript one, a Rust
one, a Python one with its own name and version, and one with no manifest at
all) so a renderer can be pointed at something it cannot be accidentally right
about. It is the project axis of the standing rule ONE PLATFORM IS NOT VERIFIED:
a claim measured on one project is true there and *unknown* everywhere else.

:func:`beadloom_local_facts_in` is the general half — a deny-list of this
repository's own identifiers that must never appear in an artifact composed for
somebody else. It names the offenders it finds, so the next instance of the
class fails with the string that gave it away rather than with ``assert False``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.doctor import get_actual_version

if TYPE_CHECKING:
    from pathlib import Path

#: Beadloom's own DDD packages, as the project-info renderer would spell them.
#: Their appearance in an adopter's file means our tree was scanned for theirs.
BEADLOOM_PACKAGES: tuple[str, ...] = (
    "ai_agents",
    "context_oracle",
    "doc_sync",
    "onboarding",
)


@dataclass(frozen=True)
class AdopterProject:
    """One project that is not Beadloom.

    ``version`` is what the project *declares* about itself; ``None`` means the
    project declares no version anywhere, which is the case that must render
    nothing rather than something false.
    """

    root: Path
    name: str
    version: str | None
    stack: str


def typescript_project(root: Path, *, version: str = "0.4.1") -> AdopterProject:
    """A Node/TypeScript service — the shape BDL-UX #183 was reported against."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "orders-web",
                "version": version,
                "devDependencies": {"vitest": "^1.0.0", "eslint": "^8.0.0"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    src = root / "src"
    src.mkdir(exist_ok=True)
    (src / "index.ts").write_text("export const orders = [];\n", encoding="utf-8")
    return AdopterProject(root=root, name="orders-web", version=version, stack="typescript")


def rust_project(root: Path, *, version: str = "1.2.3") -> AdopterProject:
    """A Cargo workspace — a stack the renderer has never been pointed at."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "Cargo.toml").write_text(
        f'[package]\nname = "ledger-core"\nversion = "{version}"\nedition = "2021"\n',
        encoding="utf-8",
    )
    src = root / "src"
    src.mkdir(exist_ok=True)
    (src / "main.rs").write_text("fn main() {}\n", encoding="utf-8")
    return AdopterProject(root=root, name="ledger-core", version=version, stack="rust")


def python_project(root: Path, *, version: str = "3.7.0") -> AdopterProject:
    """A Python project that is **not** Beadloom.

    Deliberately declares a version that cannot be confused with ours and a
    toolchain that only partly overlaps, so "the renderer read the project" is
    distinguishable from "the renderer read itself".
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "invoice-svc"\nversion = "{version}"\n'
        'dependencies = ["fastapi", "sqlalchemy"]\n\n'
        '[dependency-groups]\ndev = ["pytest"]\n',
        encoding="utf-8",
    )
    pkg = root / "src" / "invoice_svc"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for sub in ("billing", "ledger"):
        child = pkg / sub
        child.mkdir(exist_ok=True)
        (child / "__init__.py").write_text("", encoding="utf-8")
    return AdopterProject(root=root, name="invoice-svc", version=version, stack="python")


def poetry_project(root: Path, *, version: str = "0.9.2") -> AdopterProject:
    """A Python project declaring its version under ``[tool.poetry]``."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        f'[tool.poetry]\nname = "warehouse"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    return AdopterProject(root=root, name="warehouse", version=version, stack="python")


def hatch_dynamic_project(root: Path, *, version: str = "5.1.0") -> AdopterProject:
    """A Python project whose version is ``dynamic`` — the common modern layout.

    ``[project] dynamic = ["version"]`` with ``[tool.hatch.version] path = ...``
    declares the version just as firmly as a literal does; it simply keeps it in
    the package. Beadloom's own ``pyproject.toml`` is this shape, so treating it
    as "undeclared" would have made the tool unable to read its own version —
    honest, and needlessly blind for a large share of Python adopters.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "pipeline"\ndynamic = ["version"]\n\n'
        '[tool.hatch.version]\npath = "src/pipeline/__init__.py"\n',
        encoding="utf-8",
    )
    pkg = root / "src" / "pipeline"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
    return AdopterProject(root=root, name="pipeline", version=version, stack="python")


def undeclared_version_project(root: Path) -> AdopterProject:
    """A project that declares no version anywhere — *unknown is not zero*."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "go.mod").write_text("module example.com/gateway\n\ngo 1.22\n", encoding="utf-8")
    (root / "main.go").write_text("package main\n\nfunc main() {}\n", encoding="utf-8")
    return AdopterProject(root=root, name="gateway", version=None, stack="go")


#: Patterns that identify text as a fact about **this** repository. Each is
#: paired with the reason it must not reach somebody else's artifact.
_LOCAL_FACT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bBDL-\d{3}\b", "our epic key"),
    (r"BDL-UX[- ]Issues", "our issue log's filename"),
    (r"\bBDL-UX #\d+", "our issue number"),
    (r"beadloom-[a-z0-9]{4}\.\d+", "our bead id"),
    (r"src/beadloom\b", "our own source layout"),
)


def beadloom_local_facts_in(text: str) -> list[str]:
    """Every fact about *this* repository found in ``text``, named.

    Returns a list of human-readable offenders (``"<match> (<why>)"``), empty
    when the text is clean. A caller asserts on the list rather than on a
    boolean so the failure carries the string that gave it away.
    """
    found: list[str] = []
    for pattern, why in _LOCAL_FACT_PATTERNS:
        for match in re.findall(pattern, text):
            found.append(f"{match} ({why})")
    version = get_actual_version()
    if version in text:
        found.append(f"{version} (Beadloom's own version)")
    for package in BEADLOOM_PACKAGES:
        if f"`{package}/`" in text:
            found.append(f"{package}/ (a Beadloom DDD package)")
    return found


# --------------------------------------------------------------------------- #
# An adopter project Beadloom can actually index (BDL-062 `.5`)
# --------------------------------------------------------------------------- #
#
# The factories above build manifests, which is all the CLAUDE.md renderer
# reads. BDL-062's three rules read the *index*: `graph-summary-facts` reads
# `nodes.summary`, `doc-area-coherence` reads node source against doc path, and
# the audit's three populations are computed from the project's own facts. None
# of those can be pointed at a manifest alone.
#
# :func:`indexed_python_project` is the same "not Beadloom" idea one layer
# deeper — a project with a graph, a docs tree and a config, whose every knob is
# a parameter so one factory covers the states the rules must keep apart:
#
#   docs_layout="by-area"  a derivable convention        -> the rule can check
#   docs_layout="flat"     no convention to derive       -> the rule checked nothing
#   misfiled=(...)         a node contradicting it       -> the rule found something
#   version=None           a version nothing can resolve -> the fact is declined
#   summaries={...}        a claim in a node summary     -> agrees/disagrees/unverifiable
#
# FAKES PROVE FAKES: the "by-area" spelling is a control, not decoration. A
# stand-down reported on the flat tree proves nothing unless the same nodes,
# the same summaries and the same rule report a clean check when the tree is
# nested — otherwise the fixture might simply be broken.

#: The areas every indexed adopter is built with, and how many modules each
#: holds. Four is not arbitrary: ``doc-area-coherence`` needs ``min_support``
#: (2) observations before a mapping counts, and misfiling one of four leaves
#: 3/4 = 0.75 agreement, above the 0.6 default threshold, so the misfiled node
#: is reported rather than dissolving the convention it contradicts.
ADOPTER_AREAS: tuple[str, ...] = ("billing", "ledger", "reporting")
ADOPTER_MODULES_PER_AREA = 4


def _adopter_pyproject(version: str | None) -> str:
    """The manifest, with or without a resolvable version.

    ``version=None`` omits the field entirely rather than writing an empty
    string: an empty ``version = ""`` is a declaration, and the state under test
    is a project that declares none.
    """
    body = '[project]\nname = "invoice-svc"\n'
    if version is not None:
        body += f'version = "{version}"\n'
    return body + 'dependencies = ["fastapi", "sqlalchemy"]\n'


def indexed_python_project(
    root: Path,
    *,
    docs_layout: str = "by-area",
    version: str | None = "3.7.0",
    misfiled: tuple[str, ...] = (),
    summaries: dict[str, str] | None = None,
    rules: str | None = None,
) -> AdopterProject:
    """A project that is not Beadloom, complete enough to reindex and lint.

    Parameters
    ----------
    docs_layout:
        ``"by-area"`` files each document under ``docs/<area>/``, which is a
        convention ``doc-area-coherence`` can derive. ``"flat"`` files every
        document directly under ``docs/``, which is a tree with no area segment
        to read — the rule's ``unverifiable`` path.
    version:
        What the manifest declares. ``None`` declares nothing, so the audit
        declines the ``version`` fact and any summary claiming a version becomes
        ``unverifiable`` rather than wrong.
    misfiled:
        ``ref_id``s whose document is filed under a neighbouring area, so the
        rule has a contradiction to name.
    summaries:
        ``ref_id`` → the node's ``summary:``. Anything not named here gets a
        summary that states no number, so a test's claims are the only claims.
    rules:
        The body of ``rules.yml``. Defaults to the two rules BDL-062 added.
    """
    if docs_layout not in {"by-area", "flat"}:
        raise ValueError(f"unknown docs_layout {docs_layout!r}")

    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(_adopter_pyproject(version), encoding="utf-8")

    beadloom_dir = root / ".beadloom"
    graph_dir = beadloom_dir / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (beadloom_dir / "config.yml").write_text(
        "languages:\n- .py\nscan_paths:\n- src\n", encoding="utf-8"
    )

    claimed = summaries or {}
    lines = ["nodes:"]
    for position, area in enumerate(ADOPTER_AREAS):
        elsewhere = ADOPTER_AREAS[(position + 1) % len(ADOPTER_AREAS)]
        for index in range(ADOPTER_MODULES_PER_AREA):
            ref_id = f"{area}-m{index}"
            source = f"src/invoice_svc/{area}/m{index}.py"
            filed_under = elsewhere if ref_id in misfiled else area
            doc = (
                f"docs/{filed_under}-{ref_id}.md"
                if docs_layout == "flat"
                else f"docs/{filed_under}/{ref_id}.md"
            )

            code = root / source
            code.parent.mkdir(parents=True, exist_ok=True)
            code.write_text(f"# beadloom:domain={area}\n", encoding="utf-8")

            page = root / doc
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(
                f"# {ref_id}\n\nA module of the invoicing service.\n", encoding="utf-8"
            )

            summary = claimed.get(ref_id, f"The {ref_id} module of the invoicing service")
            lines += [
                f"  - ref_id: {ref_id}",
                "    kind: component",
                f"    summary: {summary}",
                f"    source: {source}",
                "    docs:",
                f"      - {doc}",
            ]
    lines.append("edges: []")
    (graph_dir / "services.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    (graph_dir / "rules.yml").write_text(
        rules
        if rules is not None
        else (
            "version: 3\n"
            "rules:\n"
            "  - name: doc-area-coherence\n"
            "    description: a node documents itself where the graph says it should\n"
            "    doc_area_coherence: {}\n"
            "  - name: graph-summary-facts\n"
            "    description: a number in a node summary matches what the project computes\n"
            "    summary_facts: {}\n"
        ),
        encoding="utf-8",
    )
    return AdopterProject(root=root, name="invoice-svc", version=version, stack="python")
