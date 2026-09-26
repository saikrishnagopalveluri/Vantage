import { expect, test, type Page } from "@playwright/test";
import { onboardAsStudent } from "./helpers";

async function userId(page: Page): Promise<string> {
  return (await page.evaluate(() => localStorage.getItem("vantage.userId")))!;
}

test.describe("achievement badges", () => {
  test("a fresh student sees every badge locked, at the right progress", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/profile");

    const streak = page.getByRole("listitem").filter({ hasText: "On a Roll" });
    await expect(streak).toContainText("1 / 3"); // onboarding's own visit already touched the streak
    await expect(streak.getByRole("button", { name: "Share" })).toHaveCount(0);

    const reading = page.getByRole("listitem").filter({ hasText: "Getting Started" });
    await expect(reading).toContainText("0 / 10");
    await expect(page.getByText("0 of 12")).toBeVisible();
  });

  test("reading 10 articles unlocks the badge, and it can be shared as an image", async ({ page }) => {
    await onboardAsStudent(page);
    const id = await userId(page);

    const feed = await page.request.get(`/api/feed/${id}?lens=for_you&offset=0&limit=20`, { headers: { "X-User-Id": id } });
    const items: { id: string }[] = (await feed.json()).items;
    expect(items.length).toBeGreaterThanOrEqual(10);
    for (const item of items.slice(0, 10)) {
      const res = await page.request.post(`/api/feed/${id}/interaction`, {
        headers: { "X-User-Id": id },
        data: { article_id: item.id, action: "read" },
      });
      expect(res.ok()).toBe(true);
    }

    await page.goto("/profile");
    const badge = page.getByRole("listitem").filter({ hasText: "Getting Started" });
    await expect(badge).toContainText("10 articles read");
    await expect(badge).not.toContainText("0 / 10");
    await badge.getByRole("button", { name: "Share" }).click();

    const [download] = await Promise.all([page.waitForEvent("download"), badge.getByRole("button", { name: "Save image" }).click()]);
    expect(download.suggestedFilename()).toBe("vantage-articles_10.png");
  });

  test("a user cannot read or log time for someone else's badges", async ({ page }) => {
    await onboardAsStudent(page);
    const res = await page.request.get("/api/badges/not-my-id", { headers: { "X-User-Id": await userId(page) } });
    expect(res.status()).toBe(403);
  });
});
