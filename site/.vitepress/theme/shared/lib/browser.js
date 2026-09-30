// beadloom:component=site-shared
// Whether the code runs in a browser, not in VitePress's server-side render.

/** True in a browser with a DOM; false during the server-side render. */
export function isBrowser() {
  return typeof window !== "undefined" && typeof document !== "undefined";
}
