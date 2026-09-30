// Two viewers on one page do not share an id or a test handle (BDL-076 R1 finding n3).
//
// The panel's id was the constant "bl-viewer-panel", so two viewers on one page
// would give two elements one id and the second toolbar's "Panel" button would
// control the first panel. And every viewer deleted `window.__beadloomViewer`
// when it unmounted, whoever had installed it, so a viewer leaving the page took
// a live neighbour's handle with it. No generated page mounts two viewers, so
// these cases load the viewer's modules into a blank page (`support/themeModules.js`).

import { test, expect } from "@playwright/test";
import { openThemeModules } from "./support/themeModules.js";

test("the test handle is removed only by the viewer that installed it", async ({ page }) => {
  await openThemeModules(page);

  const seen = await page.evaluate(async () => {
    const { exposeTestHandle } = await import("/widgets/graph-viewer/model/testHandle.js");
    const source = (name) => ({
      cy: () => null,
      container: () => null,
      ready: () => false,
      selection: () => name,
      state: () => ({}),
      arranging: () => false,
      impactSummary: () => null,
    });
    const disposeFirst = exposeTestHandle(source("first"));
    const disposeSecond = exposeTestHandle(source("second"));
    const installed = window.__beadloomViewer?.selection() ?? null;
    disposeFirst();
    const afterFirstLeft = window.__beadloomViewer?.selection() ?? null;
    disposeSecond();
    return { installed, afterFirstLeft, afterBothLeft: "__beadloomViewer" in window };
  });

  expect(seen).toEqual({ installed: "second", afterFirstLeft: "second", afterBothLeft: false });
});

test("each viewer's panel gets an id of its own", async ({ page }) => {
  await openThemeModules(page);

  const ids = await page.evaluate(async () => {
    const { createApp, h } = await import("vue");
    const { usePanelId } = await import("/widgets/graph-viewer/model/usePanelId.js");
    const Viewer = { setup: () => () => h("aside", { id: usePanelId() }) };
    createApp({ render: () => [h(Viewer), h(Viewer)] }).mount("#app");
    return [...document.querySelectorAll("#app aside")].map((aside) => aside.id);
  });

  expect(ids).toHaveLength(2);
  expect(new Set(ids).size).toBe(2);
  for (const id of ids) expect(id).toMatch(/^bl-viewer-panel-/);
});
