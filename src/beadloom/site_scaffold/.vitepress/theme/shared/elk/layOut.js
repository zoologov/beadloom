// beadloom:component=site-shared
// ELK run in a Web Worker, once per graph: the page's main thread is never held by a layout.
//
// One worker serves the page and is started on the first layout. It speaks
// ELK's own protocol: `register` names the algorithm once, and each `layout`
// message carries a graph and comes back with it laid out, under the id it was
// sent with. A worker that fails to start or dies fails every layout it holds,
// so a viewer reports the failure instead of waiting forever.
//
// Layouts are kept in memory by their ELK graph, so a viewer that draws a graph
// already laid out on this page (a page visited again, a node page after the
// architecture page) does not run ELK again. A run still in progress is shared.

import { geometryOf } from "./geometry.js";

/** How many layouts the page keeps; the least recently used one goes first. */
const KEPT_LAYOUTS = 8;
/** The only algorithm the viewer runs. */
const ALGORITHMS = Object.freeze(["layered"]);

let worker = null;
let nextId = 0;
const waiting = new Map();
const layouts = new Map();

function failAll(error) {
  for (const { reject } of waiting.values()) reject(error);
  waiting.clear();
}

/** The reason in an ELK error message, which may be an exception the worker could only describe. */
function errorOf(reported) {
  const reason = typeof reported === "string" ? reported : reported?.message || String(reported);
  return new Error(`ELK could not lay the graph out: ${reason}`);
}

function startWorker() {
  const started = new Worker(new URL("./elk.worker.js", import.meta.url), { type: "module" });
  started.onmessage = ({ data }) => {
    const request = waiting.get(data.id);
    if (!request) return;
    waiting.delete(data.id);
    if (data.error) request.reject(errorOf(data.error));
    else request.resolve(data.data);
  };
  started.onerror = (event) => {
    event.preventDefault();
    if (worker === started) worker = null;
    started.terminate();
    failAll(new Error(`the layout worker stopped: ${event.message || "it could not be loaded"}`));
  };
  started.postMessage({ id: nextId++, cmd: "register", algorithms: ALGORITHMS });
  return started;
}

/**
 * Start the layout worker now, if it is not running, so that loading ELK
 * overlaps whatever the page does before its first layout.
 */
export function warmUpLayout() {
  worker ||= startWorker();
}

/** The graph laid out by the worker. */
function request(graph) {
  warmUpLayout();
  const id = nextId++;
  return new Promise((resolve, reject) => {
    waiting.set(id, { resolve, reject });
    worker.postMessage({ id, cmd: "layout", graph, layoutOptions: {}, options: {} });
  });
}

function keep(key, run) {
  layouts.delete(key);
  layouts.set(key, run);
  while (layouts.size > KEPT_LAYOUTS) layouts.delete(layouts.keys().next().value);
}

/**
 * Lay `graph` (an ELK graph, `graph.js`) out; resolves to `{ geometry, source, ms }`.
 *
 * `geometry` is `geometryOf` the answer (`geometry.js`); `source` is "worker"
 * when ELK ran for this call and "cache" when the layout was already there or
 * under way; `ms` is how long the caller waited. A failed run is not kept.
 */
export async function layOut(graph) {
  const started = performance.now();
  const key = JSON.stringify(graph);
  const known = layouts.get(key);
  const run = known || request(graph).then(geometryOf);
  keep(key, run);
  if (!known) run.catch(() => layouts.get(key) === run && layouts.delete(key));
  const geometry = await run;
  return { geometry, source: known ? "cache" : "worker", ms: performance.now() - started };
}
