// beadloom:component=site-architecture-data
// The architecture data file, `architecture.data.json`, as written by
// `beadloom docs site` (`beadloom.application.site.architecture_view`).
//
// Python is the only source of the graph: the viewer never invents a node, an
// edge, a layer or a dependency. The file carries a `schema_version`. Version 2
// keeps every key of version 1, and the viewer reads only version 1's keys, so
// it accepts both. A version it does not know is refused with a message the
// page shows, rather than drawn as an empty canvas.

import { createJsonResource } from "../../../shared/lib/index.js";

/** The schema versions this viewer reads. */
export const SUPPORTED_SCHEMA_VERSIONS = [1, 2];

/** Refuse a data file whose schema version this viewer does not read. */
export function checkSchemaVersion(json) {
  const version = json?.schema_version;
  if (!SUPPORTED_SCHEMA_VERSIONS.includes(version)) {
    throw new Error(
      `architecture.data.json has schema_version ${JSON.stringify(version)}; this viewer ` +
        `reads ${SUPPORTED_SCHEMA_VERSIONS.join(" and ")}. Rebuild the site with a matching ` +
        "`beadloom docs site`."
    );
  }
  return json;
}

export const useArchitectureData = createJsonResource(
  "/architecture.data.json",
  checkSchemaVersion
);
