// The Feature-Sliced Design linter's configuration for the portal's theme.
//
// `npm run lint:fsd` runs Steiger, the official FSD linter, over
// `.vitepress/theme` with its recommended rule set and nothing switched off: a
// rule this theme does not keep is left red and named where the cut that breaks
// it was decided, rather than turned off here where no reader would see it.

import { defineConfig } from "steiger";
import fsd from "@feature-sliced/steiger-plugin";

export default defineConfig([...fsd.configs.recommended]);
