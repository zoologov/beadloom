"""Generation-time Mermaid validity guard (BDL-041 F4.4 BEAD-01).

A *targeted structural* validator — NOT a full Mermaid parser — that rejects the
two F4 render bug classes in pytest (no browser / no node), so a broken diagram
fails ``beadloom docs site`` instead of the VitePress render:

1. **Reserved-id / charset** — a flowchart (``graph``/``flowchart``) node id that
   equals a reserved Mermaid keyword (e.g. a node literally named ``graph``,
   which collides with the ``graph LR`` keyword) or carries an illegal charset.
   Fixed upstream by prefixing landscape ids (``n_…``); the guard makes a
   regression impossible without a browser.
2. **C4 Rel integrity** — a C4 ``Rel(a, b, …)`` whose endpoint is NOT declared
   in the diagram body as a ``Container``/``Component``/``Person``/``System*``
   element. This is the ``drawRels`` *"Cannot read properties of undefined
   (reading 'x')"* crash on a Rel to the undeclared ``System`` root.

The check is a small extensible registry of validators; each returns a list of
:class:`MermaidIssue`. :func:`validate_mermaid` runs them all and concatenates
the issues. It is deterministic (issues are emitted in source order) and is
called by ``generate_site`` on EVERY emitted diagram (raising on any issue).
"""

# beadloom:domain=application

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# Reserved Mermaid flowchart keywords a node id must never equal. A node literally
# named ``graph`` collides with the ``graph LR`` declaration keyword and produces
# the live ``got 'GRAPH'`` parse error.
_RESERVED_KEYWORDS = frozenset(
    {
        "graph",
        "flowchart",
        "subgraph",
        "end",
        "class",
        "classdef",
        "click",
        "style",
        "linkstyle",
        "direction",
        "interpolate",
        "default",
    }
)

# Valid Mermaid identifier charset (matches the landscape/c4 sanitizers).
_VALID_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")

# A flowchart node declaration line: ``    n_cli[cli]`` / ``id(label)`` /
# ``id{label}``. We only need the *leading id token* before the shape bracket.
_FLOW_NODE_RE = re.compile(r"^\s*([^\s\[\(\{>]+)\s*[\[\(\{]")

# Flowchart edge line: ``a -->|LABEL| b`` / ``a --> b`` / ``a --- b``. The id
# tokens flank the arrow operator.
_FLOW_EDGE_RE = re.compile(r"^\s*([^\s]+)\s*-[-.=]?-?[->ox|]+.*?\s([^\s]+)\s*$")

# A ``click <id> "<url>"`` directive — the id is the second token.
_FLOW_CLICK_RE = re.compile(r"^\s*click\s+(\S+)\s")

# C4 element declarations whose first arg is the declared id. Boundaries are
# excluded on purpose: ``System_Boundary(x_boundary, …)`` declares a *grouping*,
# not a Rel-addressable node — Rels to a boundary's anchor crash ``drawRels``.
_C4_DECL_RE = re.compile(
    r"\b(?:System(?:_Ext)?|Person(?:_Ext)?|Container(?:_Ext|Db)?"
    r"|Component(?:_Ext|Db)?)\s*\(\s*([A-Za-z0-9_]+)\s*,"
)

# A C4 ``Rel(a, b, …)`` (and directional variants ``Rel_U``/``BiRel``/…). The
# first two args are the endpoint ids that must both be declared.
_C4_REL_RE = re.compile(
    r"\b(?:Bi)?Rel(?:_[UDLR]+)?\s*\(\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*,"
)


@dataclass(frozen=True)
class MermaidIssue:
    """A single structural problem found in a Mermaid diagram.

    Attributes:
        kind: A stable machine code — ``reserved-id`` / ``charset`` /
            ``c4-rel-undeclared``.
        message: A human-readable description (includes the offending token).
    """

    kind: str
    message: str


def _is_flowchart(text: str) -> bool:
    """True if *text* declares a flowchart (``graph``/``flowchart`` header)."""
    return bool(re.search(r"^\s*(?:graph|flowchart)\b", text, re.MULTILINE))


