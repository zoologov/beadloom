"""The lint findings of one rule kind, picked out of a violation list."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beadloom.graph.rules import Violation

LIVENESS_KIND = "rule_liveness"


def liveness_of(violations: list[Violation]) -> list[Violation]:
    return [v for v in violations if v.rule_type == LIVENESS_KIND]


def forbidden_of(violations: list[Violation]) -> list[Violation]:
    return [v for v in violations if v.rule_type == "forbid_import"]
