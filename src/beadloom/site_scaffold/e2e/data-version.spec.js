// A data file of a schema version the viewer does not read is refused in the page.
//
// The data file is a contract: the viewer reads versions 1 and 2, and a version
// it does not know is refused with a message the reader sees, rather than drawn
// from keys whose meaning it cannot know.

import { test, expect } from "@playwright/test";
import { architectureData } from "./support/viewer.js";

test("a data file of an unknown schema version is refused with a visible message", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  data.schema_version = 99;
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

  await page.goto("architecture.html");

  await expect(page.getByRole("alert")).toContainText("schema_version 99");
});
