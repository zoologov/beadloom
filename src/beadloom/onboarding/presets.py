"""Architecture presets for bootstrap graph generation.

Each preset defines rules for mapping directory structures to graph node
kinds and edges.  Three built-in presets cover the most common architectures:
monolith, microservices, and monorepo.
"""

# beadloom:domain=onboarding

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class PresetRule:
    """Maps a directory name pattern to a node kind."""

    pattern: re.Pattern[str]
    kind: str  # domain, feature, service, entity
    confidence: str = "high"  # high, medium, low


@dataclass(frozen=True)
class Preset:
    """Architecture preset defining node/edge generation rules."""

    name: str
    description: str
    dir_rules: tuple[PresetRule, ...] = ()
    default_kind: str = "service"
    infer_part_of: bool = True
    infer_deps_from_manifests: bool = False

    def classify_dir(self, dir_name: str) -> tuple[str, str]:
        """Return (kind, confidence) for a directory name.

        Falls back to (default_kind, 'medium') if no rule matches.
        """
        lower = dir_name.lower()
        for rule in self.dir_rules:
            if rule.pattern.search(lower):
                return rule.kind, rule.confidence
        return self.default_kind, "medium"


# ---------------------------------------------------------------------------
# Common directory-name patterns
# ---------------------------------------------------------------------------

_ENTITY_DIRS = re.compile(r"^(models?|entities|schemas?|types|dataclasses|orm|db|database)$")
_FEATURE_DIRS = re.compile(
    r"^(api|routes?|controllers?|handlers?|views?|endpoints?|graphql|grpc|rest)$"
)
_SERVICE_DIRS = re.compile(r"^(services?|core|engine|workers?|jobs?|tasks?|processors?)$")
_UTILITY_DIRS = re.compile(
    r"^(utils?|common|shared|helpers?|lib|tools|middleware|config|settings?)$"
)

# ---------------------------------------------------------------------------
# Built-in presets
# ---------------------------------------------------------------------------

MONOLITH = Preset(
    name="monolith",
    description=(
        "Single deployable: top-level dirs are domains, subdirs map to features/entities/services."
    ),
    dir_rules=(
        PresetRule(_ENTITY_DIRS, "entity", "high"),
        PresetRule(_FEATURE_DIRS, "feature", "high"),
        PresetRule(_SERVICE_DIRS, "service", "high"),
        PresetRule(_UTILITY_DIRS, "service", "medium"),
    ),
    default_kind="domain",
    infer_part_of=True,
    infer_deps_from_manifests=False,
)

MICROSERVICES = Preset(
    name="microservices",
    description=(
        "Independent services: top-level dirs are services, shared code becomes domains."
    ),
    dir_rules=(
        PresetRule(_ENTITY_DIRS, "entity", "high"),
        PresetRule(_FEATURE_DIRS, "feature", "high"),
        PresetRule(_SERVICE_DIRS, "service", "high"),
        PresetRule(
            re.compile(r"^(shared|common|lib|packages?)$"),
            "domain",
            "high",
        ),
    ),
    default_kind="service",
    infer_part_of=True,
    infer_deps_from_manifests=False,
)

MONOREPO = Preset(
    name="monorepo",
    description=(
        "Multi-package repo: packages/apps are services, "
        "shared packages are domains, manifest deps become edges."
    ),
    dir_rules=(
        PresetRule(_ENTITY_DIRS, "entity", "high"),
        PresetRule(_FEATURE_DIRS, "feature", "high"),
        PresetRule(_SERVICE_DIRS, "service", "high"),
        PresetRule(
            re.compile(r"^(shared|common|lib)$"),
            "domain",
            "high",
        ),
    ),
    default_kind="service",
    infer_part_of=True,
    infer_deps_from_manifests=True,
)

PRESETS: dict[str, Preset] = {
    "monolith": MONOLITH,
    "microservices": MICROSERVICES,
    "monorepo": MONOREPO,
}


def detect_preset(project_root: Path) -> Preset:
    """Auto-detect the best preset for a project.

    Heuristic:
    - ``services/`` or ``cmd/`` directory -> microservices
    - ``packages/`` or ``apps/`` directory -> monorepo
    - Otherwise -> monolith
    """
    children = {
        p.name for p in project_root.iterdir() if p.is_dir() and not p.name.startswith(".")
    }

    if children & {"services", "cmd"}:
        return MICROSERVICES
    if children & {"packages", "apps"}:
        return MONOREPO
    return MONOLITH
