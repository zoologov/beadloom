"""Architecture presets for bootstrap graph generation.

Each preset defines rules for mapping directory structures to graph node
kinds and edges.  Four built-in presets cover the most common architectures:
monolith, microservices, monorepo, and a Feature-Sliced Design frontend (``fsd``).
"""

# beadloom:domain=onboarding

from __future__ import annotations

import json
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

#: Feature-Sliced Design's six layers, top to bottom: a layer imports only the layers
#: below it (BDL-080 S3c, RFC D4).
FSD_LAYERS: tuple[str, ...] = ("app", "pages", "widgets", "features", "entities", "shared")

#: How many of the six layer folders make a project FSD. Fewer is a coincidence of
#: names: a monolith has an ``app/`` and a ``shared/`` often enough.
_FSD_MIN_LAYERS = 3

#: Where the layer folders are looked for, in order. ``src`` first, because an Expo
#: project keeps its router in an ``app/`` at the root and its FSD layers under ``src/``.
_FSD_ROOTS: tuple[str, ...] = ("src", "")

FSD = Preset(
    name="fsd",
    description=(
        "Feature-Sliced Design frontend: a slice is a component tagged with its layer, "
        "app and shared hold segments, folders beside the layers are legacy nodes."
    ),
    dir_rules=(),
    # A folder outside the FSD root (an Expo Router `app/` at the project root) is a
    # part of the frontend, not a bounded context.
    default_kind="component",
    infer_part_of=True,
    infer_deps_from_manifests=False,
)

PRESETS: dict[str, Preset] = {
    "monolith": MONOLITH,
    "microservices": MICROSERVICES,
    "monorepo": MONOREPO,
    "fsd": FSD,
}


def fsd_root(project_root: Path) -> str | None:
    """The project-relative folder holding the FSD layers, ``""`` for the root, or ``None``.

    A folder is the FSD root when at least three of :data:`FSD_LAYERS` are folders in it.
    ``src/`` is read before the root (see :data:`_FSD_ROOTS`).
    """
    for root in _FSD_ROOTS:
        folder = project_root / root if root else project_root
        present = [layer for layer in FSD_LAYERS if (folder / layer).is_dir()]
        if len(present) >= _FSD_MIN_LAYERS:
            return root
    return None


def detect_preset(project_root: Path) -> Preset:
    """Auto-detect the best preset for a project.

    Heuristic (evaluated in order):
    0. At least three Feature-Sliced Design layer folders at the root or under
       ``src/`` -> fsd (:func:`fsd_root`)
    1. Mobile app indicators (React Native / Expo / Flutter) -> monolith
    2. ``services/`` or ``cmd/`` directory -> microservices
    3. ``packages/`` or ``apps/`` directory -> monorepo
    4. Otherwise -> monolith

    Mobile apps often have a ``services/`` directory containing internal API
    modules, not independent microservices.  We check for mobile indicators
    first so these projects are not misclassified as microservices.

    FSD comes before all of them: a React Native project in the FSD layout is
    mobile AND layered, and read as a monolith its layers became domains and its
    slices their children, with no layer rule to judge them (BDL-080 S3c).
    """
    if fsd_root(project_root) is not None:
        return FSD

    # --- Mobile app detection (must come before services/cmd check) ---
    pkg_json = project_root / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            all_deps: dict[str, object] = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }
            if "react-native" in all_deps or "expo" in all_deps:
                return MONOLITH
        except (json.JSONDecodeError, OSError):
            pass

    if (project_root / "pubspec.yaml").exists():
        return MONOLITH

    # --- Standard directory-based heuristics ---
    children = {
        p.name for p in project_root.iterdir() if p.is_dir() and not p.name.startswith(".")
    }

    if children & {"services", "cmd"}:
        return MICROSERVICES
    if children & {"packages", "apps"}:
        return MONOREPO
    return MONOLITH
