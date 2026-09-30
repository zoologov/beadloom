// beadloom:component=site-shared
// The portal's CSS variables resolved to the literal values a canvas library accepts.
//
// Cytoscape parses colour names, hex, rgb and hsl only. A `var(--vp-…)` string is
// rejected with a console warning and drawn in its fallback grey,
// rgb(153,153,153), which is how every edge of the viewer went grey before
// BDL-076. So nothing that reaches Cytoscape may carry `var(...)`: the browser
// resolves each token here, through `getComputedStyle` on a probe element, and a
// translucent colour is flattened over the resolved background so the result is
// one opaque `rgb(r,g,b)`.

/** The tokens the graph viewer draws with: name → VitePress CSS variable. */
export const TOKEN_VARIABLES = {
  bg: "--vp-c-bg",
  bgSoft: "--vp-c-bg-soft",
  bgAlt: "--vp-c-bg-alt",
  text1: "--vp-c-text-1",
  text2: "--vp-c-text-2",
  text3: "--vp-c-text-3",
  divider: "--vp-c-divider",
  brand: "--vp-c-brand-1",
  danger: "--vp-c-danger-1",
  warning: "--vp-c-warning-1",
  purple: "--vp-c-purple-1",
  indigo: "--vp-c-indigo-1",
  green: "--vp-c-green-1",
  yellow: "--vp-c-yellow-1",
  red: "--vp-c-red-1",
  gray: "--vp-c-gray-1",
};

/** The font token, resolved the same way because Cytoscape rejects `var(...)` there too. */
const FONT_VARIABLE = "--vp-font-family-base";
const FALLBACK_FONT = "system-ui, sans-serif";

function parseRgb(value) {
  const parts = String(value).match(/[\d.]+/g);
  if (!parts || parts.length < 3) return null;
  const [r, g, b] = parts.slice(0, 3).map(Number);
  const alpha = parts.length > 3 ? Number(parts[3]) : 1;
  return { r, g, b, alpha };
}

function flatten(colour, under) {
  const mix = (top, bottom) => Math.round(top * colour.alpha + bottom * (1 - colour.alpha));
  return `rgb(${mix(colour.r, under.r)},${mix(colour.g, under.g)},${mix(colour.b, under.b)})`;
}

/** Mix two resolved `rgb(...)` colours; `share` is the weight of `top`, from 0 to 1. */
export function mixRgb(top, bottom, share) {
  const a = parseRgb(top);
  const b = parseRgb(bottom);
  if (!a || !b) return top;
  return flatten({ ...a, alpha: share }, b);
}

/**
 * Every token of `TOKEN_VARIABLES` as an opaque `rgb(r,g,b)`, plus `font`.
 *
 * `scope` is the element whose cascade applies, normally the viewer's root, so a
 * page that overrides a variable around the viewer is honoured.
 */
export function resolveTokens(scope) {
  const probe = document.createElement("span");
  probe.style.display = "none";
  scope.appendChild(probe);
  try {
    const read = (variable, fallback) => {
      probe.style.color = `var(${variable}, ${fallback})`;
      return parseRgb(getComputedStyle(probe).color);
    };
    const white = { r: 255, g: 255, b: 255, alpha: 1 };
    const bgRaw = read(TOKEN_VARIABLES.bg, "#ffffff") || white;
    const bg = { ...bgRaw, alpha: 1 };
    const tokens = {};
    for (const [name, variable] of Object.entries(TOKEN_VARIABLES)) {
      const colour = read(variable, "currentColor") || bgRaw;
      tokens[name] = flatten(colour, bg);
    }
    probe.style.fontFamily = `var(${FONT_VARIABLE}, ${FALLBACK_FONT})`;
    tokens.font = getComputedStyle(probe).fontFamily || FALLBACK_FONT;
    return tokens;
  } finally {
    probe.remove();
  }
}
