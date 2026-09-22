import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { onboardAsStudent } from "./helpers";

test.use({ serviceWorkers: "block" });

test.describe("Games section", () => {
  test("the sidebar and mobile bar both carry a Games entry", async ({ page, isMobile }) => {
    await onboardAsStudent(page);
    const nav = isMobile ? page.getByRole("navigation", { name: "Main" }) : page.getByRole("navigation", { name: "Main" }).first();
    await expect(nav.getByRole("link", { name: "Games" })).toBeVisible();
  });

  test("the page lists the pop quiz as a tile", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/games");
    await expect(page.getByRole("heading", { name: "Games", level: 1 })).toBeVisible();
    const tile = page.getByRole("button", { name: "Pop quiz" });
    await expect(tile).toBeVisible();
    await expect(tile).toContainText(/three wrong answers/);
  });

  test("picking the pop quiz tile opens the game", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Pop quiz" }).click();
    await expect(page.getByRole("dialog").getByRole("heading", { level: 1 })).toContainText("How well do you know your field?");
    await page.getByRole("button", { name: "Close the quiz" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });

  test("has no serious accessibility violations", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/games");
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });

  test("nothing scrolls sideways on a small phone", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await onboardAsStudent(page);
    await page.goto("/games");
    await page.waitForLoadState("networkidle");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
  });
});
