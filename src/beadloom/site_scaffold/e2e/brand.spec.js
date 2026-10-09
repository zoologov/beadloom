// The portal's brand: the project's logo in the nav, the favicon, the footer and
// the icon of the header's repository link.
//
// Each rule is read against the identity `beadloom docs site` generated for the
// portal under test, `.vitepress/site.generated.mjs`, so the same case holds on
// a portal that declares a logo and on one that does not: a logo declared is
// drawn and a logo not declared is absent; a footer
// switched on has its two lines and a footer switched off is not there; a
// repository declared is linked with its icon and none declared draws no link.
//
// The favicon follows the logo (the owner's look of 2026-10-09): a
// portal with a logo of its own takes that file as its favicon, and only a portal
// without one shows Beadloom's, so on an adopter's portal Beadloom's mark is in the
// footer alone. A portal whose logo is Beadloom's own icon has no logo of its own:
// it shows Beadloom's favicon, the theme-adaptive form of the same mark.

import { test, expect } from "@playwright/test";
import { importGenerated } from "../.vitepress/generated.mjs";

const { site = {} } = await importGenerated(
  new URL("../.vitepress/site.generated.mjs", import.meta.url)
);
const BASE = site.base || "/";
/** Beadloom's repository, where the footer's second line links. */
const BEADLOOM_REPOSITORY = "https://github.com/zoologov/beadloom";
const FOOTER_ICON = `${BASE}brand/beadloom-icon.svg`;
/** Beadloom's favicon: the theme-adaptive SVG, and the PNG for browsers that take no SVG. */
const FAVICON_SVG = `${BASE}brand/beadloom-favicon.svg`;
const FAVICON_PNG = `${BASE}brand/beadloom-favicon.png`;
const FAVICON_PNG_SIZE = 32;
/** The nav logo's side when it is drawn in the text's colour. */
const NAV_LOGO_SIZE = 32;
/** A page with a sidebar, which the footer must stay clear of. */
const PAGE = "dashboard.html";
/** The first line of an SVG the scaffold wrote: the comment that marks it as written by `docs site`. */
const MARKER_LINE = /^<!--[^\n]*-->\n/;

/** The file at `path` on the server under test, and its body as text. */
async function served(request, path) {
  const response = await request.get(path);
  expect(response.status(), path).toBe(200);
  return response.text();
}

/** The logo's address on the server under test; `""` without one. */
function logoPath() {
  return site.logo ? `${BASE}${site.logo.replace(/^\//, "")}` : "";
}

/**
 * Whether the portal declares a logo of its own: a logo that is not Beadloom's
 * icon, compared with the icon the portal serves for its footer, marker removed.
 */
async function hasLogoOfItsOwn(request) {
  if (!site.logo) return false;
  if (!site.logo.endsWith(".svg")) return true;
  const icon = (await served(request, FOOTER_ICON)).replace(MARKER_LINE, "");
  return (await served(request, logoPath())) !== icon;
}

/** The favicon links in the page's head, as `{href, type, sizes}`. */
async function favicons(page) {
  return page.locator('head link[rel="icon"]').evaluateAll((links) =>
    links.map((link) => ({
      href: link.getAttribute("href"),
      type: link.getAttribute("type"),
      sizes: link.getAttribute("sizes"),
    }))
  );
}

/** Whether the element is the topmost thing at its own centre: nothing covers it. */
async function uncovered(locator) {
  await locator.scrollIntoViewIfNeeded();
  return locator.evaluate((element) => {
    const box = element.getBoundingClientRect();
    const top = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
    return element === top || element.contains(top);
  });
}

/** The nav logo's painted colour and the title's text colour, in the theme now shown. */
async function logoAndTitleColours(page) {
  return page.locator(".VPNavBarTitle .title").evaluate((title) => ({
    logo: getComputedStyle(title.querySelector(".logo")).backgroundColor,
    text: getComputedStyle(title).color,
  }));
}

test("a portal without a logo of its own shows Beadloom's favicon, theme-adaptive, and its PNG", async ({ page, request }) => {
  await page.goto(PAGE);
  const icons = await favicons(page);
  if (await hasLogoOfItsOwn(request)) {
    // Beadloom's mark is on an adopter's portal in the footer alone.
    const named = icons.map((icon) => icon.href).filter((href) => href.includes("beadloom"));
    expect(named, "an adopter's favicon names Beadloom's").toEqual([]);
    return;
  }
  expect(icons).toEqual([
    { href: FAVICON_SVG, type: "image/svg+xml", sizes: null },
    { href: FAVICON_PNG, type: "image/png", sizes: `${FAVICON_PNG_SIZE}x${FAVICON_PNG_SIZE}` },
  ]);
  // The SVG picks its glyph's colour by the browser's scheme.
  expect(await served(request, FAVICON_SVG)).toContain("prefers-color-scheme: dark");
  // The PNG is a PNG of the size its link declares: the signature, then IHDR's width and height.
  const png = await (await request.get(FAVICON_PNG)).body();
  expect([...png.subarray(1, 4)].map((code) => String.fromCharCode(code)).join("")).toBe("PNG");
  expect([png.readUInt32BE(16), png.readUInt32BE(20)]).toEqual([FAVICON_PNG_SIZE, FAVICON_PNG_SIZE]);
});

