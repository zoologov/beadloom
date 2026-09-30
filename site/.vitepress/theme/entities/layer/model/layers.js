// beadloom:component=site-layer
// The layers of the architecture graph, read from the data file, and their colours.
//
// No layer is named here. A version 1 data file gives each node its layer rank
// (`layer_rank`, inherited through `part_of`) and, on a node that declares one,
// the layer's name (`layer`). The layers are the ranks that occur, named by the
// nodes that declare them, so a project whose layers are called differently
// gets its own names. The colour of a layer is a theme tone chosen by its
// position in the order, top to bottom.

/** Theme tones for the layers, top to bottom; a longer order repeats them. */
export const LAYER_TONES = ["purple", "indigo", "green", "yellow", "red"];

/** The tone of a node in no layer. */
export const UNLAYERED_TONE = "gray";

/** The layers that occur, `[{ rank, name, tone }]`, top to bottom. */
export function layersOf(nodes) {
  const names = new Map();
  const ranks = new Set();
  for (const node of nodes) {
    if (typeof node.layer_rank !== "number") continue;
    ranks.add(node.layer_rank);
    if (node.layer && !names.has(node.layer_rank)) names.set(node.layer_rank, node.layer);
  }
  return [...ranks]
    .sort((a, b) => a - b)
    .map((rank, position) => ({
      rank,
      name: names.get(rank) || `rank ${rank}`,
      tone: LAYER_TONES[position % LAYER_TONES.length],
    }));
}

/** The layer a node is in, or null. */
export function layerOfNode(node, layers) {
  return layers.find((layer) => layer.rank === node.layer_rank) || null;
}

/** The theme tone of the node's layer. */
export function layerToneOf(node, layers) {
  return layerOfNode(node, layers)?.tone || UNLAYERED_TONE;
}
