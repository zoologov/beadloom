// beadloom:component=site-layer
// The layers of the architecture graph, read from the data file, and their colours.
//
// No layer is named here. A data file that carries every layer rule — `layer_rules:
// [{ name, scope, edge_kind, layers: [{ name, rank, tag, token }] }]`, and on each
// node the rule that places it, `layer_rule`, at `layer_rule_rank` — names the
// layers of each rule, and a layer is the pair (rule, rank): a project with a
// backend and a frontend has two orders, and rank 2 of one is no layer of the
// other. A file without them — schema 2 before every rule was written, or version
// 1 — names one order: its declared `layers: [{ name, rank, tag, token }]`, else
// the ranks the nodes are in (`layer_rank`, inherited through `part_of`), named
// by the tag token a node of that rank declares (`layer`). Such a file is drawn
// as it always was.
//
// The colour of a layer is a theme tone chosen by its position in its own rule,
// top to bottom, so each rule's layers are told apart from each other and the
// legend, grouped per rule, says which rule a tone belongs to. Every node is drawn
// as the legend draws its layer, whether it holds other nodes or not: a border in
// the tone over a tint of it (`LAYER_FILL_SHARE`). A node in no layer is drawn the
// same way in a neutral tone of its own, and the legend names it where the graph
// has one.

/**
 * Theme tones for the layers, top to bottom; a longer order repeats them. Six,
 * so the six layers of Feature-Sliced Design each have one. The sixth is the
 * portal's own cyan (`shared/theme-tokens/tones.css`): VitePress's brand colour
 * is its indigo unless a project sets it, so a sixth tone of "brand" would tell
 * the second layer and the sixth apart by nothing. Each keeps WCAG's 3:1 for a
 * boundary against what it is drawn on in both themes.
 */
export const LAYER_TONES = ["purple", "indigo", "green", "yellow", "red", "cyan"];

/**
 * The tone of a node in no layer: the secondary text colour, a neutral that
 * keeps WCAG's 3:1 for a boundary against the canvas in both themes, as every
 * layer's tone does. The theme's grey, which it was, is a fill tone: 1.33:1 on
 * the light canvas and 2.38:1 on the dark one, so such a node read as background.
 */
export const UNLAYERED_TONE = "text2";

/** What the legend calls a node in no layer, beside the layers' names. */
export const UNLAYERED_NAME = "no layer";

/** How much of its layer's tone a node's fill shows over what it is drawn on, in the legend as on the canvas. */
export const LAYER_FILL_SHARE = 0.16;

/** What joins a rule's name and a layer's name where a name must say which rule it belongs to. */
export const RULE_SEPARATOR = ": ";

/**
 * `layers` of one order, `[{ rank, name, tag }]`, top to bottom, each with its
 * tone by position and its key: the rule's name and the rank, so two orders'
 * ranks are never one layer.
 */
function toned(layers, rule) {
  return [...layers]
    .sort((a, b) => a.rank - b.rank)
    .map((layer, position) => ({
      ...layer,
      rule,
      key: `${rule ?? ""}\u0000${layer.rank}`,
      tone: LAYER_TONES[position % LAYER_TONES.length],
    }));
}

/** The layers a declaration lists, `[{ rank, name, tag }]`, or none. */
function declaredLayers(declared) {
  if (!Array.isArray(declared)) return [];
  return declared
    .filter((layer) => typeof layer?.rank === "number")
    .map((layer) => ({ rank: layer.rank, name: layer.name || layer.token || `rank ${layer.rank}`, tag: layer.tag || "" }));
}

/** The ranks the nodes are in, named by the token a node of that rank declares. */
function layersFromTokens(nodes) {
  const names = new Map();
  const ranks = new Set();
  for (const node of nodes) {
    if (typeof node.layer_rank !== "number") continue;
    ranks.add(node.layer_rank);
    if (node.layer && !names.has(node.layer_rank)) names.set(node.layer_rank, node.layer);
  }
  return [...ranks].map((rank) => ({ rank, name: names.get(rank) || `rank ${rank}`, tag: "" }));
}

/** The layer rules the file declares, in its order, each with a name and at least one layer. */
export function declaredRulesOf(rules) {
  if (!Array.isArray(rules)) return [];
  return rules.filter((rule) => typeof rule?.name === "string" && rule.name && declaredLayers(rule.layers).length);
}

/**
 * The layers, `[{ key, rule, rank, name, label, tag, tone }]`: every rule's,
 * the rules in the file's order and each one's top to bottom.
 *
 * `rules` is the data file's `layer_rules`; when it names none, `declared`, its
 * `layers`, is the one order, `rule` null, and when that names none either the
 * layers are read from the nodes' tokens. `label` is the name a filter and a
 * page show: the layer's own name, said with its rule's (`RULE_SEPARATOR`)
 * where more than one rule is drawn and two rules may name a layer alike.
 */
export function layersOf(nodes, declared, rules) {
  const ruled = declaredRulesOf(rules);
  if (ruled.length) {
    const qualified = ruled.length > 1;
    return ruled.flatMap((rule) =>
      toned(declaredLayers(rule.layers), rule.name).map((layer) => ({
        ...layer,
        label: qualified ? `${rule.name}${RULE_SEPARATOR}${layer.name}` : layer.name,
      }))
    );
  }
  const layers = declaredLayers(declared);
  return toned(layers.length ? layers : layersFromTokens(nodes), null).map((layer) => ({ ...layer, label: layer.name }));
}

/**
 * The rules the layers belong to, `[{ rule, layers }]`, in the layers' order: one
 * entry, `rule` null, for a file that names one order without a rule.
 */
export function layerRulesOf(layers) {
  const groups = new Map();
  for (const layer of layers) {
    if (!groups.has(layer.rule)) groups.set(layer.rule, []);
    groups.get(layer.rule).push(layer);
  }
  return [...groups].map(([rule, members]) => ({ rule, layers: members }));
}

/** Whether `layers` are each a rule's, read off a node's own rule, rather than one order read off its rank. */
const byRule = (layers) => layers.length > 0 && layers[0].rule !== null;

/**
 * The layer a node is in, or null: the layer of the rule that places it, at the
 * rank it places it, where the layers are a rule's; else the layer of its rank.
 */
export function layerOfNode(node, layers) {
  if (byRule(layers)) {
    return layers.find((layer) => layer.rule === node.layer_rule && layer.rank === node.layer_rule_rank) || null;
  }
  return layers.find((layer) => layer.rank === node.layer_rank) || null;
}

/**
 * Whether the node carries its layer's tag itself, rather than inheriting the
 * layer through `part_of`; false for a node in no layer.
 */
export function ownsLayer(node, layers) {
  const layer = layerOfNode(node, layers);
  if (!layer) return false;
  if (layer.tag && Array.isArray(node.tags)) return node.tags.includes(layer.tag);
  return Boolean(node.layer);
}

/** Whether any of `nodes` is in none of `layers`, and so drawn in `UNLAYERED_TONE`. */
export function hasUnlayeredNode(nodes, layers) {
  return nodes.some((node) => !layerOfNode(node, layers));
}

/** The theme tone of the node's layer. */
export function layerToneOf(node, layers) {
  return layerOfNode(node, layers)?.tone || UNLAYERED_TONE;
}
