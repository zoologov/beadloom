// beadloom:component=site-graph-edge
// Public API of the `graph-edge` entity.

export {
  CONTAINMENT_KIND,
  DRAWN_KINDS,
  EDGE_STYLES,
  VIOLATION_KEY,
  contractStyleKey,
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
export { default as EdgeLegend } from "./ui/EdgeLegend.vue";
