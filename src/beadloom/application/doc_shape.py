# beadloom:domain=application
# beadloom:component=doc-shape-requirements
"""Resolve a project's required document sections, for the doc-shape check.

The shape a document must keep is derived from the composed doc templates, which
live in the ``onboarding`` domain; the check that reads a document back lives in
``doc-sync``. The two are peers and neither may import the other, so the join
happens here, in the layer whose job is exactly this kind of orchestration.

One function, one caller shape: every surface that REPORTS freshness to a human
or to CI calls this and passes the result into ``check_sync``. The three call
sites that deliberately do not are named in the SPEC — re-baselining a pair
(``sync-update``) cannot fix a missing section, and publishing a site does not
judge one.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from beadloom.onboarding.doc_templates import required_sections_by_node_kind
from beadloom.onboarding.flow_config import FlowConfigError

if TYPE_CHECKING:
    from pathlib import Path


def section_requirements(project_root: Path) -> dict[str, tuple[str, ...]] | None:
    """Required sections per graph node kind, or ``None`` when unresolvable.

    ``None`` — structure is not checked — is returned only for a malformed
    ``flow.yml``, which ``config-check`` already reports by name. Raising here
    would turn one configuration error into a failing freshness gate that names
    the wrong file.
    """
    from beadloom.onboarding.doc_templates import doc_flow_config

    try:
        config = doc_flow_config(project_root)
    except FlowConfigError:
        return None
    return required_sections_by_node_kind(config=config, project_root=project_root)


def document_section_requirements(project_root: Path) -> dict[str, tuple[str, ...]]:
    """Required sections per PLANNING document kind, or ``{}`` when unresolvable.

    The same join :func:`section_requirements` performs for generated node
    documentation, over the other family of composed templates. ``{}`` — nothing
    is required, so nothing is reported — is returned for a malformed
    ``flow.yml``, which ``config-check`` already names: raising here would turn
    one configuration error into a document-quality run that names the wrong
    file.
    """
    from beadloom.onboarding.doc_templates import (
        doc_flow_config,
        required_sections_by_document_kind,
    )

    try:
        config = doc_flow_config(project_root)
        return required_sections_by_document_kind(
            config=config, project_root=project_root
        )
    except FlowConfigError:
        return {}


#: Where the flow's planning documents live, when a project declares nothing.
#: The convention the shipped ``/task-init`` scaffolds into and
#: ``active_table`` already reads (``.claude/development/docs/features/<KEY>/``).
DEFAULT_PLANNING_GLOBS: tuple[str, ...] = (
    ".claude/development/docs/features/*/*.md",
)

#: ``.beadloom/config.yml`` key holding a project's own globs.
_CONFIG_KEY = "doc_quality"


def planning_document_globs(project_root: Path) -> tuple[str, ...]:
    """The globs a project's planning documents are found by.

    Configurable from the start, because the flow ships to projects with their
    own conventions and a hardcoded path would make the check true only here —
    the defect ``tests/adopter_project.py`` exists to catch.
    """
    import yaml

    config = project_root / ".beadloom" / "config.yml"
    if not config.is_file():
        return DEFAULT_PLANNING_GLOBS
    data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    block = data.get(_CONFIG_KEY) if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return DEFAULT_PLANNING_GLOBS
    paths = block.get("paths")
    if isinstance(paths, str):
        return (paths,)
    if isinstance(paths, list) and all(isinstance(p, str) for p in paths):
        return tuple(paths) or DEFAULT_PLANNING_GLOBS
    return DEFAULT_PLANNING_GLOBS


def planning_documents(project_root: Path) -> list[Path]:
    """Every planning document the quality checks read, deterministically ordered."""
    found: list[Path] = []
    for pattern in planning_document_globs(project_root):
        found.extend(p for p in project_root.glob(pattern) if p.is_file())
    return sorted(set(found))


#: An inline code span — a command's syntax, never a document's placeholder.
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

#: A bracketed span the author is meant to replace. Excludes a markdown link
#: (``[text](url)``) and a task checkbox, neither of which is a placeholder.
_BRACKET_RE = re.compile(r"\[([^\[\]\n]{2,90})\](?!\()")

#: An angle-bracketed span with prose inside — ``<the scenario's exact name>``.
_ANGLE_RE = re.compile(r"<([a-z][^<>\n]{3,90})>")

#: An enumerated stub that stands in for content: ``Goal 1``, ``Criterion 1``.
#: Letter-space-digit, so an identifier like ``Q1`` or ``BEAD-01`` is not one.
_ENUMERATED_RE = re.compile(r"\b([A-Z][a-z]{2,15} \d{1,2})\b")


def _outside(match: re.Match[str], code: list[tuple[int, int]]) -> bool:
    """Whether *match* lies wholly outside every inline code span.

    A span that CONTAINS code is still a placeholder — the shipped
    ``[Which domains ... discover via `beadloom ctx`]`` is one — so containment
    is tested the one way round that answers the question asked.
    """
    start, end = match.span()
    return not any(cs <= start and end <= ce for cs, ce in code)


def shipped_placeholders(project_root: Path) -> tuple[str, ...]:
    """Placeholder tokens the shipped document templates leave for the author.

    DERIVED from the composed ``/templates`` command rather than listed in code:
    a hand-kept list is a second source of truth that goes stale the first time
    a template gains a field, and the check would then pass documents that were
    never filled in.

    Read only from FENCED blocks — those are the templates themselves; the prose
    around them is commentary and its brackets are not placeholders. Inline code
    spans are removed first: ``beadloom ctx <ref-id>`` is a command's
    metavariable, and treating it as a placeholder would report the correct
    documentation of every command this project ships.
    """
    from beadloom.onboarding.composer import compose
    from beadloom.onboarding.doc_templates import doc_flow_config

    try:
        text = compose(
            "commands",
            "templates",
            config=doc_flow_config(project_root),
            project_root=project_root,
        ).text
    except FlowConfigError:
        return ()

    tokens: set[str] = set()
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            continue
        code = [m.span() for m in _INLINE_CODE_RE.finditer(line)]
        tokens.update(
            f"[{m.group(1)}]" for m in _BRACKET_RE.finditer(line) if _outside(m, code)
        )
        tokens.update(
            f"<{m.group(1)}>" for m in _ANGLE_RE.finditer(line) if _outside(m, code)
        )
        tokens.update(
            m.group(1) for m in _ENUMERATED_RE.finditer(line) if _outside(m, code)
        )
    return tuple(sorted(tokens))
