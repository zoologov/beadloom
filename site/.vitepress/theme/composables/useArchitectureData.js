// useArchitectureData — loads the deterministic `architecture.data.json` emitted
// by `beadloom docs site` (Python is the single source of truth; the front-end
// never invents a node, an edge, a layer, or a dependency).
//
// The JSON lives next to the architecture page at the site root
// (`<base>/architecture.data.json`, copied verbatim from `public/`). It is
// fetched client-side so the map stays purely presentational and the page
// degrades gracefully (the static textual summary in `architecture.md`) when JS
// is disabled or the fetch fails.

import { ref } from "vue";
import { withBase } from "vitepress";

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
    const res = await fetch(withBase("/architecture.data.json"));
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    data.value = await res.json();
  } catch (err) {
    error.value = err;
  }
}

export function useArchitectureData() {
  load();
  return { data, error };
}
