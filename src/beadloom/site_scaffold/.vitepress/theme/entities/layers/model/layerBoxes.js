// beadloom:component=site-layers
// The boxes a layer rule scoped to a box draws inside it: one per layer, derived from the rule.
//
// A Feature-Sliced frontend is a service whose slices sit in six layers. Drawn as
// the graph declares it, its box holds every slice side by side, and a frontend
// of eighty slices is eighty boxes at one level. A rule whose scope is a box
// inside the project's frame therefore draws one box per layer inside its scope
// (owner, 2026-10-08): each holds the scope's own parts that the rule places in
// that layer, and the boxes open by readability like any box. A layer box is no
// node of the graph — no `part_of` edge names it and the data file does not list
// it — so it has no card, no filter value and no page; it is where the drawing
// puts the parts of one layer.
//
// A rule scoped to the frame itself, the one root that holds everything, draws
// no box: its layers are the frame's lanes, as they always were, and boxes there
// would turn the overview of the whole project into a map of its layers. A part
// the scope holds that its rule does not place — in no layer, or placed by
// another rule — stays where it is, directly in the scope.

import { freshId, idRecord } from "../../../shared/ids/index.js";
import { layerOfNode } from "./layers.js";

/** The id a layer's box is given, where no node of the file and no box before it has the id. */
const LAYER_BOX_ID = (rule, layer) => `layer:${rule}/${layer}`;

/** The one root that holds everything, when the containment `parents` has one: the project's frame. */
function frameOf(parents) {
  const ids = Object.keys(parents);
  const holders = new Set(Object.values(parents).filter(Boolean));
  const roots = ids.filter((id) => !parents[id]);
  return roots.length === 1 && holders.has(roots[0]) ? roots[0] : null;
}

/**
 * The boxes the scoped rules draw and the containment they are drawn in:
 * `{ boxes, parents }`.
 *
 * `boxes` are `[{ id, label, rule, rank, tone, scope }]`, one per layer that
 * holds a part of its rule's scope, in the layers' order; `parents` is
 * `parents`, each node's box, with each such part moved into its layer's box and
 * each layer box in its scope — the containment the canvas draws. `rules` is the
 * data file's `layer_rules`, `layers` the layers `layersOf` read from it.
 */
export function layerBoxesOf(nodes, parents, layers, rules) {
  const frame = frameOf(parents);
  const holders = new Set(Object.values(parents).filter(Boolean));
  const scopes = new Map(
    (Array.isArray(rules) ? rules : [])
      .filter((rule) => rule?.scope && rule.scope !== frame && holders.has(rule.scope))
      .map((rule) => [rule.name, rule.scope])
  );
  if (!scopes.size) return { boxes: [], parents };
  const taken = new Set(nodes.map((node) => node.id));
  const boxOfLayer = new Map();
  const drawn = idRecord(Object.entries(parents));
  for (const node of nodes) {
    const layer = layerOfNode(node, layers);
    if (!layer || scopes.get(layer.rule) !== parents[node.id]) continue;
    if (!boxOfLayer.has(layer)) {
      const id = freshId(LAYER_BOX_ID(layer.rule, layer.name), taken);
      taken.add(id);
      boxOfLayer.set(layer, id);
    }
    drawn[node.id] = boxOfLayer.get(layer);
  }
  const boxes = layers
    .filter((layer) => boxOfLayer.has(layer))
    .map((layer) => ({
      id: boxOfLayer.get(layer),
      label: layer.name,
      rule: layer.rule,
      rank: layer.rank,
      tone: layer.tone,
      scope: scopes.get(layer.rule),
    }));
  for (const box of boxes) drawn[box.id] = box.scope;
  return { boxes, parents: drawn };
}
