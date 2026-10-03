// The browser tests' own crossing finder: where drawn routes cross, written apart from the viewer's.
//
// A case that asked the viewer's crossing finder where the bridges belong would
// pass whatever it did. This one reads the routes the handle reports as drawn
// (`edgeRoutes`) and tests every pair of their segments, with no index and no
// assumption that a segment is horizontal or vertical: a pair of segments cross
// where each passes through the other at least `INSIDE` from its ends. A point
// where a route runs straight on is not a segment's end.
//
// The rule it checks is the viewer's stated one: a bridge on a highlighted edge
// at every crossing with another drawn edge, none with an edge of its own bundle
// and none with itself; at a crossing of two highlighted edges, one bridge, on
// the edge whose segment there is the more horizontal.

/** How far inside both segments a crossing lies at least, in layout units. */
export const INSIDE = 0.5;
/** How far apart two reported crossings may lie and be one, in layout units. */
const SAME_PLACE = 0.5;
/**
 * The sine of the angle below which two segments run along each other rather
 * than across: a route ELK made straight can drift a thousandth of a unit over a
 * few hundred, and two such segments on one line meet along it, not at a point.
 */
const PARALLEL = 1e-3;

const cross = (u, v) => u.x * v.y - u.y * v.x;
const minus = (p, q) => ({ x: p.x - q.x, y: p.y - q.y });
const lengthOf = (v) => Math.hypot(v.x, v.y);

/** `points` without a point repeated or one the line runs straight through. */
function cornersOf(points) {
  const kept = [];
  for (const point of points) {
    const last = kept[kept.length - 1];
    if (last && lengthOf(minus(point, last)) < 1e-9) continue;
    const before = kept[kept.length - 2];
    if (before) {
      const u = minus(last, before);
      const v = minus(point, last);
      const straight = Math.abs(cross(u, v)) <= 1e-9 * lengthOf(u) * lengthOf(v) && u.x * v.x + u.y * v.y > 0;
      if (straight) {
        kept[kept.length - 1] = point;
        continue;
      }
    }
    kept.push(point);
  }
  return kept;
}

/** The segments of a polyline, `[{ a, b }]`. */
function segmentsOf(points) {
  const corners = cornersOf(points);
  return corners.slice(1).map((b, i) => ({ a: corners[i], b }));
}

/** Where segments `s` and `t` cross, at least `INSIDE` inside both, or null. */
function crossingOf(s, t) {
  const u = minus(s.b, s.a);
  const v = minus(t.b, t.a);
  const [ls, lt] = [lengthOf(u), lengthOf(v)];
  const denominator = cross(u, v);
  if (Math.abs(denominator) <= PARALLEL * ls * lt) return null;
  const w = minus(t.a, s.a);
  const along = cross(w, v) / denominator;
  const across = cross(w, u) / denominator;
  const inside = (fraction, length) => fraction * length >= INSIDE && (1 - fraction) * length >= INSIDE;
  if (!inside(along, ls) || !inside(across, lt)) return null;
  return { x: s.a.x + along * u.x, y: s.a.y + along * u.y };
}

/** How horizontal a segment is: its run across over its run down. */
const flatness = ({ a, b }) => Math.abs(b.x - a.x) - Math.abs(b.y - a.y);

/** Each edge's bundle siblings from the handle's `bundles()`: id to a set of the ids it shares a trunk or a bus with. */
export function bundleSiblings({ trunks, buses }) {
  const siblings = new Map();
  for (const { members } of [...trunks, ...buses]) {
    for (const id of members) {
      const set = siblings.get(id) || new Set();
      members.filter((other) => other !== id).forEach((other) => set.add(other));
      siblings.set(id, set);
    }
  }
  return siblings;
}

/**
 * The bridges the rule asks for over `routes` (`[{ id, points }]`, the routed
 * edges drawn): `{ id: [{ x, y, crossed }] }`, an entry for every id in
 * `highlighted` that is drawn. `siblings` maps an id to its bundle siblings;
 * with `{ siblings: null }` crossings between siblings are kept, which is what a
 * case needs to know whether the graph has any.
 */
export function expectedBridges(routes, highlighted, siblings = new Map()) {
  const segments = new Map(routes.map(({ id, points }) => [id, segmentsOf(points)]));
  const answer = {};
  for (const id of highlighted) {
    if (!segments.has(id)) continue;
    answer[id] = [];
    for (const [other, theirs] of segments) {
      if (other === id || siblings?.get(id)?.has(other)) continue;
      for (const s of segments.get(id)) {
        for (const t of theirs) {
          const at = crossingOf(s, t);
          if (!at) continue;
          if (highlighted.has(other) && flatness(s) <= flatness(t)) continue;
          answer[id].push({ x: at.x, y: at.y, crossed: other });
        }
      }
    }
  }
  return answer;
}

/**
 * How the handle's `bridges()` differs from `expected` (`expectedBridges`):
 * `{ edges, missing, stray }`. `edges` lists the highlighted edges one names and
 * the other does not; `missing` the expected crossings not reported, `stray` the
 * reported ones not expected, each as `edge×crossed@x,y`.
 */
export function compareBridges(reported, expected) {
  const named = (list) => list.map((entry) => `${entry.edge}×${entry.crossed}@${entry.x.toFixed(1)},${entry.y.toFixed(1)}`);
  const reportedEdges = new Set(reported.map((entry) => entry.edge));
  const expectedEdges = new Set(Object.keys(expected));
  const edges = [...new Set([...reportedEdges, ...expectedEdges])].filter((id) => reportedEdges.has(id) !== expectedEdges.has(id)).sort();
  const missing = [];
  const stray = [];
  for (const { edge, crossings } of reported) {
    const left = [...(expected[edge] || [])];
    for (const crossing of crossings) {
      const match = left.findIndex(
        (other) => other.crossed === crossing.crossed && Math.hypot(other.x - crossing.x, other.y - crossing.y) <= SAME_PLACE
      );
      if (match >= 0) left.splice(match, 1);
      else stray.push({ edge, ...crossing });
    }
    missing.push(...left.map((crossing) => ({ edge, ...crossing })));
  }
  for (const edge of expectedEdges) {
    if (!reportedEdges.has(edge)) missing.push(...expected[edge].map((crossing) => ({ edge, ...crossing })));
  }
  return { edges, missing: named(missing), stray: named(stray) };
}
