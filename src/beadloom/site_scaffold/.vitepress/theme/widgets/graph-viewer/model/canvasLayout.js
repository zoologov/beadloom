// beadloom:component=site-graph-viewer
// The canvas's side of the ELK layout: what it hands ELK, and the positions it takes back.
//
// ELK is told what Cytoscape would draw: each node's place in the containment
// tree, the size Cytoscape gives it and where it stands now, each edge's ends, and
// the canvas's proportions. The answer places every leaf at the centre of its
// ELK box through a `preset` layout; a box follows its children, as Cytoscape
// draws compound nodes.

/** Node sizes as Cytoscape lays them out: the shape, without the label. */
const LAYOUT_DIMENSIONS = Object.freeze({ nodeDimensionsIncludeLabels: false });

/** What ELK needs of the canvas `cy` (`shared/elk`, `elkGraphOf`). */
export function layoutInputOf(cy) {
  const nodes = cy.nodes().map((node) => {
    const { w, h } = node.layoutDimensions(LAYOUT_DIMENSIONS);
    const { x, y } = node.position();
    return {
      id: node.id(),
      parent: node.isChild() ? node.parent().id() : null,
      width: w,
      height: h,
      x: x - w / 2,
      y: y - h / 2,
      partition: node.data("partition"),
    };
  });
  const edges = cy.edges().map((edge) => ({
    id: edge.id(),
    source: edge.data("source"),
    target: edge.data("target"),
  }));
  return { nodes, edges, aspectRatio: cy.height() ? cy.width() / cy.height() : 1 };
}

/** Place every leaf of `cy` at the centre of its box in `geometry`; resolves when it is placed. */
export function applyGeometry(cy, geometry) {
  const centreOf = (node) => {
    const box = geometry.boxes[node.id()];
    return box ? { x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 } : undefined;
  };
  return new Promise((resolve) => {
    const layout = cy.layout({
      name: "preset",
      positions: centreOf,
      eles: cy.nodes().filter((node) => !node.isParent()),
      fit: false,
      animate: false,
    });
    layout.one("layoutstop", resolve);
    layout.run();
  });
}
