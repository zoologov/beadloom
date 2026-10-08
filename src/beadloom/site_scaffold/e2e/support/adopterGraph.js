// An architecture data file of an adopter's size, made from the served one's declarations.
//
// A case about how the viewer behaves on a large graph cannot wait for a large
// project: the portal under test may draw a hundred nodes where an adopter's
// service landscape draws several times that. `adopterSizedGraph` keeps the
// served file's schema version and declared layers and replaces its nodes and
// edges with a seeded graph of about 450 nodes and 1,300 drawn edges, shaped like
// a real one: a root box holding boxes per layer, a few boxes nested one level
// deeper, edges mostly down the layers, about four in ten inside one box, and a
// few hubs. The same seed gives the same file, so a case reads the same graph on
// every run. Every name in it is made up here.
//
// The layout pins each box to its layer rank, so the graph's shape depends on
// how many ranks the served file declares, and a portal's ranks are its
// project's. `layerRanks` asks for a graph of a given number of ranks instead,
// whatever the served file declares: the same boxes, nodes and edges, laid out
// in that many ranks.

import { withoutLayerRules } from "./layers.js";

/**
 * The tag of every case that runs on this graph rather than on the portal's own.
 * The graph takes nothing from the served file but its schema and its declared
 * layer ranks, so such a case does the same work on every portal that declares
 * the same ranks. A run that has already checked these cases on such a portal can
 * leave them out by setting `NO_ADOPTER_SIZED` to 1 (`playwright.config.js`).
 */
export const ADOPTER_SIZED = "@adopter-sized";

/** The environment variable that leaves out every case tagged `ADOPTER_SIZED`. */
export const NO_ADOPTER_SIZED = "BEADLOOM_E2E_NO_ADOPTER_SIZED";

/** The graph's size: boxes per layer position (and unlayered), and drawn edges. */
const BOXES_PER_RANK = [4, 6, 18, 5];
/**
 * How many layer positions the boxes take: a graph of more ranks than this is
 * laid out as one of this many, since its further ranks hold no box.
 */
export const RANK_POSITIONS = BOXES_PER_RANK.length;
const UNLAYERED_BOXES = 3;
const LEAVES_PER_BOX = [8, 14];
const DRAWN_EDGES = 1300;
const NESTED_BOXES = 4;
const HUBS = 6;
const SEED = 76;

/** A seeded generator of numbers in [0, 1) (mulberry32), so the graph is the same on every run. */
function seeded(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function nodeOf(id, kind, rank, parent) {
  return {
    id,
    label: id,
    kind,
    ...(typeof rank === "number" ? { layer_rank: rank } : {}),
    parent: parent || id,
    findings: [],
    doc_status: "fresh",
    lint_clean: true,
  };
}

/** The boxes and leaves: `{ nodes, parent, rank, leaves }`. */
function nodesOf(ranks, random) {
  const between = ([low, high]) => low + Math.floor(random() * (high - low + 1));
  const nodes = [nodeOf("root", "service", null, null)];
  const parent = { root: null };
  const rank = { root: null };
  const add = (id, kind, layerRank, parentId) => {
    nodes.push(nodeOf(id, kind, layerRank, parentId));
    parent[id] = parentId;
    rank[id] = layerRank;
  };
  const plan = BOXES_PER_RANK.map((count, index) => [ranks[index % ranks.length] ?? null, count]);
  plan.push([null, UNLAYERED_BOXES]);
  const boxes = [];
  plan.forEach(([layerRank, count], position) => {
    for (let b = 0; b < count; b += 1) {
      const box = `box${position}-${b}`;
      add(box, "domain", layerRank, "root");
      boxes.push(box);
      const leaves = between(LEAVES_PER_BOX);
      for (let k = 0; k < leaves; k += 1) add(`${box}-n${k}`, k % 2 ? "feature" : "component", layerRank, box);
    }
  });
  for (const box of boxes.slice(0, NESTED_BOXES)) {
    const nested = `${box}-sub`;
    add(nested, "feature", rank[box], box);
    for (let k = 0; k < 2; k += 1) add(`${nested}-n${k}`, "component", rank[box], nested);
  }
  const containers = new Set(Object.values(parent).filter(Boolean));
  const leaves = nodes.map((n) => n.id).filter((id) => id !== "root" && !containers.has(id));
  return { nodes, parent, rank, leaves };
}

function ancestorsOf(id, parent) {
  const out = [];
  for (let cursor = parent[id]; cursor; cursor = parent[cursor]) out.push(cursor);
  return out;
}

/** The drawn edges: mostly down the layers, some inside one box, a few hubs with many. */
function edgesOf({ nodes, parent, rank, leaves }, random) {
  const ids = nodes.map((n) => n.id).filter((id) => id !== "root");
  const weight = Object.fromEntries(ids.map((id) => [id, 1 / (1 + random() * 30) ** 1.6]));
  for (let h = 0; h < HUBS; h += 1) weight[leaves[Math.floor(random() * leaves.length)]] *= 25;
  const pick = (pool) => {
    let r = random() * pool.reduce((sum, id) => sum + weight[id], 0);
    for (const id of pool) if ((r -= weight[id]) <= 0) return id;
    return pool[pool.length - 1];
  };
  const downward = (a, b) => rank[a] === null || rank[b] === null || rank[a] <= rank[b];
  const edges = new Map();
  while (edges.size < DRAWN_EDGES) {
    const src = pick(leaves);
    const sameBox = random() < 0.4;
    const pool = ids.filter(
      (id) => id !== src && (!sameBox || parent[id] === parent[src]) && downward(src, id)
    );
    if (!pool.length) continue;
    const dst = pick(pool);
    if (ancestorsOf(dst, parent).includes(src)) continue;
    edges.set(`${src}->${dst}`, { src, dst, kind: random() < 0.05 ? "uses" : "depends_on" });
  }
  return [...edges.values()];
}

/** The layers of a graph of `count` ranks, 0 to `count - 1`, each named after its rank. */
const layersOfRanks = (count) => Array.from({ length: count }, (_, rank) => ({ name: `rank ${rank}`, rank }));

/**
 * `served` with its nodes and edges replaced by an adopter-sized graph, its
 * boxes in the served file's layer ranks, or in `layerRanks` ranks when given
 * (0 for none), with the served layers replaced to match.
 */
export function adopterSizedGraph(served, { layerRanks } = {}) {
  const random = seeded(SEED);
  const layers =
    typeof layerRanks === "number" ? layersOfRanks(layerRanks) : Array.isArray(served.layers) ? served.layers : [];
  const ranks = layers.map((layer) => layer.rank).filter((value) => typeof value === "number");
  const tree = nodesOf(ranks, random);
  const containment = tree.nodes.map((n) => ({ src: n.id, dst: n.parent, kind: "part_of" }));
  // Its nodes are in one order of ranks, as a file that names one order without a rule says:
  // the served file's every-rule keys would place none of them.
  const graph = { ...withoutLayerRules(served), nodes: tree.nodes, edges: [...containment, ...edgesOf(tree, random)] };
  return typeof layerRanks === "number" ? { ...graph, layers } : graph;
}
