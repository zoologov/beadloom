"""Generate rules.yml from a discovered graph + read rule metadata."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.graph.rules import DEFAULT_DISCOURAGED_SEGMENTS, DEFAULT_SLICE_SEGMENTS
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
#:
#: ``pages`` has none (BDL-082 S2a, RFC D3): FSD 2.1 is pages-first — "There's no limit
#: to how much code you can place in a page slice as long as your team still finds it
#: easy to navigate" (``/docs/reference/layers``) — so a limit there asks an adopter
#: to split what the specification tells them to keep together.
FSD_COHESION_LIMITS: dict[str, int] = {
    "app": 60,
    "widgets": 80,
    "features": 60,
    "entities": 60,
    "shared": 60,
}

#: The layers that hold slices; ``app`` and ``shared`` hold segments.
_SLICED_LAYERS: tuple[str, ...] = ("pages", "widgets", "features", "entities")

#: The layers whose segments are entered through their index: ``shared`` and ``app``.
_SEGMENTED_LAYERS: tuple[str, ...] = ("shared", "app")

#: The rules ``fsd.configs.recommended`` turns on, in the plugin's order, each with one
#: line of what it reports and which rule here judges the same thing at the graph's
#: level. Read from the installed ``@feature-sliced/steiger-plugin`` 0.8.0 (BDL-082 S2a,
#: Node v22.9.0, ``npm ci`` of the scaffold's lock): 21 rules defined, these 17 on, all
#: ``error``. Off in ``recommended``: ``no-cross-imports``, ``no-higher-level-imports``,
#: ``import-locality``, ``no-wildcard-exports``.
STEIGER_RECOMMENDED: tuple[tuple[str, str], ...] = (
    ("ambiguous-slice-names", "a slice named like a segment of shared"),
    ("excessive-slicing", "a layer or a group holding more slices than its threshold"),
    ("forbidden-imports", "an import across one layer or upward; fsd-layers"),
    ("inconsistent-naming", "entity slices mixing plural and singular names"),
    ("insignificant-slice", "a slice with one reference or none: merge it or move it"),
    ("no-layer-public-api", "an index file on a layer itself"),
    ("no-public-api-sidestep", "an import past a slice's public API; fsd-public-api"),
    ("no-reserved-folder-names", "a folder inside a segment named like a segment or @x"),
    ("no-segmentless-slices", "a slice with no segments"),
    ("no-segments-on-sliced-layers", "a standard segment directly in a sliced layer"),
    ("no-ui-in-app", "a ui segment in the app layer"),
    ("public-api", "a slice or segment with no public API; fsd-public-api"),
    ("repetitive-naming", "a word repeated across the slice names of a layer"),
    ("segments-by-purpose", "a segment named by essence, not purpose; fsd-slice-shape"),
    ("shared-lib-grouping", "shared/lib holding more modules than its threshold"),
    ("typo-in-layer-name", "a layer folder whose name is likely a misspelt layer"),
    ("no-processes", "the processes layer, deprecated"),
)

_FSD_HEADER = """\
# The rules `beadloom init` wrote for a Feature-Sliced Design frontend (preset `fsd`),
# by feature-sliced.design 2.1.
#
# Steiger, the official FSD linter, judges files; these rules judge the graph the
# portal draws. Run both: `npm run lint:fsd` is Steiger. Its `recommended` set, read
# from @feature-sliced/steiger-plugin 0.8.0, turns on these 17 rules, each named with
# what it reports and, where one does, the rule below that judges the same thing:
#
{steiger_lines}#
# A slice is a folder of a sliced layer holding a standard segment or an index. A folder
# holding neither with a slice below it is a group, at any depth: it has no node, each
# slice in it is one, named <layer>-<group>-<slice> (a group inside a group adds its
# name), and its top holds no code ("there should be no code sharing in that folder").
# Folders beside the layers are nodes tagged `fsd-legacy` and stand outside every rule
# below, so the graph shows them without judging them.
version: 3
rules:
"""

_FSD_LAYERS_RULE = """\
  # FSD's layers belong to one application root: a rule stratifies the slices of the
  # frontend service that holds them, and a layer imports only the layers below it.
  # Cross imports inside one layer are forbidden by the rule, as FSD prescribes: two
  # slices of one layer do not know each other (Steiger: forbidden-imports). The one
  # sanctioned exception is a cross-import API, `entities/<A>/@x/<B>`, which entity B
  # imports from entity A; the specification allows `@x` on the entities layer only.
  # There is no node per layer, so two slices of one layer are never internal to one
  # container; `app` and `shared` hold segments, which import one another freely.
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
  # resolved, aliases included. `@x/<B>` is a second public API of an entity, open to
  # entity B alone. Each segment of shared and app is entered through its own index,
  # and in shared/ui and shared/lib a per-component index (shared/ui/button/index) is an
  # entry as well; two segments of one layer import each other freely.
  - name: fsd-public-api
    description: "An import into a slice or a segment from outside it lands on its index"
    severity: error
    slice_public_api:
      tags: [{public_api_tags}]
