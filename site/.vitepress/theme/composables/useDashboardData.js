// useDashboardData — loads the deterministic `dashboard.data.json` emitted by
// `beadloom docs site` (Python is the single source of truth; the front-end
// never invents a figure).
//
// The JSON lives next to the dashboard page at the site root
// (`<base>/dashboard.data.json`). It is fetched client-side so the widgets stay
// purely presentational and the page degrades gracefully (static textual
// summary) when JS is disabled or the fetch fails.

import { ref } from "vue";
import { withBase } from "vitepress";

// Shared module-level state so the four widgets fetch the data only once.
const data = ref(null);
const error = ref(null);
let started = false;

function isBrowser() {
  return typeof window !== "undefined" && typeof fetch !== "undefined";
}

async function load() {
  if (started || !isBrowser()) {
    return;
  }
  started = true;
  try {
    const res = await fetch(withBase("/dashboard.data.json"));
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    data.value = await res.json();
  } catch (err) {
    error.value = err;
  }
}

export function useDashboardData() {
  load();
  return { data, error };
}
