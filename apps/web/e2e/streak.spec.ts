import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { onboardAsStudent } from "./helpers";

test.describe("daily streak", () => {
  test("opening the app for the first time starts a one-day streak", async ({ page }) => {
    await onboardAsStudent(page);
    const badge = page.getByRole("img", { name: /day/ }).filter({ visible: true }).first();
    await expect(badge).toBeVisible();
    await expect(badge.getByTestId("streak-count")).toHaveText("1");
    await expect(badge).toHaveAccessibleName("1 day in a row");
  });

  test("reopening the app on the same day doesn't inflate the count", async ({ page }) => {
    await onboardAsStudent(page);
    const badge = page.getByRole("img", { name: /day/ }).filter({ visible: true }).first();
    await expect(badge.getByTestId("streak-count")).toHaveText("1");
    await page.reload();
    await expect(page.getByRole("img", { name: /day/ }).filter({ visible: true }).first().getByTestId("streak-count")).toHaveText("1");
  });

  test("the streak badge doesn't break the feed page's accessibility", async ({ page }) => {
    await onboardAsStudent(page);
    await expect(page.getByRole("img", { name: /day/ }).filter({ visible: true }).first()).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });
});
