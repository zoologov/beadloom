// beadloom:component=site-dashboard-data
// The dashboard data file, `dashboard.data.json`, as written by `beadloom docs site`.
//
// Every dashboard panel reads the same file, and they share one fetch.

import { createJsonResource } from "../../../shared/lib/index.js";

export const useDashboardData = createJsonResource("/dashboard.data.json");
