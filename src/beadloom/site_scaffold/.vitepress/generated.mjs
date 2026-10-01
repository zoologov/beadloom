// Reads a module `beadloom docs site` generates beside the VitePress config.
//
// `site.generated.mjs` (title, description, base path, repository link) and
// `config.generated.mjs` (nav and sidebar) do not exist before the first
// generation, and the portal's config and its browser tests still load then,
// with an empty module and a message that says which file is missing. A module
// that exists and does not load - a syntax error, a throw, an import of its own
// that is missing - is not read as missing: the error is thrown, because a
// portal built without its identity deploys under the wrong base, with no title
// and no nav, and says nothing.

import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

/** The module at `url`, or `{}`, with a warning, when no file is there yet. */
export async function importGenerated(url) {
  const file = fileURLToPath(url);
  if (!existsSync(file)) {
    console.warn(`${file} does not exist yet; run \`beadloom docs site\` to generate it.`);
    return {};
  }
  return import(url.href);
}
