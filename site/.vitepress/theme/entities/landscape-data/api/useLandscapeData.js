// beadloom:component=site-landscape-data
// The landscape data file, `landscape.data.json`, as written by `beadloom docs site`
// (`beadloom.application.landscape_view`).
//
// Python is the only source: the landscape map never invents a node, an edge or
// a contract field.

import { createJsonResource } from "../../../shared/lib/index.js";

export const useLandscapeData = createJsonResource("/landscape.data.json");
