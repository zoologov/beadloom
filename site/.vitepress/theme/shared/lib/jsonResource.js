// beadloom:component=site-shared
// A JSON file under the site's base path, fetched once per page load.
//
// The portal's data files (`architecture.data.json`, `landscape.data.json`,
// `dashboard.data.json`) are written by `beadloom docs site` and copied verbatim
// from `public/`. Each reader shares one fetch and one state across every
// component that asks for it, and the page degrades to its static summary when
// JavaScript is off or the fetch fails.

import { ref } from "vue";
import { withBase } from "vitepress";
import { isBrowser } from "./browser.js";

/**
 * A reader of one JSON file: `use()` returns `{ data, error }`, both refs.
 *
 * `validate(json)` may throw to refuse a file; the error it throws becomes the
 * reader's `error`, so a caller shows a message rather than a blank canvas.
 */
export function createJsonResource(path, validate = (json) => json) {
  const data = ref(null);
  const error = ref(null);
  let started = false;

  async function load() {
    if (started || !isBrowser() || typeof fetch === "undefined") return;
    started = true;
    try {
      const response = await fetch(withBase(path));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      data.value = validate(await response.json());
    } catch (err) {
      error.value = err;
    }
  }

  return function use() {
    load();
    return { data, error };
  };
}
