// beadloom:component=site-select-neighbourhood
// Public API of the `select-neighbourhood` feature.

export { boxNeighbourhoodOf, neighbourhoodOf } from "./lib/neighbourhood.js";
export {
  ALL_DEPTHS,
  DEPTH_CHOICES,
  DIRECTION_CHOICES,
  MAX_DEPTH,
  NEIGHBOURHOOD_DEFAULTS,
  depthLimit,
} from "./model/options.js";
export { default as NeighbourhoodControls } from "./ui/NeighbourhoodControls.vue";
