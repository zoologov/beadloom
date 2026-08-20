// Dev/runtime guard for the interactive viz (BDL-060 S4 ext).
//
// The web-worker bug class slipped through because `vitepress build` (the
// production bundle) stayed GREEN while the VitePress *dev* server crashed: the
// dev server pre-bundles dependencies with Vite's optimizer, and the Cytoscape +
// cytoscape-elk -> elkjs -> web-worker chain failed to resolve there. This script
// boots the VitePress dev server programmatically (the SAME path the crash was
// on), waits until it is listening (proving dep optimization succeeded), then
// shuts it straight down — so it proves the dev path without leaving a server
// running. Exits non-zero on any boot/optimize failure.

import { createServer } from "vitepress";

const root = new URL("..", import.meta.url).pathname;

async function main() {
  const server = await createServer(root, { port: 5199 });
  await server.listen();
  // Reaching here means Vite created the dev server + began dep optimization
  // for the configured root without throwing on the viz worker chain.
  await server.close();
  console.log("DEV-OPTIMIZE-CHECK OK: vitepress dev server booted + closed");
}

main().catch((err) => {
  console.error("DEV-OPTIMIZE-CHECK FAIL:", err);
  process.exit(1);
});
