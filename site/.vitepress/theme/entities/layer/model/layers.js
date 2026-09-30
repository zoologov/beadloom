// beadloom:component=site-layer
// The layers of the architecture graph, read from the data file, and their colours.
//
// No layer is named here. A version 2 data file declares the project's layers
// at its top level, `layers: [{ name, rank, tag, token }]`, top to bottom, and
// those are the layers the legend, the Layer filter and the card name. A file
// that declares none — version 1 — gives each node its layer rank
// (`layer_rank`, inherited through `part_of`) and, on a node that declares one,
// the layer's tag token (`layer`); the layers are then the ranks that occur,
// named by those tokens. The colour of a layer is a theme tone chosen by its
// position in the order, top to bottom.

/** Theme tones for the layers, top to bottom; a longer order repeats them. */
export const LAYER_TONES = ["purple", "indigo", "green", "yellow", "red"];

/** The tone of a node in no layer. */
export const UNLAYERED_TONE = "gray";

function toned(layers) {
  return layers
    .sort((a, b) => a.rank - b.rank)
    .map((layer, position) => ({ ...layer, tone: LAYER_TONES[position % LAYER_TONES.length] }));
}

/** The declared layers, `[{ rank, name }]`, or none when the file declares none. */
function declaredLayers(declared) {
  if (!Array.isArray(declared)) return [];
  return declared
    .filter((layer) => typeof layer?.rank === "number")
    .map((layer) => ({ rank: layer.rank, name: layer.name || layer.token || `rank ${layer.rank}` }));
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
  return [...ranks].map((rank) => ({ rank, name: names.get(rank) || `rank ${rank}` }));
}

/**
 * The layers, `[{ rank, name, tone }]`, top to bottom.
 *
 * `declared` is the data file's `layers`; when it names none, the layers are
 * read from the nodes' tokens instead.
 */
export function layersOf(nodes, declared) {
  const layers = declaredLayers(declared);
  return toned(layers.length ? layers : layersFromTokens(nodes));
}

/** The layer a node is in, or null. */
export function layerOfNode(node, layers) {
  return layers.find((layer) => layer.rank === node.layer_rank) || null;
}

/** The theme tone of the node's layer. */
export function layerToneOf(node, layers) {
  return layerOfNode(node, layers)?.tone || UNLAYERED_TONE;
}
