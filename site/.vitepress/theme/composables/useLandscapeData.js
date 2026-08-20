// useLandscapeData — loads the deterministic `landscape.data.json` emitted by
// `beadloom docs site` (Python is the single source of truth; the front-end
// never invents a node, an edge, or a contract field).
//
// The JSON lives next to the landscape page at the site root
// (`<base>/landscape.data.json`, copied verbatim from `public/`). It is fetched
// client-side so the map stays purely presentational and the page degrades
// gracefully (the static textual summary in `landscape.md`) when JS is disabled
// or the fetch fails.

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
    const res = await fetch(withBase("/landscape.data.json"));
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    data.value = await res.json();
  } catch (err) {
    error.value = err;
  }
}

export function useLandscapeData() {
  load();
  return { data, error };
}
