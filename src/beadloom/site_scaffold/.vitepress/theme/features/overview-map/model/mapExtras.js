// beadloom:component=site-overview-map
// What the map draws beyond the level at rest for the pointer, a selection and the test handle: own lines, edges drawn as themselves, stubs and walk counts.
//
// A node inside an open box carries the count of its outward edges, the ones a
// box that holds it carries at rest (`shared/map-levels/levels.js`, `OUTWARD`), drawn as "+N"
// over the canvas (`features/edge-pills/model/pillOverlay.js`). While it is under the pointer or selected,
// they are drawn: each as itself, on its route, where both its ends are drawn at
// their laid-out size, an open box among them; otherwise one **own line** from
// the node to each node the other ends are drawn as, along the medoid of their
// drawn routes (`aggregateElements.js`). A line of a box whose every edge is then
// drawn by such lines is not drawn twice, and a line into an open box that the
// node's other lines run on into is their stub, with no head of its own
// (`STUB_AT`). A selection's walk draws its edges as themselves wherever both
// their ends can take one. The walk's edges of the selected node itself are its
// own lines, the lines the pointer on it draws: a click and a hover draw the same
// lines. A box selected open draws its own outward edges the same way
// (`shared/map-levels/levels.js`, `outwardOfOpen`).
//
// Each source — the pointer, the selection, the test handle — names the nodes it
// exposes (`expose`); a selection names its walk (`setWalk`). What they draw is
// worked out at each drawing of the map from those and the level drawn then.

import { OUTWARD, holdersOf, isWithinAny, outwardOfOpen, ownLinesOf } from "../../../shared/map-levels/index.js";
import { isOwnLine, weigh } from "./aggregateElements.js";

/** The source of a reveal that opens its boxes at any zoom, and draws every edge of its nodes: the test handle's. */
export const FORCED = "test";

/**
 * What the sources over `cy` ask the map to draw beyond the level at rest, in
 * the box tree `tree`; `edges` the file's edges by id (Cytoscape's),
 * `plainEdges` and `edgeById` as plain `{ id, source, target }`, `byKey` an
 * edge's id by its key: `{ expose, setWalk, walkKeys, extrasOf, fullDetailOf,
 * saidOf }`.
 */
