// The browser tests' own reading of the viewer's look: sizes on screen, final runs, colours, contrast.
//
// Written apart from the viewer's code, so a case that asks how big an
// arrowhead is on screen, or which lines share their last run, does not ask the
// functions it checks. Cytoscape's own rules are restated here from its source
// (3.34.1): an arrowhead of a line `w` units wide at an `arrow-scale` of `s` is
// `max((13.37 w)^0.9, 29) * s` units across, and a triangle or a vee takes 0.3 of
// that along the line; a rounded corner of radius `r` between two straight runs
// takes `r` of each, and never more than half of either.

/** How much of Cytoscape's arrow size an arrowhead takes along its line: a triangle's and a vee's length. */
const ARROW_LENGTH_SHARE = 0.3;

/** The step the viewer's marks are restyled at as the zoom changes: a size on screen stays within half a step of its own. */
export const SCALE_STEP = 1.25;

/** Whether `measured` is `wanted` within half a scale step either way. */
export function withinAStep(measured, wanted) {
  const half = Math.sqrt(SCALE_STEP);
  return measured >= wanted / half - 1e-6 && measured <= wanted * half + 1e-6;
}

/** How long an arrowhead of `look` (`lineLooks`) is, in layout units. */
export function headLength(look) {
  return Math.max((look.width * 13.37) ** 0.9, 29) * look.arrowScale * ARROW_LENGTH_SHARE;
}

/** Whether `look` ends in an arrowhead at its target. */
export const hasTargetHead = (look) => look.targetArrow !== "none";

const distance = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);

/**
 * How long the straight part of a routed line's final run is, in layout units:
 * the last segment of `look.points`, less what its corner takes of it. Null for
 * a line with no corner before its end.
 */
export function straightFinalRun(look) {
  const points = look.points;
  const n = points.length;
  if (n < 3) return null;
  const last = distance(points[n - 2], points[n - 1]);
  const before = distance(points[n - 3], points[n - 2]);
  const corners = n - 2;
  const radius = look.cornerRadii.length === 1 ? look.cornerRadii[0] : look.cornerRadii[corners - 1] ?? 0;
  const taken = Math.min(radius, last / 2, before / 2);
  return last - taken;
}

/**
 * The lines among `looks` that share their final run into one end: groups of
 * the ids whose routes end at one point, arriving from one direction. A group of
 * one is a line that arrives on its own.
 */
export function finalRunGroups(looks) {
  const groups = new Map();
  for (const look of looks) {
    const points = look.points;
    const n = points.length;
    if (n < 2) continue;
    const [before, tip] = [points[n - 2], points[n - 1]];
    const along = Math.hypot(tip.x - before.x, tip.y - before.y) || 1;
    const direction = `${Math.round((tip.x - before.x) / along)},${Math.round((tip.y - before.y) / along)}`;
    const key = `${Math.round(tip.x * 2) / 2},${Math.round(tip.y * 2) / 2}|${direction}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(look);
  }
  return [...groups.values()];
}

/** `[r, g, b]` of an `rgb(...)`, `rgba(...)` or `color(srgb ...)` string, each from 0 to 255. */
export function rgbOf(colour) {
  const text = String(colour).trim();
  const srgb = text.match(/^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/);
  if (srgb) return srgb.slice(1, 4).map((value) => Math.round(Number(value) * 255));
  return text.match(/[\d.]+/g).slice(0, 3).map(Number);
}

/** `top` laid over `bottom` at `alpha`, as `[r, g, b]`. */
export function over(top, bottom, alpha) {
  const [a, b] = [rgbOf(top), rgbOf(bottom)];
  return `rgb(${a.map((value, i) => Math.round(value * alpha + b[i] * (1 - alpha))).join(",")})`;
}

/** The largest difference of one channel between two colours. */
export function channelDistance(a, b) {
  const [x, y] = [rgbOf(a), rgbOf(b)];
  return Math.max(...x.map((value, i) => Math.abs(value - y[i])));
}

/** A colour's relative luminance, as WCAG 2.1 defines it. */
function luminance(colour) {
  const [r, g, b] = rgbOf(colour).map((value) => {
    const c = value / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** The WCAG 2.1 contrast ratio of two colours, from 1 to 21. */
export function contrastRatio(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

/** The contrast WCAG AA asks of normal text. */
export const AA_TEXT = 4.5;

/** The value a CSS colour expression resolves to on `page`, as the browser computes it. */
export function cssColour(page, expression) {
  return page.evaluate((value) => {
    const probe = document.createElement("span");
    probe.style.color = value;
    document.querySelector("[data-fullscreen-fallback]").appendChild(probe);
    const resolved = getComputedStyle(probe).color;
    probe.remove();
    return resolved;
  }, expression);
}

/** The background the viewer's canvas is drawn on. */
export function canvasBackground(page) {
  return page.evaluate(
    () => getComputedStyle(document.querySelector("[data-testid='graph-canvas']")).backgroundColor
  );
}

/**
 * The colour each node of `looks` (`nodeLooks`) is drawn in, by its id: its fill
 * over what holds it, the canvas `background` at the top. A node not drawn is
 * drawn on nothing of its own, so asking for it answers the canvas.
 */
export function drawnColours(looks, background) {
  const byId = new Map(looks.map((look) => [look.id, look]));
  const drawn = new Map();
  const colourOf = (id) => {
    const look = byId.get(id);
    if (!look) return background;
    if (!drawn.has(id)) drawn.set(id, over(look.fill, colourOf(look.parent), look.fillOpacity));
    return drawn.get(id);
  };
  return colourOf;
}

/** WCAG 2.1's contrast for a component's boundary against what is beside it (non-text contrast, 1.4.11). */
export const NON_TEXT = 3;

/**
 * The layer legend's samples, by the layer's name: `{ tone, share }`, the tone
 * its border is drawn in and the share of that tone its fill shows over the
 * page's background, read from the sample as the browser paints it.
 */
export function legendSamples(page) {
  return page.locator("[data-legend-layer]").evaluateAll((items) =>
    items.map((item) => {
      const sample = getComputedStyle(item.querySelector(".bl-legend-swatch"));
      const page = getComputedStyle(document.querySelector("[data-testid='graph-canvas']"));
      return { name: item.dataset.legendLayer, border: sample.borderTopColor, fill: sample.backgroundColor, page: page.backgroundColor };
    })
  ).then((samples) =>
    new Map(
      samples.map(({ name, border, fill, page: under }) => {
        const [tone, painted, ground] = [rgbOf(border), rgbOf(fill), rgbOf(under)];
        // The channel the tone stands furthest from the page in says the share most exactly.
        const channel = [0, 1, 2].sort((a, b) => Math.abs(tone[b] - ground[b]) - Math.abs(tone[a] - ground[a]))[0];
        const share = (painted[channel] - ground[channel]) / (tone[channel] - ground[channel]);
        return [name, { tone: `rgb(${tone.join(",")})`, share }];
      })
    )
  );
}
