// Dev/runtime guard for the interactive viz.
//
// `vitepress build` (the production bundle) and the VitePress *dev* server
// resolve dependencies differently: the dev server pre-bundles them with Vite's
// optimizer, so a dependency chain the build resolves can still crash the dev
// server. That happened once, when the theme reached elkjs through
// cytoscape-elk, whose `web-worker` dependency did not resolve under the
// optimizer. The theme now runs elkjs in a module worker of its own
// (`shared/elk/elk.worker.js`), and no package pulls `web-worker` in.
//
// This script boots the VitePress dev server programmatically, the same path,
// waits until it is listening, then shuts it down, so it proves the dev server
// boots without leaving one running. It does not open a page, so it does not
// prove the layout worker runs under the dev server. Exits non-zero on any boot
// or optimize failure.

import { createServer } from "vitepress";

const root = new URL("..", import.meta.url).pathname;

async function main() {
  const server = await createServer(root, { port: 5199 });
  await server.listen();
  // Reaching here means Vite created the dev server and began dependency
  // optimization for the configured root without throwing.
  await server.close();
  process.stdout.write("DEV-OPTIMIZE-CHECK OK: vitepress dev server booted + closed\n");
}

main().catch((err) => {
  process.stderr.write(`DEV-OPTIMIZE-CHECK FAIL: ${err?.stack || err}\n`);
  process.exit(1);
});