export function mapExtras(cy, { tree, edges, plainEdges, edgeById, byKey }) {
  const exposures = new Map();
  // The sources whose open boxes draw their own outward edges: a selected box's, not the pointer's.
  const exposingOpen = new Set();
  let walkKeys = null;
  // The node or box the walk was taken from: its own edges are its own lines, not the walk's.
  let walkFocus = null;

  /** Whether the drawing changes when `before` and `after`, two lists of node ids, swap as exposed. */
  const exposesOther = (before, after) => {
    const outward = (ids) => ids.some((id) => cy.getElementById(id).data(OUTWARD) > 0);
    return JSON.stringify(before) !== JSON.stringify(after) && (outward(before) || outward(after));
  };

  /**
   * Draw the outward edges of each node of `ids` for `source` (the pointer,
   * the selection, the test handle); an empty list takes them back. With
   * `openBoxes`, an open box of `ids` draws its own too, as a selected box
   * does; the pointer resting inside an open box draws nothing for it. True
   * when the drawing changes.
   */
  function expose(source, ids, { openBoxes = false } = {}) {
    const before = exposures.get(source) || [];
    const after = [...new Set(ids || [])];
    exposures.set(source, after);
    if (openBoxes) exposingOpen.add(source);
    else exposingOpen.delete(source);
    return exposesOther(before, after);
  }

  /**
   * Draw the edges whose keys are in `keys`, a selection's walk from `focus`,
   * as themselves where both their ends can take one, and have every line that
   * carries some say how many; null for none. The edges of `focus` itself, or
   * of everything in it when it is a box, are its own lines (`expose`).
   */
  function setWalk(keys, focus = null) {
    walkKeys = keys ? new Set(keys) : null;
    walkFocus = keys ? focus : null;
  }

  /**
   * The lines among `originals` and `own` that end at an open box whose nodes
   * their node's other lines run on into: each a stub of those lines, under the
   * bus that spreads them in the box, its head theirs. `Map(id or pair name =>
   * the box)`.
   */
  function stubsOf(originals, own, openNow) {
    const reached = new Map();
    const note = (node, end) => reached.set(node, [...(reached.get(node) || []), end]);
    const endsOf = [...[...originals].map((id) => [id, [edgeById.get(id).source, edgeById.get(id).target]]), ...own.map((pair) => [pair.name, pair.ends])];
    for (const [, [a, b]] of endsOf) {
      note(a, b);
      note(b, a);
    }
    const stubs = new Map();
    for (const [key, ends] of endsOf) {
      const box = ends.find((end) => tree.boxes.has(end) && openNow.has(end));
      const node = ends.find((end) => end !== box);
      if (box && (reached.get(node) || []).some((end) => end !== box && holdersOf(tree, end).includes(box))) stubs.set(key, box);
    }
    return stubs;
  }

  /**
   * What the exposed nodes and the walk draw besides the level at rest, with
   * the boxes `openNow` open, the outward edges of the level `outward` and the
   * nodes drawn larger than their layout `grownNow`: `{ originals, own, stubs }`,
   * the edges drawn as themselves, the own lines, each weighed by the edges
   * `kept` shows, and the end each line that is a stub draws no head at
   * (`STUB_AT`), by its id or its pair's name.
   */
  function extrasOf(level, openNow, outward, kept, grownNow) {
    const exposed = new Set();
    // An open box exposed draws its own outward edges, which its nodes carry at rest.
    const ofOpen = new Map(outward);
    for (const [source, ids] of exposures) {
      for (const id of ids) {
        if (!level.nodes.has(id) || id === tree.wrapper) continue;
        const isOpen = tree.boxes.has(id) && openNow.has(id);
        if (isOpen && !exposingOpen.has(source)) continue;
        exposed.add(id);
        if (isOpen) ofOpen.set(id, outwardOfOpen(tree, id, plainEdges.filter((edge) => kept(edge.id)), level));
      }
    }
    // An end takes an edge drawn as itself when it is drawn at its laid-out size: a leaf, or an open box, on its route.
    const asItself = (id) => level.nodes.has(id) && !(tree.boxes.has(id) && !openNow.has(id)) && !grownNow.has(id);
    const lines = ownLinesOf(tree, openNow, edgeById, ofOpen, exposed, asItself);
    const originals = new Set(lines.originals);
    for (const id of level.originals) originals.delete(id);
    const own = [...lines.pairs.values()].map((pair) => weigh(pair, kept)).filter((pair) => pair.weight > 0);
    return { originals, own, stubs: stubsOf(originals, own, openNow) };
  }

  /**
   * The edges drawn as themselves besides the level at rest by the test handle
   * and by a selection's walk: every edge with an end at a node the handle
   * reveals with its edges, both of whose ends are drawn and neither of them a
   * closed box — the whole graph at full detail, every edge on its route, when
   * it reveals every node — and every edge of the walk whose ends are so drawn.
   * An edge the filters hide is drawn and marked hidden, as at rest.
   */
  function fullDetailOf(level, openNow) {
    const forced = new Set(exposures.get(FORCED) || []);
    const takes = (id) => level.nodes.has(id) && !(tree.boxes.has(id) && !openNow.has(id));
    const rest = new Set(level.originals);
    const full = forced.size
      ? plainEdges.filter((edge) => !rest.has(edge.id) && (forced.has(edge.source) || forced.has(edge.target)) && takes(edge.source) && takes(edge.target))
      : [];
    // A selection's walk draws its edges as themselves wherever both their ends are drawn, a box open: a
    // node drawn larger than its layout is then drawn at its laid-out size, as the selection frames it.
    // The edges of the selected node itself are its own lines, as the pointer on it draws them.
    const walked = walkKeys ? [...walkKeys].map((key) => edgeById.get(byKey.get(key))).filter(Boolean) : [];
    const focus = new Set(walkFocus === null ? [] : [walkFocus]);
    const walk = walked.filter((edge) => !rest.has(edge.id) && !isWithinAny(tree, edge.source, focus) && !isWithinAny(tree, edge.target, focus) && takes(edge.source) && takes(edge.target));
    return [...new Set([...full, ...walk].map((edge) => edge.id))];
  }

  /**
   * What `pair` says while a selection's walk is marked and it carries edges of
   * the walk no other line draws (`drawnElsewhere`): how many each way,
   * `{ forward, backward }`; otherwise null, and it says all it carries. A
   * node's own line says its own.
   */
  function saidOf(pair, drawnElsewhere) {
    if (!walkKeys) return null;
    const own = isOwnLine(pair);
    const walkedOf = (ids) => ids.filter((id) => walkKeys.has(edges.get(id).data("key")) && (own || !drawnElsewhere.has(id))).length;
    const said = { forward: walkedOf(pair.forward), backward: walkedOf(pair.backward) };
    return said.forward + said.backward ? said : null;
  }

  return { expose, setWalk, walkKeys: () => walkKeys, extrasOf, fullDetailOf, saidOf };
}
