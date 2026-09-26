import { expect, test } from "@playwright/test";
import { agree } from "./helpers";

test.describe("adding a missing role or company", () => {
  test("a student can add a role and a company that aren't in the taxonomy yet", async ({ page }) => {
    await page.goto("/onboarding");
    await page.getByLabel("What's your name?").fill("Priya Nair");
    await page.getByRole("radio", { name: /I'm a student/ }).click();
    await agree(page);
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: /^Marketing/ }).click();
    await page.getByRole("button", { name: "Continue" }).click();

    const roleTitle = "Zzyxq Growth Wrangler";
    await page.getByPlaceholder("Search roles").fill(roleTitle);
    await page.getByRole("button", { name: /Can't find/ }).click();
    await page.getByRole("button", { name: "Add it", exact: true }).click();
    await expect(page.getByRole("button", { name: new RegExp(`Remove ${roleTitle}`) })).toBeVisible();
    await page.getByRole("button", { name: "Continue" }).click();

    const companyName = "Zzyxq Foods Pvt Ltd";
    await page.getByPlaceholder("Search companies").fill(companyName);
    await page.getByRole("button", { name: /Can't find/ }).click();
    await page.getByLabel("Website (optional)").fill("zzyxqfoods.example");
    await page.getByRole("button", { name: "Add it", exact: true }).click();
    await expect(page.getByRole("button", { name: new RegExp(`Remove ${companyName}`) })).toBeVisible();
    await page.getByRole("button", { name: "Continue" }).click();

    await page.getByPlaceholder("Search skills and tools").fill("Excel");
    await page.getByRole("button", { name: /^Excel/ }).first().click();
    await page.getByRole("button", { name: "Show me my feed" }).click();
    await page.waitForURL("**/feed");
    await expect(page.locator("article").first()).toBeVisible();
  });

  test("adding a role that already exists returns the existing one instead of a duplicate", async ({ page }) => {
    await page.goto("/onboarding");
    await page.getByLabel("What's your name?").fill("Rohan Das");
    await page.getByRole("radio", { name: /I'm a student/ }).click();
    await agree(page);
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: /^Marketing/ }).click();
    await page.getByRole("button", { name: "Continue" }).click();

    await page.getByPlaceholder("Search roles").fill("Brand Manager");
    await page.getByRole("button", { name: /Can't find/ }).click();
    await expect(page.getByRole("button", { name: /^Brand Manager$/ })).toBeVisible();
    await page.getByRole("button", { name: "Add it", exact: true }).click();
    await expect(page.getByRole("button", { name: /Remove Brand Manager/ })).toBeVisible();
  });
});