def _is_c4(text: str) -> bool:
    """True if *text* declares a C4 diagram (``C4Context``/``C4Container``/…)."""
    return bool(re.search(r"^\s*C4(?:Context|Container|Component|Dynamic)\b", text, re.MULTILINE))


def _flowchart_node_ids(text: str) -> list[str]:
    """Collect declared flowchart node ids (decls, click targets, edge ends).

    Returns ids in source order with duplicates preserved so the validators emit
    deterministic, line-ordered issues.
    """
    ids: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith(("graph ", "flowchart")):
            continue
        # A node decl (``id[…]`` / ``id(…)`` / ``id{…}``) is checked even when the
        # id equals a directive keyword — that collision is exactly the bug. Only
        # genuine directive lines (a keyword with NO shape bracket) are skipped.
        decl = _FLOW_NODE_RE.match(line)
        if decl:
            ids.append(decl.group(1))
            continue
        if _is_directive_line(stripped):
            continue
        click = _FLOW_CLICK_RE.match(line)
        if click:
            ids.append(click.group(1))
            continue
        edge = _FLOW_EDGE_RE.match(line)
        if edge:
            ids.extend((edge.group(1), edge.group(2)))
    return ids


# Directive line leaders (no shape bracket) that are NOT node declarations.
_DIRECTIVE_LEADERS = ("classDef", "class ", "style ", "linkStyle", "subgraph", "direction")


def _is_directive_line(stripped: str) -> bool:
    """True for a genuine flowchart directive (a keyword used as a statement)."""
    return stripped.startswith(_DIRECTIVE_LEADERS)


def _validate_flowchart_ids(text: str) -> list[MermaidIssue]:
    """Reserved-keyword + charset check on flowchart node ids."""
    if not _is_flowchart(text):
        return []
    issues: list[MermaidIssue] = []
    seen: set[str] = set()
    for node_id in _flowchart_node_ids(text):
        if node_id in seen:
            continue
        seen.add(node_id)
        if node_id.lower() in _RESERVED_KEYWORDS:
            issues.append(
                MermaidIssue(
                    kind="reserved-id",
                    message=(
                        f"flowchart node id {node_id!r} is a reserved Mermaid "
                        f"keyword (prefix it, e.g. n_{node_id})"
                    ),
                )
            )
        elif not _VALID_ID_RE.match(node_id):
            issues.append(
                MermaidIssue(
                    kind="charset",
                    message=(
                        f"flowchart node id {node_id!r} has an illegal charset "
                        "(only [A-Za-z0-9_] allowed)"
                    ),
                )
            )
    return issues


def _validate_c4_rels(text: str) -> list[MermaidIssue]:
    """Every C4 ``Rel(a, b, …)`` endpoint must be a declared element."""
    if not _is_c4(text):
        return []
    declared = set(_C4_DECL_RE.findall(text))
    issues: list[MermaidIssue] = []
    for src, dst in _C4_REL_RE.findall(text):
        for endpoint in (src, dst):
            if endpoint not in declared:
                issues.append(
                    MermaidIssue(
                        kind="c4-rel-undeclared",
                        message=(
                            f"C4 Rel endpoint {endpoint!r} is not a declared "
                            "Container/Component/Person/System node (a Rel to a "
                            "boundary/root crashes drawRels)"
                        ),
                    )
                )
    return issues


# Extensible registry of structural validators (run in order; deterministic).
_VALIDATORS: tuple[Callable[[str], list[MermaidIssue]], ...] = (
    _validate_flowchart_ids,
    _validate_c4_rels,
)


def validate_mermaid(text: str) -> list[MermaidIssue]:
    """Run every structural validator over *text* and return all issues.

    Args:
        text: A Mermaid diagram (a bare diagram, or a Markdown page containing a
            ```` ```mermaid ```` fence — both are accepted).

    Returns:
        A list of :class:`MermaidIssue` (empty when the diagram is structurally
        valid for the covered bug classes), in deterministic source order.
    """
    issues: list[MermaidIssue] = []
    for validator in _VALIDATORS:
        issues.extend(validator(text))
    return issues
