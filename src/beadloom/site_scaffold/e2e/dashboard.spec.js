// The dashboard names the populations its numbers were counted over.
//
// Beside the status cards, "Rule findings" says lint's totals for the project,
// split into the findings on nodes and the findings on none, and lists every
// finding lint binds to no node — no node card holds them — and
// "Pages" names the pages `beadloom docs site` wrote, by section, with the
// language of each About page. Both read `dashboard.data.json`; a file written
// before either was carried shows neither.

import { test, expect } from "@playwright/test";
import { requireShape } from "./support/shape.js";

async function dashboardData(request) {
  const response = await request.get("dashboard.data.json");
  expect(response.ok()).toBe(true);
  return response.json();
}

/** Open the dashboard served `data`. */
async function openDashboard(page, data) {
  await page.route("**/dashboard.data.json", (route) => route.fulfill({ json: data }));
  await page.goto("dashboard.html");
}

/** `count` followed by `one` when it is 1, and by `many` otherwise. */
const countOf = (count, one, many) => `${count} ${count === 1 ? one : many}`;

/** Lint's reach as the panel says it, from the data file's `lint`. */
function totalsSaid({ errors, warnings, nodes_with_findings: nodes, nodeless }) {
  const totals = `${countOf(errors, "error", "errors")}, ${countOf(warnings, "warning", "warnings")}`;
  const onNodes = errors + warnings - nodeless.length;
  return `This project: ${totals} — ${onNodes} on ${countOf(nodes, "node", "nodes")}, ${nodeless.length} on none.`;
}

const NODELESS = [
  { rule: "inert-rule", severity: "error", message: "cannot fire", file: "", line: null },
  { rule: "scenario-coverage", severity: "warn", message: "names no scenario", file: "docs/PRD.md", line: 12 },
];

test("Rule findings says the project's totals and lists every finding bound to no node", async ({ page, request }) => {
  const data = await dashboardData(request);
  data.lint = { ...data.lint, errors: 1, warnings: 69, nodes_with_findings: 28, nodeless: NODELESS };

  await openDashboard(page, data);
  const panel = page.getByTestId("rule-findings");

  await expect(panel.locator("[data-reach='totals']")).toHaveText("This project: 1 error, 69 warnings — 68 on 28 nodes, 2 on none.");
  await expect(panel.locator("[data-reach='nodeless']")).toHaveText("2 findings are bound to no node:");
  const listed = panel.locator("[data-nodeless-finding]");
  await expect(listed).toHaveCount(2);
  await expect(listed.nth(0)).toContainText("inert-rule");
  await expect(listed.nth(1)).toContainText("docs/PRD.md:12");
});

test("Rule findings says when no finding is bound to no node", async ({ page, request }) => {
  const data = await dashboardData(request);
  data.lint = { ...data.lint, errors: 0, warnings: 1, nodes_with_findings: 1, nodeless: [] };

  await openDashboard(page, data);

  await expect(page.getByTestId("rule-findings").locator("[data-reach='totals']")).toHaveText(
    "This project: 0 errors, 1 warning — 1 on 1 node, 0 on none."
  );
  await expect(page.getByTestId("rule-findings").locator("[data-reach='nodeless']")).toHaveText(
    "0 findings are bound to no node."
  );
  await expect(page.getByTestId("rule-findings").locator("[data-nodeless-finding]")).toHaveCount(0);
});

test("this portal's own Rule findings are the ones its data file holds", async ({ page, request }) => {
  const data = await dashboardData(request);
  requireShape(Array.isArray(data.lint?.nodeless), "the data file carries no node-less findings; it was written before they were carried");

  await openDashboard(page, data);
  const panel = page.getByTestId("rule-findings");

  await expect(panel.locator("[data-reach='totals']")).toHaveText(totalsSaid(data.lint));
  await expect(panel.locator("[data-nodeless-finding]")).toHaveCount(data.lint.nodeless.length);
});

test("Pages names every page the run wrote, by section, and the language of each About page", async ({
  page,
  request,
}) => {
  const data = await dashboardData(request);
  requireShape(data.pages, "the data file carries no page map; it was written before it was carried");

  await openDashboard(page, data);
  const panel = page.getByTestId("page-map");

  // The count is what the run wrote: a file the project adds under `.beadloom/site/` is
  // on the portal and not counted, so the line names the run, not the portal.
  const said = panel.locator("[data-pages='count']");
  await expect(said).toContainText(`beadloom docs site wrote ${countOf(data.pages.count, "page", "pages")}`);
  await expect(said).not.toContainText("This portal");
  for (const { language, page: about } of data.pages.languages) {
    await expect(panel.locator("[data-pages='count']")).toContainText(`${language} (${about})`);
  }
  for (const section of data.pages.sections) {
    const shown = panel.locator(`[data-pages-section='${section.name}']`);
    await expect(shown.locator("summary")).toHaveText(`${section.name}: ${section.count}`);
    await expect(shown.locator("li")).toHaveCount(section.pages.length);
  }
});

test("Pages says one page in the singular", async ({ page, request }) => {
  const data = await dashboardData(request);
  requireShape(data.pages, "the data file carries no page map; it was written before it was carried");
  data.pages = { ...data.pages, count: 1, languages: [] };

  await openDashboard(page, data);
  await expect(page.getByTestId("page-map").locator("[data-pages='count']")).toHaveText("beadloom docs site wrote 1 page.");
});

test("a data file written before the two panels shows neither", async ({ page, request }) => {
  const data = await dashboardData(request);
  delete data.pages;
  data.lint = { violations: 0, errors: 0, warnings: 0, by_severity: { error: 0, warn: 0 } };

  await openDashboard(page, data);
  await expect(page.locator("h1")).toContainText("Metrics dashboard");

  await expect(page.getByTestId("rule-findings")).toHaveCount(0);
  await expect(page.getByTestId("page-map")).toHaveCount(0);
});
