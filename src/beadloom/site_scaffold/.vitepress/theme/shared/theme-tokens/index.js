// beadloom:component=site-shared
// Public API of the `shared/theme-tokens` segment, and the tone it defines that the
// VitePress palette has no variable for (`tones.css`), loaded wherever a token is.

import "./tones.css";

export { TOKEN_VARIABLES, mixRgb, resolveTokens } from "./resolve.js";
export { useThemeTokens } from "./useThemeTokens.js";