"""

_FSD_SHAPE_RULE = """\
  # FSD gives no file count; it gives the shape: a slice is one business entity or
  # feature, with the standard segments (ui, model, lib, api, config) or segments of its
  # own, and a public API in index. A segment is named by its purpose: "Make sure that
  # the name of these segments describes the purpose of the content, not its essence.
  # For example, components, hooks, and types are bad segment names"
  # (/docs/reference/slices-segments). So `segments:` is the known-good set, a folder in
  # `discouraged:` and not in `segments:` is a finding, and any other folder is a custom
  # segment and fine. The discouraged names are Steiger's segments-by-purpose list.
  # A code file at a slice's top that is not its index is a finding, and so is a code
  # file at a group's top. Edit either list here; a name in both is fine.
  - name: fsd-slice-shape
    description: "A slice's top holds segments named by purpose and its index"
    severity: warn
    slice_shape:
      tags: [{slice_tags}]
      segments: [{segments}]
      discouraged: [
{discouraged}      ]
"""

_FSD_COHESION_COMMENT = """\
  # The rule judges shape first and keeps a calibrated symbol-count signal second -- a
  # signal, not a target: the symbols one slice (or one segment of app and shared)
  # owns. Calibrated on Beadloom's own FSD portal, whose largest widget owns 65
  # symbols: 80 for widgets, 60 for every other layer. A slice past it is a candidate
  # for a split by responsibility; a limit is recalibrated here with its reason.
  # No check is written for pages, which FSD 2.1 makes pages-first: "There's no limit
  # to how much code you can place in a page slice as long as your team still finds it
  # easy to navigate" (/docs/reference/layers). Start code in its page and extract it
  # to a lower layer when a second page reuses it.
"""

_FSD_COHESION_RULE = """\
  - name: fsd-cohesion-{layer}
    description: "A slice of the {layer} layer owns at most {limit} symbols"
    severity: warn
    check:
      for: {{ kind: component, tag: fsd-{layer} }}
      max_symbols: {limit}
"""

#: The indent of a wrapped list's lines and the column they stop before.
_LIST_INDENT = "        "
_LINE_LIMIT = 95


def _wrapped(names: tuple[str, ...]) -> str:
    """*names* as the lines of a YAML flow list, each item followed by a comma."""
    lines: list[str] = []
    line = _LIST_INDENT
    for name in names:
        item = f"{name}, "
        if len(line) + len(item.rstrip()) > _LINE_LIMIT and line.strip():
            lines.append(line.rstrip())
            line = _LIST_INDENT
        line += item
    lines.append(line.rstrip())
    return "".join(f"{text}\n" for text in lines)


def fsd_rules_text(frontend: str) -> str:
    """The ``rules.yml`` text :func:`generate_fsd_rules` writes for *frontend*."""
    slice_tags = ", ".join(f"fsd-{layer}" for layer in _SLICED_LAYERS)
    public_api_tags = ", ".join(f"fsd-{layer}" for layer in (*_SLICED_LAYERS, *_SEGMENTED_LAYERS))
    layer_lines = "".join(
        f"      - name: {layer}\n        tag: fsd-{layer}\n" for layer in FSD_LAYERS
    )
    width = max(len(rule) for rule, _ in STEIGER_RECOMMENDED) + len("fsd/")
    steiger_lines = "".join(
        f"#   {f'fsd/{rule}':<{width}}  {line}\n" for rule, line in STEIGER_RECOMMENDED
    )
    return "".join(
        (
            _FSD_HEADER.format(steiger_lines=steiger_lines),
            _FSD_LAYERS_RULE.format(
                layer_names=", ".join(FSD_LAYERS), frontend=frontend, layer_lines=layer_lines
            ),
            "\n",
            _FSD_PUBLIC_API_RULE.format(public_api_tags=public_api_tags),
            "\n",
            _FSD_SHAPE_RULE.format(
                slice_tags=slice_tags,
                segments=", ".join(DEFAULT_SLICE_SEGMENTS),
                discouraged=_wrapped(DEFAULT_DISCOURAGED_SEGMENTS),
            ),
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
    ``FSD architecture`` for the portal, ``slice_public_api`` over every layer,
    ``slice_shape`` with both its lists (BDL-082 S2a) and one cohesion ``check`` per
    layer but ``pages`` (:data:`FSD_COHESION_LIMITS`). Written as text, so
    the owner's reason for each rule stands beside it in the file an adopter edits.
    The count is read back from the text written, so it cannot drift from it.
    """
    text = fsd_rules_text(frontend)
    write_text_atomic(rules_path, text)
    return len(yaml.safe_load(text)["rules"])


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
