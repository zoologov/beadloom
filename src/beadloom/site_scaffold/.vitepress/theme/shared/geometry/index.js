// beadloom:component=site-shared-geometry
// Public API of the `shared/geometry` segment.

export { aggregateRouteOf } from "./aggregateRoutes.js";
export { CORNER, cornerRadiusOf, cornerRoomOf } from "./corners.js";
export { crossesAny, drawnBoxOf, grownBoxesOf, pathOutside } from "./grownBoxes.js";
export { PILL_MARKS, pillStagesOf } from "./pillPlaces.js";
export { routeIndexOf, routesAlong } from "./routeIndex.js";
export { centreOf, compoundSizeOf, pathOf, pathOfSegments, segmentsOf } from "./routes.js";
export { gridIndex, lineIndex, orientationOf, segmentRect } from "./spatialIndex.js";
