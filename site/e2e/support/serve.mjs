// The browser tests' server fixture: build the portal, then serve the build.
//
// `vitepress build` and then `vitepress preview` on the port Playwright names,
// so the tests run against the bundle that ships. It refuses to start when the
// generated content is missing, because a build over no data renders an empty
// viewer and every test would fail for a reason that has nothing to do with it.

import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SITE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const DATA_FILE = path.join(SITE_ROOT, "public", "architecture.data.json");
const port = process.argv[2] || "4178";
const vitepress = path.join(SITE_ROOT, "node_modules", ".bin", "vitepress");

if (!existsSync(DATA_FILE)) {
  process.stderr.write(
    `serve.mjs: ${DATA_FILE} is missing. Generate the content first: ` +
      "`beadloom docs site --out site`, from the repository root.\n"
  );
  process.exit(1);
}

const build = spawnSync(vitepress, ["build", "."], { cwd: SITE_ROOT, stdio: "inherit" });
if (build.status !== 0) {
  process.exit(build.status ?? 1);
}

const preview = spawn(vitepress, ["preview", ".", "--port", port], {
  cwd: SITE_ROOT,
  stdio: "inherit",
});
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => preview.kill(signal));
}
preview.on("exit", (code) => process.exit(code ?? 0));
