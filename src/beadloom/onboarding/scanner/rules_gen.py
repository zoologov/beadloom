"""Generate rules.yml from a discovered graph + read rule metadata."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.graph.rules.loader import AUTHORING_KEYS
from beadloom.infrastructure.atomic_io import write_text_atomic, write_yaml_atomic
from beadloom.onboarding.presets import FSD_LAYERS

if TYPE_CHECKING:
    from pathlib import Path


def generate_rules(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
    project_name: str,
    rules_path: Path,
) -> int:
    """Generate ``rules.yml`` from discovered graph structure.

    Only creates structural *require* rules — no *deny* rules by default.
    Returns the number of rules written.
    """
    kinds = {n["kind"] for n in nodes}
    rules: list[dict[str, Any]] = []

    # Rule 1: every domain must have a part_of edge (to any node).
    # Using an empty matcher so sub-domains pointing at a parent domain
    # (rather than the root) are not flagged as violations.
    if "domain" in kinds:
        rules.append(
            {
                "name": "domain-needs-parent",
                "description": "Every domain must have a part_of edge",
                "require": {
                    "for": {"kind": "domain"},
                    "has_edge_to": {},
                    "edge_kind": "part_of",
                },
            }
        )

    # Rule 2: every feature must have a part_of edge (to any node).
    # Using an empty matcher so features placed under a service parent
    # (e.g. `core-rest` part_of the `core` service) are not flagged as
    # violations.  The bootstrap classifier legitimately nests feature
    # dirs (api/rest/graphql) inside service dirs (core/tasks/workers);
    # requiring a `domain` parent makes a clean bootstrap fail its own
    # `lint --strict` gate out of the box (BDL-UX-Issues #71).
    if "feature" in kinds:
        rules.append(
            {
                "name": "feature-needs-parent",
                "description": "Every feature must have a part_of edge",
                "require": {
                    "for": {"kind": "feature"},
                    "has_edge_to": {},
                    "edge_kind": "part_of",
                },
            }
        )

    # Note: service-needs-parent rule was intentionally removed.
    # The root service node has no parent by definition, so the rule
    # always fails on freshly bootstrapped projects. The domain-needs-parent
    # and feature-needs-parent rules are sufficient for structural enforcement.

    if not rules:
        return 0

    data: dict[str, Any] = {"version": 1, "rules": rules}
    write_yaml_atomic(rules_path, data, default_flow_style=False, allow_unicode=True)
    return len(rules)


#: The cohesion signal per FSD layer: the most symbols one slice (or one segment of
#: ``app`` and ``shared``) owns before ``check`` reports it. Measured on Beadloom's own
#: portal after its viewer was cut into FSD slices (BDL-080 S2, RFC D3): the largest
#: widget owns 65 symbols, so widgets get 80 and every other layer 60. A signal, not a
#: target: shape comes first, and a project recalibrates these with a stated reason.
#: The number is the one that portal's ``rules.yml`` states beside the same limits,
#: with the commit it was measured at; a self-check holds the two to one number.
FSD_COHESION_LIMITS: dict[str, int] = {
    "app": 60,
    "pages": 60,
    "widgets": 80,
    "features": 60,
    "entities": 60,
    "shared": 60,
}

#: The layers that hold slices; ``app`` and ``shared`` hold segments.
_SLICED_LAYERS: tuple[str, ...] = ("pages", "widgets", "features", "entities")

_FSD_HEADER = """\
# The rules `beadloom init` wrote for a Feature-Sliced Design frontend (preset `fsd`).
#
# Steiger, the official FSD linter, is the reference for them: its `recommended` set
# judges files (forbidden-imports, public-api, no-public-api-sidestep,
# insignificant-slice, no-layer-public-api), and these rules judge the graph the
# portal draws. Run both: `npm run lint:fsd` is Steiger. Folders beside the layers
# are nodes tagged `fsd-legacy` and stand outside every rule below, so the graph
# shows them without judging them.
version: 3
rules:
"""

_FSD_LAYERS_RULE = """\
  # FSD's layers belong to one application root: a rule stratifies the slices of the
  # frontend service that holds them, and a layer imports only the layers below it.
  # Cross imports inside one layer are forbidden by the rule, as FSD prescribes: two
  # slices of one layer do not know each other (Steiger: forbidden-imports). There is
  # no node per layer, so two slices of one layer are never internal to one container;
  # `app` and `shared` hold segments, which import one another freely.
  - name: fsd-layers
    title: "FSD architecture"
    description: "The frontend's Feature-Sliced layers import downward: {layer_names}"
    severity: error
    scope: {frontend}
    layers:
{layer_lines}    enforce: top-down
    allow_skip: true
    edge_kind: depends_on
"""

_FSD_PUBLIC_API_RULE = """\
  # A slice is entered through its public API, the index at its top. An import that
  # reaches past another slice's index is a finding (Steiger: no-public-api-sidestep;
  # its public-api reports a slice with no index), judged on the imports the reindex
  # resolved, aliases included.
  - name: fsd-public-api
    description: "An import into a slice from outside it lands on the slice's index"
    severity: error
    slice_public_api:
      tags: [{slice_tags}]
