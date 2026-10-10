// The font a case draws the portal in, set from the case rather than from the viewer.
//
// The viewer draws its canvas in the portal's font, the CSS variable
// `--vp-font-family-base` resolved on its root (`shared/theme-tokens/resolve.js`),
// and measures every title in it. A system's fonts decide how wide a title is:
// the same name is wider in Linux's DejaVu Sans than in macOS's default font, and
// a rule about titles that holds in one font is held in another by setting that
// variable before the page is loaded. Nothing in the viewer reads a switch for
// this; the case overrides the portal's own stylesheet, as a reader's user
// stylesheet would.

/**
 * A font wider than the portal's default on every system the suite runs on:
 * Verdana where it is installed (macOS, Windows), DejaVu Sans, its near
 * equivalent in width, on Linux.
 */
export const WIDE_FONT = '"Verdana", "DejaVu Sans", sans-serif';

/** The variable the portal's font is read from. */
const FONT_VARIABLE = "--vp-font-family-base";

/** Draw every page `page` loads from now on in `family`, over the portal's own font. */
export async function drawInFont(page, family) {
  await page.addInitScript(
    ([variable, value]) => {
      const style = document.createElement("style");
      style.textContent = `:root { ${variable}: ${value} !important; }`;
      const add = () => (document.head || document.documentElement).appendChild(style);
      if (document.head || document.documentElement) add();
      else document.addEventListener("DOMContentLoaded", add, { once: true });
    },
    [FONT_VARIABLE, family]
  );
}
