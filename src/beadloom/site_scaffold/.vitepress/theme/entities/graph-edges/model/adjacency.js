// beadloom:component=site-graph-edges
// Which edges a walk follows, and each node's edges read as neighbours.
//
// A neighbourhood follows every kind drawn as a line, in the direction the
// arrow points. The impact walk goes from a node to what depends on it, and a
// table names, per edge kind it follows, the end that depends on the other
// (`dependentsOf`). In the architecture graph that is the source of
// `depends_on`, `uses` and `consumes`. `produces` points from the producer to
// what it produces, which is not a dependency of the producer, and the
// architecture's impact does not follow it; the landscape, whose every edge is
// a contract from a producer to a consumer, names its own table.

import { DRAWN_KINDS, EDGE_STYLES, isDrawnKind, isViolation } from "./edgeKinds.js";

/** The kinds a neighbourhood walks: every kind drawn as a line. */
export const NEIGHBOURHOOD_KINDS = DRAWN_KINDS;

/** The end of an edge that depends on the other, per kind: the source of each dependency kind. */
export const DEPENDENT_ENDS = Object.freeze({ depends_on: "src", uses: "src", consumes: "src" });

/** The kinds whose source depends on its target: what the architecture's impact walk follows. */
export const DEPENDENCY_KINDS = Object.freeze(Object.keys(DEPENDENT_ENDS));

/** The key of a drawn edge: its kind, source and target. Two contracts on one pair share it. */
export function edgeKeyOf(edge) {
  return `${edge.kind}:${edge.src}->${edge.dst}`;
}

function append(map, id, entry) {
  const list = map.get(id);
  if (list) list.push(entry);
  else map.set(id, [entry]);
}

/**
 * `{ out, in }`: for each node, its edges of `kinds` as `[{ id, key }]`.
 *
 * Only edges between two of `ids` count, and a loop from a node to itself
 * leads nowhere, so it is left out.
 */
export function adjacencyOf(edges, kinds, ids) {
  const wanted = new Set(kinds);
  const out = new Map();
  const into = new Map();
  for (const edge of edges) {
    if (!wanted.has(edge.kind) || edge.src === edge.dst) continue;
    if (!ids.has(edge.src) || !ids.has(edge.dst)) continue;
    const key = edgeKeyOf(edge);
    append(out, edge.src, { id: edge.dst, key });
    append(into, edge.dst, { id: edge.src, key });
  }
  return { out, in: into };
}

/**
 * For each node, what depends on it: `Map` of id to `[{ id, key }]`.
 *
 * `dependentEnds` names, per edge kind the walk follows, the end that depends
 * on the other (`src` or `dst`); an edge of another kind is left out. As in
 * `adjacencyOf`, only edges between two of `ids` count, and a loop is left out.
 */
export function dependentsOf(edges, dependentEnds, ids) {
  const dependents = new Map();
  for (const edge of edges) {
    if (!Object.hasOwn(dependentEnds, edge.kind) || edge.src === edge.dst) continue;
    const end = dependentEnds[edge.kind];
    if (!ids.has(edge.src) || !ids.has(edge.dst)) continue;
    const [dependent, dependency] = end === "src" ? [edge.src, edge.dst] : [edge.dst, edge.src];
    append(dependents, dependency, { id: dependent, key: edgeKeyOf(edge) });
  }
  return dependents;
}

/**
 * A node's drawn edges grouped by kind and direction, for its card.
 *
 * `[{ kind, direction, title, targets: [{ id, violation }] }]`, in the order
 * of `EDGE_STYLES` and outgoing before incoming; a group with no edge is left out.
 */
export function edgeGroupsOf(id, edges) {
  const groups = new Map();
  for (const edge of edges) {
    if (!isDrawnKind(edge.kind) || edge.src === edge.dst) continue;
    const direction = edge.src === id ? "out" : edge.dst === id ? "in" : null;
    if (!direction) continue;
    const other = direction === "out" ? edge.dst : edge.src;
    const key = `${edge.kind}:${direction}`;
    if (!groups.has(key)) groups.set(key, new Map());
    const targets = groups.get(key);
    targets.set(other, Boolean(targets.get(other)) || isViolation(edge));
  }
  const ordered = [];
  for (const kind of NEIGHBOURHOOD_KINDS) {
    for (const direction of ["out", "in"]) {
      const targets = groups.get(`${kind}:${direction}`);
      if (!targets) continue;
      const style = EDGE_STYLES[kind];
      ordered.push({
        kind,
        direction,
        title: direction === "out" ? style.outgoing : style.incoming,
        targets: [...targets].sort(([a], [b]) => a.localeCompare(b)).map(([other, violation]) => ({ id: other, violation })),
      });
    }
  }
  return ordered;
}