"""

_FSD_SHAPE_RULE = """\
  # FSD gives no file count; it gives the shape: a slice is one business entity or
  # feature, with the standard segments (ui, model, lib, api, config) and a public API
  # in index. A slice whose lib/ or model/ grows past the standard segments is a
  # finding; so is a code file at its top that is not its index.
  - name: fsd-slice-shape
    description: "A slice's top holds its standard segments and its index"
    severity: warn
    slice_shape:
      tags: [{slice_tags}]
      segments: [ui, model, lib, api, config]
"""

_FSD_COHESION_COMMENT = """\
  # The rule judges shape first and keeps a calibrated symbol-count signal second -- a
  # signal, not a target: the symbols one slice (or one segment of app and shared)
  # owns. Calibrated on Beadloom's own FSD portal, whose largest widget owns 65
  # symbols: 80 for widgets, 60 for every other layer. A slice past it is a candidate
  # for a split by responsibility; a limit is recalibrated here with its reason.
"""

_FSD_COHESION_RULE = """\
  - name: fsd-cohesion-{layer}
    description: "A slice of the {layer} layer owns at most {limit} symbols"
    severity: warn
    check:
      for: {{ kind: component, tag: fsd-{layer} }}
      max_symbols: {limit}
"""


def fsd_rules_text(frontend: str) -> str:
    """The ``rules.yml`` text :func:`generate_fsd_rules` writes for *frontend*."""
    slice_tags = ", ".join(f"fsd-{layer}" for layer in _SLICED_LAYERS)
    layer_lines = "".join(
        f"      - name: {layer}\n        tag: fsd-{layer}\n" for layer in FSD_LAYERS
    )
    return "".join(
        (
            _FSD_HEADER,
            _FSD_LAYERS_RULE.format(
                layer_names=", ".join(FSD_LAYERS), frontend=frontend, layer_lines=layer_lines
            ),
            "\n",
            _FSD_PUBLIC_API_RULE.format(slice_tags=slice_tags),
            "\n",
            _FSD_SHAPE_RULE.format(slice_tags=slice_tags),
            "\n",
            _FSD_COHESION_COMMENT,
            *(
                _FSD_COHESION_RULE.format(layer=layer, limit=limit)
                for layer, limit in FSD_COHESION_LIMITS.items()
            ),
        )
    )


def generate_fsd_rules(frontend: str, rules_path: Path) -> int:
    """Write the FSD rules for the frontend service *frontend*; return how many.

    BDL-080 S3c, RFC D4: the layer order scoped to *frontend* and titled
    ``FSD architecture`` for the portal, ``slice_public_api``, ``slice_shape`` and one
    cohesion ``check`` per layer (:data:`FSD_COHESION_LIMITS`). Written as text, so
    the owner's reason for each rule stands beside it in the file an adopter edits.
    """
    write_text_atomic(rules_path, fsd_rules_text(frontend))
    return 3 + len(FSD_COHESION_LIMITS)


#: The authoring keys whose label in the agent instructions is not the key
#: itself, kept for the names the generated `.beadloom/AGENTS.md` has always
#: printed: ``check`` reads as ``cardinality`` and ``forbid`` as ``forbid_edge``.
_LABEL_FOR_KEY: dict[str, str] = {"check": "cardinality", "forbid": "forbid_edge"}


def _detect_rule_type(rule: dict[str, object]) -> str:
    """Label a rules.yml rule entry by the authoring key that selects its type.

    WHICH keys select a type is read from `graph.rules.loader.AUTHORING_KEYS`, the
    keys of the loader's own dispatch table, rather than from a twelve-key copy
    here: a copy fell behind the loader once, and the rules it did not know read
    "unknown" in the generated `.beadloom/AGENTS.md` (BDL-062 `.4`). What the
    label SAYS stays here, in `_LABEL_FOR_KEY`, because the loader has no display
    names to share — its table maps a key to a parser, and the evaluators' own
    ``rule_type`` strings (``cycle``, ``layer``) are a third vocabulary that the
    agent instructions have never used.

    The rule's own keys are walked in the order its author wrote them, so a rule
    naming two kinds — which the loader rejects — is labelled by the first.
    """
    for key in rule:
        if key in AUTHORING_KEYS:
            return _LABEL_FOR_KEY.get(key, key)
    return "unknown"


def _read_rules_data(project_root: Path) -> list[dict[str, str]]:
    """Read architecture rules from rules.yml as structured data."""
    rules_path = project_root / ".beadloom" / "_graph" / "rules.yml"
    if not rules_path.exists():
        return []
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    if not data or not data.get("rules"):
        return []
    result: list[dict[str, str]] = []
    for rule in data["rules"]:
        rule_type = _detect_rule_type(rule)
        result.append(
            {
                "name": rule.get("name", "unnamed"),
                "type": rule_type,
                "description": rule.get("description", ""),
            }
        )
    return result
