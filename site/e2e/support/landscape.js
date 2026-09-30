// The browser tests' own reading of the landscape data file, written independently of the viewer.
//
// The expected sets come from `landscape.data.json` directly: which services a
// filter leaves, and a service's one-step neighbourhood along the contracts.

import { expect } from "@playwright/test";
import { waitForViewer } from "./viewer.js";

/** Each verdict's health, as the landscape data file's generator buckets it. */
const BROKEN = ["drift", "breaking", "orphaned_consumer", "undeclared_producer", "undeclared"];
const NEUTRAL = ["expected", "external", "dead", "unmapped"];

/** The health a verdict reads as: `broken`, `neutral` or `healthy`. */
export function healthOf(verdict) {
  const value = String(verdict || "").toLowerCase();
  if (BROKEN.includes(value)) return "broken";
  if (NEUTRAL.includes(value)) return "neutral";
  return "healthy";
}

/** Open the landscape page, optionally with a query string, and wait for the layout. */
export async function openLandscape(page, query = "") {
  await page.goto(`landscape.html${query}`);
  await waitForViewer(page);
}

/** The landscape data file the page was built from. */
export async function landscapeData(request) {
  const response = await request.get("landscape.data.json");
  expect(response.ok()).toBe(true);
  return response.json();
}

/** The ids of the services an edge of `health` touches (every edge when `health` is `all`), sorted. */
export function servicesWithEdges(data, health) {
  const ids = new Set();
  for (const edge of data.edges) {
    if (health !== "all" && healthOf(edge.verdict) !== health) continue;
    ids.add(edge.src);
    ids.add(edge.dst);
  }
  return [...ids].sort();
}

/** A service's one-step neighbourhood along the contracts, both ways: `{ ids, edges }`. */
export function contractNeighbourhood(data, id) {
  const ids = new Set([id]);
  const edges = new Set();
  for (const edge of data.edges) {
    if (edge.src === edge.dst || (edge.src !== id && edge.dst !== id)) continue;
    ids.add(edge.src);
    ids.add(edge.dst);
    edges.add(`produces:${edge.src}->${edge.dst}`);
  }
  return { ids: [...ids].sort(), edges: [...edges].sort() };
}

/** The contracts a service produces or consumes. */
export function contractsOf(data, id) {
  return data.contracts.filter(
    (c) => (c.producers || []).includes(id) || (c.consumers || []).includes(id)
  );
}
