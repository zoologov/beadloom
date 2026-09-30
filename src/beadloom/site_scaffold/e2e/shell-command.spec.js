// A command to copy names its target in a form the shell reads back whole (BDL-076 R1 finding n2).
//
// The card and the impact summary offer `beadloom ctx <ref>`, `beadloom why <ref>`
// and `beadloom impact <source>` to copy. A source path with a space, a quote or
// a `#` pasted unquoted names another target, or several. `shellQuote` leaves a
// word the shell reads as itself alone and single-quotes anything else.

import { test, expect } from "@playwright/test";
import { openThemeModules } from "./support/themeModules.js";
import { architectureData, openArchitecture } from "./support/viewer.js";

const CASES = [
  { word: "rule-engine", quoted: "rule-engine" },
  { word: "src/shop/core/", quoted: "src/shop/core/" },
  { word: "src/my module/a.py", quoted: "'src/my module/a.py'" },
  { word: "src/it's.py", quoted: "'src/it'\\''s.py'" },
  { word: "src/c#/x.py", quoted: "'src/c#/x.py'" },
  { word: "src/$HOME;rm", quoted: "'src/$HOME;rm'" },
  { word: "", quoted: "''" },
];

test("a word the shell reads as itself is left alone, and any other is single-quoted", async ({
  page,
}) => {
  await openThemeModules(page);

  const quoted = await page.evaluate(async (words) => {
    const { shellQuote } = await import("/shared/lib/shell.js");
    return words.map((word) => shellQuote(word));
  }, CASES.map((c) => c.word));

  expect(quoted).toEqual(CASES.map((c) => c.quoted));
});

test("the impact summary quotes a source path with a space in the command it copies", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = data.nodes.find((n) => n.id === "rule-engine") || data.nodes.find((n) => n.source);
  node.source = "src/my module/it's.py";
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

  await openArchitecture(page, `?focus=${node.id}&view=impact`);

  await expect(page.getByTestId("impact-summary")).toContainText(
    "beadloom impact 'src/my module/it'\\''s.py'"
  );
});
