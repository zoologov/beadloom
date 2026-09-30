// beadloom:component=site-shared
// The ELK layout of a layered graph: fixed, seedless options, so one data file
// always gives one layout.
//
// Each node carries a `partition`, its layer rank, and ELK's partitioning pins
// it into that rank's band from top to bottom (`elk.direction: DOWN`), so the
// lanes follow the declared layers rather than the topology.
// `INCLUDE_CHILDREN` lays out compound parents (a domain's box around its
// features and components) together with their children.
//
// The partition reaches ELK through `nodeLayoutOptions`. Before BDL-076 the
// element carried `partition` in its data and nothing handed it to ELK, so
// partitioning was switched on with no node in a partition.

/** ELK's per-node options: the node's lane, when it has one. */
function laneOf(node) {
  const partition = node.data("partition");
  return typeof partition === "number" ? { "elk.partitioning.partition": String(partition) } : {};
}

export const LAYERED_LAYOUT = {
  name: "elk",
  elk: {
    algorithm: "layered",
    "elk.direction": "DOWN",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.hierarchyHandling": "INCLUDE_CHILDREN",
    "elk.partitioning.activate": "true",
    "elk.layered.spacing.nodeNodeBetweenLayers": "70",
    "elk.spacing.nodeNode": "45",
    "elk.padding": "[top=36,left=24,bottom=24,right=24]",
    "elk.layered.crossingMinimization.semiInteractive": "true",
  },
  nodeLayoutOptions: laneOf,
  fit: false,
  animate: false,
};
