// beadloom:component=site-shared-map-levels
// The sizes a node is drawn at, in layout units: a card's and a box's, their borders, and what a node's data says it is drawn as.
//
// The stylesheet draws a node at these sizes (`widgets/graph-viewer/lib/stylesheet.js`),
// the layout keeps an open box's title room by them (`shared/elk`, `boxTop`), and the
// map's titles, pills and corners measure a node by them, so each reads one number.

import { COLLAPSED, PROJECT_BOX } from "./levels.js";
import { MAP_BOX } from "./mapMarks.js";

/**
 * A node's sizes, in layout units. `outerWidth` and `outerHeight` are a leaf's
 * size with its border, the size the layout places it by, and the same whatever
 * its status: a status is a mark inside the card, so a finding moves no node.
 */
export const GEOMETRY = Object.freeze({
  outerWidth: 163,
  outerHeight: 47,
  /** A node's title size, in layout units. */
  nodeTitle: 12,
  cardBorder: 1.5,
  boxBorder: 1,
  selectedBorder: 3,
  riskOutlineWidth: 4,
  /** A status mark's side, and how far it sits in from the card's top right corner. */
  statusMark: 10,
  statusMarkInset: 6,
  /** How far an open box's title sits below its top border. */
  boxTitleInset: 20,
  /**
   * The room an open box keeps above its children for its title: the title,
   * drawn `boxTitleInset` in, ends about 22.5 below the border, and the children
   * keep about the 12 ELK keeps from a border below it (`shared/elk`, `boxTop`).
   */
  boxTitleRoom: 36,
});

/** The border a node of the map is drawn with at rest: a closed box's, or a card's. */
const borderOf = (node) => (node.hasClass(COLLAPSED) ? GEOMETRY.boxBorder : GEOMETRY.cardBorder);

/**
 * The size `node`'s shape is drawn at, in layout units, `{ width, height }`, read
 * from its data as the stylesheet sizes it: the box the map draws it as, its
 * border taken off; ELK's box; or a card's. Read from the data rather than from
 * Cytoscape, whose sizes trail a change of the data made in the same batch.
 */
export function drawnSizeOf(node) {
  const grown = node.data(MAP_BOX);
  if (grown) return { width: grown.width - borderOf(node), height: grown.height - borderOf(node) };
  const box = node.data("box");
  if (box) return { width: box.width, height: box.height };
  return { width: GEOMETRY.outerWidth - GEOMETRY.cardBorder, height: GEOMETRY.outerHeight - GEOMETRY.cardBorder };
}

/** How far `node`'s border reaches outside its shape at rest, in layout units: half of it, drawn on its edge; none of the project's frame, drawn inside. */
export function rimOf(node) {
  if (node.hasClass(PROJECT_BOX)) return 0;
  return (node.isParent() || node.hasClass(COLLAPSED) ? GEOMETRY.boxBorder : GEOMETRY.cardBorder) / 2;
}
