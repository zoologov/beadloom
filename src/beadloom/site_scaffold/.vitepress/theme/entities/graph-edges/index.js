// beadloom:component=site-graph-edges
// Public API of the `graph-edges` entity.

export {
  CONTAINMENT_KIND,
  DOT_PATTERN,
  DRAWN_KINDS,
  EDGE_STYLES,
  VIOLATION_KEY,
  contractStyleKey,
  dashOf,
  isDrawnKind,
  isViolation,
  legendKeysOf,
  styleKeyOf,
} from "./model/edgeKinds.js";
export {
  DEPENDENCY_KINDS,
  DEPENDENT_ENDS,
  NEIGHBOURHOOD_KINDS,
  adjacencyOf,
  dependentsOf,
  edgeGroupsOf,
  edgeKeyOf,
} from "./model/adjacency.js";
export { boxEdgesOf } from "./model/boxEdges.js";
export { DIMMED_SHARE, edgePaletteOf } from "./lib/edgePalette.js";
export {
  HEAD_ROOM,
  NO_SOURCE_HEAD,
  NO_TARGET_HEAD,
  SAME_END,
  crowdedHeadsOf,
  departuresBeside,
  droppedHeadsOf,
  headEndsOf,
  headRoomsOf,
} from "./lib/heads.js";
export {
  LINE_MARKS,
  arrowScaleOf,
  cornerRadiiOf,
  dashOffsetOf,
  dashOnScreen,
  edgeCornerRadiiOf,
  endHeadLength,
  headLengthOf,
  lineWidthOf,
  routePointsOf,
} from "./lib/lineMarks.js";
export { default as EdgeLegend } from "./ui/EdgeLegend.vue";
