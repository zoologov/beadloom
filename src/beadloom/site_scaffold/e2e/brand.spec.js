// The portal's brand: the project's logo in the nav, the favicon, the footer and
// the icon of the header's repository link.
//
// Each rule is read against the identity `beadloom docs site` generated for the
// portal under test, `.vitepress/site.generated.mjs`, so the same case holds on
// a portal that declares a logo and on one that does not: a logo declared is
// drawn and a logo not declared is absent; a footer
// switched on has its two lines and a footer switched off is not there; a
// repository declared is linked with its icon and none declared draws no link.

import { test, expect } from "@playwright/test";
import { importGenerated } from "../.vitepress/generated.mjs";

const { site = {} } = await importGenerated(
  new URL("../.vitepress/site.generated.mjs", import.meta.url)
);
const BASE = site.base || "/";
/** Beadloom's repository, where both lines of the footer link. */
const BEADLOOM_REPOSITORY = "https://github.com/zoologov/beadloom";
const FAVICON = `${BASE}brand/beadloom-icon-gradient.svg`;
const FOOTER_ICON = `${BASE}brand/beadloom-icon.svg`;
/** A page with a sidebar, which the footer must stay clear of. */
const PAGE = "dashboard.html";

/** The file at `path` on the server under test, and its body as text. */
async function served(request, path) {
  const response = await request.get(path);
  expect(response.status(), path).toBe(200);
  return response.text();
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

test("the favicon is Beadloom's gradient icon", async ({ page, request }) => {
  await page.goto(PAGE);
  const icon = page.locator('head link[rel="icon"]');
  await expect(icon).toHaveCount(1);
  await expect(icon).toHaveAttribute("href", FAVICON);
  await expect(icon).toHaveAttribute("type", "image/svg+xml");
  expect(await served(request, FAVICON)).toContain("linearGradient");
});

test("the nav shows the project's logo when it declares one, and none otherwise", async ({ page }) => {
  await page.goto(PAGE);
  const logo = page.locator(".VPNavBarTitle img.logo");
  if (!site.logo) {
    await expect(logo).toHaveCount(0);
    return;
  }
  await expect(logo).toBeVisible();
  await expect(logo).toHaveAttribute("src", `${BASE}${site.logo.replace(/^\//, "")}`);
  const drawn = await logo.evaluate((image) => image.complete && image.naturalWidth > 0);
  expect(drawn, `the logo ${site.logo} is not drawn`).toBe(true);
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

  // Line 1: the small icon, drawn in the text's colour, and the name linking to Beadloom.
  const name = footer.locator('[data-powered-by="name"]');
  const icon = name.locator('[data-powered-by="icon"]');
  await expect(icon).toBeVisible();
  const mask = await icon.evaluate((element) => {
    const style = getComputedStyle(element);
    return style.maskImage || style.webkitMaskImage;
  });
  expect(mask).toContain(FOOTER_ICON);
  expect(await served(request, FOOTER_ICON)).toContain("currentColor");
  const link = name.getByRole("link", { name: "Powered by Beadloom" });
  await expect(link).toHaveAttribute("href", BEADLOOM_REPOSITORY);
  expect(await uncovered(link), "the sidebar covers the footer").toBe(true);

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