test("a portal with a logo of its own takes the logo as its favicon, as it is", async ({ page, request }) => {
  await page.goto(PAGE);
  const icons = await favicons(page);
  if (!(await hasLogoOfItsOwn(request))) {
    expect(icons.map((icon) => icon.href)).not.toContain(logoPath() || "no logo");
    return;
  }
  const type = site.logo.endsWith(".svg") ? "image/svg+xml" : "image/png";
  expect(icons).toEqual([{ href: logoPath(), type, sizes: null }]);
});

test("the nav shows the project's logo when it declares one, and none otherwise", async ({ page }) => {
  await page.goto(PAGE);
  const logo = page.locator(".VPNavBarTitle img.logo");
  if (!site.logo) {
    await expect(logo).toHaveCount(0);
    return;
  }
  await expect(logo).toBeVisible();
  await expect(logo).toHaveAttribute("src", logoPath());
  const drawn = await logo.evaluate((image) => image.complete && image.naturalWidth > 0);
  expect(drawn, `the logo ${site.logo} is not drawn`).toBe(true);
});

test("a logo drawn in currentColor is drawn in the text's colour, in either theme, at 32 pixels", async ({ page, request }) => {
  const monochrome =
    Boolean(site.logo) && site.logo.endsWith(".svg") && (await served(request, logoPath())).includes("currentColor");
  await page.goto(PAGE);
  const logo = page.locator(".VPNavBarTitle img.logo");
  if (!monochrome) {
    // Drawn as it is: no mask over a logo in colours of its own.
    if (site.logo) {
      const mask = await logo.evaluate((image) => getComputedStyle(image).maskImage);
      expect(mask).toBe("none");
    }
    return;
  }
  const mask = await logo.evaluate((image) => {
    const style = getComputedStyle(image);
    return style.maskImage || style.webkitMaskImage;
  });
  expect(mask).toContain(logoPath());
  const box = await logo.boundingBox();
  expect([box.width, box.height]).toEqual([NAV_LOGO_SIZE, NAV_LOGO_SIZE]);

  const light = await logoAndTitleColours(page);
  expect(light.logo).toBe(light.text);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
  const dark = await logoAndTitleColours(page);
  expect(dark.logo).toBe(dark.text);
  expect(dark.logo, "the logo keeps one colour in both themes").not.toBe(light.logo);
});

test("the footer says Powered by Beadloom on two lines, unless it is switched off", async ({ page, request }) => {
  await page.goto(PAGE);
  const footer = page.getByTestId("powered-by");
  if (site.poweredBy === false) {
    await expect(footer).toHaveCount(0);
    return;
  }
  await expect(footer).toBeVisible();
  await expect(footer.locator(".bl-powered-by-line")).toHaveCount(2);

  // Line 1: the small icon, drawn in the text's colour, and the name, which links nowhere.
  const name = footer.locator('[data-powered-by="name"]');
  const icon = name.locator('[data-powered-by="icon"]');
  await expect(icon).toBeVisible();
  const mask = await icon.evaluate((element) => {
    const style = getComputedStyle(element);
    return style.maskImage || style.webkitMaskImage;
  });
  expect(mask).toContain(FOOTER_ICON);
  expect(await served(request, FOOTER_ICON)).toContain("currentColor");
  const text = name.getByText("Powered by Beadloom", { exact: true });
  await expect(text).toBeVisible();
  await expect(name.getByRole("link")).toHaveCount(0);
  expect(await uncovered(text), "the sidebar covers the footer").toBe(true);

  // Line 2: MIT, and Beadloom's repository drawn with the GitHub mark.
  const licence = footer.locator('[data-powered-by="licence"]');
  await expect(licence).toContainText("MIT");
  const github = licence.locator("a.VPSocialLink");
  await expect(github).toHaveAttribute("href", BEADLOOM_REPOSITORY);
  const glyph = github.locator(".vpi-social-github");
  await expect(glyph).toBeVisible();
  const box = await glyph.boundingBox();
  expect([box.width, box.height]).toEqual([20, 20]);
});

test("the header links the project's repository with its forge's icon, or links nothing", async ({ page }) => {
  await page.goto(PAGE);
  const links = page.locator(".VPNavBarSocialLinks .VPSocialLink");
  if (!site.repoUrl) {
    await expect(links).toHaveCount(0);
    return;
  }
  await expect(links).toHaveCount(1);
  await expect(links).toHaveAttribute("href", site.repoUrl);
  const glyph = links.locator(`.vpi-social-${site.repoIcon}`);
  await expect(glyph).toBeVisible();
  const mask = await glyph.evaluate((element) => {
    const style = getComputedStyle(element);
    return style.maskImage || style.webkitMaskImage;
  });
  expect(mask, `no ${site.repoIcon} glyph is drawn`).not.toBe("none");
  // The footer's GitHub mark is the header's own size class.
  const box = await glyph.boundingBox();
  expect([box.width, box.height]).toEqual([20, 20]);
});
