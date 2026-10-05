// beadloom:component=site-graph-node
// A node of the architecture data file, and what the viewer reads off it.
//
// Version 1's fields: `id`, `label`, `kind`, `summary`, `layer` (the node's own
// layer tag), `layer_rank` (its layer, inherited through `part_of`), `parent`,
// `doc_status`, `lint_clean` and the dependency lists. Version 2's card fields
// are read for the risk a change runs: `tests`, `docs` and `findings`, and the
// findings' severities for the node's status. A field a version 1 file does not
// carry is no risk, because nothing says it is one.

import { idRecord } from "../../../shared/ids/index.js";

/** The severity of a finding that breaks a rule; every other severity warns. */
const ERROR_SEVERITY = "error";

/**
 * The statuses a node is drawn with, most severe first: its theme tone, the
 * mark it puts in the node's corner — `filled`, or a `ring` — and the legend's
 * words. A status never changes the node's border, which is its layer's. Only an
 * error finding is a violation; a node with warn findings only is drawn in a
 * look of its own, a ring, apart from the filled marks of what needs fixing.
 */
export const NODE_STATUSES = Object.freeze({
  violation: Object.freeze({ tone: "danger", mark: "filled", legend: "rule violation (error)" }),
  stale: Object.freeze({ tone: "warning", mark: "filled", legend: "stale docs" }),
  warned: Object.freeze({ tone: "warning", mark: "ring", legend: "rule warning" }),
});

/**
 * The node's status, or null: an error finding, then stale docs, then any other finding.
 *
 * A version 1 file carries no findings, only `lint_clean`, and cannot tell an
 * error from a warning; a node it marks not clean is drawn as a violation.
 */
export function statusOf(node) {
  const findings = Array.isArray(node.findings) ? node.findings : null;
  if (findings ? findings.some((f) => f.severity === ERROR_SEVERITY) : node.lint_clean === false) {
    return "violation";
  }
  if (node.doc_status === "stale") return "stale";
  if (findings?.length) return "warned";
  return null;
}

/** The statuses the nodes are drawn with, in the order of `NODE_STATUSES`. */
export function statusesOf(nodes) {
  const present = new Set(nodes.map(statusOf));
  return Object.keys(NODE_STATUSES).filter((status) => present.has(status));
}

export function isFlagged(node) {
  return statusOf(node) !== null;
}

/**
 * Each node's container, `{ id: parentId | null }`, a record without a prototype
 * (`idRecord`), so a node named `__proto__` or `constructor` is a key like any other.
 *
 * A parent that is not itself a node of the file, or a node that names itself
 * (the root service is `part_of` itself), has none: Cytoscape rejects a dangling
 * or self parent, and a walk over it would never end.
 */
export function parentMapOf(nodes) {
  const ids = new Set(nodes.map((n) => n.id));
  const parents = idRecord();
  for (const n of nodes) {
    parents[n.id] = n.parent && n.parent !== n.id && ids.has(n.parent) ? n.parent : null;
  }
  return parents;
}

/** The risks a node carries for a change, as the phrases the viewer shows. */
export const RISKS = Object.freeze({
  untested: "no bound tests",
  staleDocs: "stale docs",
  uncheckedDocs: "docs not checked",
  findings: "open findings",
});

/** A doc's sync status that is no risk. */
const DOC_OK = "ok";
/** A doc's sync status that was compared and found out of date. */
const DOC_STALE = "stale";

/**
 * Why a change to this node is risky: no bound tests, stale docs, docs nothing
 * could check, open rule findings.
 *
 * A doc is stale when its pairs were compared and found out of date. Any other
 * status but `ok` — `unpaired`, `unverified`, `missing` — means nothing could be
 * compared, which the sync engine does not report as stale, and neither does
 * this. A version 1 file lists no docs, and its aggregate `doc_status` is read.
 */
export function risksOf(node) {
  const risks = [];
  if (node.tests && node.tests.count === 0) risks.push(RISKS.untested);
  const statuses = Array.isArray(node.docs) ? node.docs.map((doc) => doc.status) : [];
  const stale = Array.isArray(node.docs)
    ? statuses.includes(DOC_STALE)
    : node.doc_status === DOC_STALE;
  if (stale) risks.push(RISKS.staleDocs);
  if (statuses.some((status) => status !== DOC_OK && status !== DOC_STALE)) {
    risks.push(RISKS.uncheckedDocs);
  }
  if ((node.findings || []).length) risks.push(RISKS.findings);
  return risks;
}

/** The node's nearest container of `kind`, the node itself included, or null. */
export function containerOfKind(id, kind, nodeById, parents) {
  for (let cursor = id; cursor; cursor = parents[cursor]) {
    if (nodeById.get(cursor)?.kind === kind) return cursor;
  }
  return null;
}
