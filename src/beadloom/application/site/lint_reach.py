# beadloom:domain=application
# beadloom:feature=site-generation
"""Lint's reach on the portal: the population one ``beadloom lint`` run covered.

BDL-080 S4a (RFC D8, BDL-UX #305). A node card that says ``Rule findings: none``
reads the same whether lint found nothing on the node or never ran, and the
findings lint binds to no node — a rule that cannot fire, a scenario pointing at
a line of a document — had no place on the portal at all. This module projects
one lint result to what both data files publish about the whole project:

- ``errors`` and ``warnings``: lint's own totals, over every finding, the ones
  bound to a node and the ones bound to none;
- ``nodes_with_findings``: how many distinct nodes carry at least one finding;
- ``nodeless``: every finding bound to no node, with the file and line it points
  at where it names one.

**One responsibility:** the project-wide projection of a lint result. Which
findings a given node carries is the node card's question
(:mod:`beadloom.application.site.architecture_card`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beadloom.graph.linter import LintResult


@dataclass(frozen=True)
class NodelessFinding:
    """A lint finding bound to no node: the rule, how loudly, what it says and where.

    ``file`` is ``""`` and ``line`` is ``None`` when the finding names no place.
    """

    rule: str
    severity: str
    message: str
    file: str
    line: int | None

    def as_dict(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }


@dataclass(frozen=True)
class LintReach:
    """What one lint run found over the whole project."""

    errors: int
    warnings: int
    nodes_with_findings: int
    nodeless: tuple[NodelessFinding, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "nodes_with_findings": self.nodes_with_findings,
            "nodeless": [finding.as_dict() for finding in self.nodeless],
        }


def lint_reach_of(result: LintResult) -> LintReach:
    """Project *result* to its totals and its node-less findings, sorted for a stable file."""
    nodes = {v.from_ref_id for v in result.violations if v.from_ref_id is not None}
    nodeless = sorted(
        (
            NodelessFinding(
                rule=v.rule_name,
                severity=v.severity,
                message=v.message,
                file=v.file_path or "",
                line=v.line_number,
            )
            for v in result.violations
            if v.from_ref_id is None
        ),
        key=lambda f: (f.rule, f.severity, f.file, f.line or 0, f.message),
    )
    return LintReach(
        errors=result.error_count,
        warnings=result.warning_count,
        nodes_with_findings=len(nodes),
        nodeless=tuple(nodeless),
    )
