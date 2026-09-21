import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";
import { onboardAsStudent } from "./helpers";

const item = (n: number, newsletter: boolean) => ({
  id: `a${n}`, title: `The quiet rise of brand playbooks, part ${n}`, url: `https://letter.example/p${n}`, summary: "An essay on how teams plan.",
  brief: { paragraphs: ["An essay on how brand teams plan their year."], pointers: ["Start with the customer"], note: null },
  source: { name: newsletter ? "Lenny's Newsletter" : "Marketing Dive", authority: 4 }, also_covered_by: [], published_at: new Date().toISOString(),
  score: 62, tier: "relevant", why_this_matters: "It mentions Brand Manager, a role you're targeting.", action: "Add one line about this to your notes for Brand Manager interviews.",
  matched: { companies: [], roles: ["Brand Manager"], industries: [], capabilities: [], topics: [] }, domains: ["Marketing"], saved: false, newsletter,
});

async function stubFeed(page: Page, newsletters: unknown[]) {
  const lenses: string[] = [];
  await page.route("**/api/feed/**", async (route: Route) => {
    const url = new URL(route.request().url());
    if (route.request().method() !== "GET" || url.pathname.endsWith("/saved")) return route.fallback();
    const lens = url.searchParams.get("lens") ?? "for_you";
    lenses.push(lens);
    const items = lens === "newsletters" ? newsletters : [item(1, false)];
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ lens, summary: { total: items.length, critical: 0, relevant: items.length, explore: 0 }, items, offset: 0, has_more: false }),
    });
  });
  return lenses;
}

// The app's service worker fetches the feed itself, where a test can't stand in for the server, so it is switched off here.
test.use({ serviceWorkers: "block" });

test.describe("newsletters section", () => {
  test("is a fourth tab next to For you, Companies and Skills", async ({ page }) => {
    await onboardAsStudent(page);
    const tabs = page.getByRole("tablist", { name: "Feed lens" }).getByRole("tab");
    await expect(tabs).toHaveText(["For you", "Companies", "Skills", "Newsletters"]);
  });

  test("shows newsletter posts with a label, asked for with the newsletters lens", async ({ page }) => {
    const lenses = await stubFeed(page, [item(7, true), item(8, true)]);
    await onboardAsStudent(page);
    await page.getByRole("tab", { name: "Newsletters" }).click();
    await expect(page.locator("article")).toHaveCount(2);
    await expect(page.locator("article").first()).toContainText("Newsletter");
    await expect(page.locator("article").first()).toContainText("Lenny's Newsletter");
    expect(lenses).toContain("newsletters");
  });

  test("news stories do not carry the newsletter label", async ({ page }) => {
    await stubFeed(page, []);
    await onboardAsStudent(page);
    await expect(page.locator("article").first()).not.toContainText("Newsletter");
  });

  test("says what this section is when nothing matches yet", async ({ page }) => {
    await stubFeed(page, []);
    await onboardAsStudent(page);
    await page.getByRole("tab", { name: "Newsletters" }).click();
    await expect(page.getByText("No newsletter posts match you yet")).toBeVisible();
    await expect(page.getByText(/Substack and other independent newsletters/)).toBeVisible();
  });

  test("a newsletter card opens its summary and has the listen controls like any story", async ({ page }) => {
    await stubFeed(page, [item(3, true)]);
    await onboardAsStudent(page);
    await page.getByRole("tab", { name: "Newsletters" }).click();
    const card = page.locator("article").first();
    await card.getByRole("button", { name: "Summary and pointers" }).click();
    await expect(card.getByRole("button", { name: /Listen to the summary/ })).toBeVisible();
  });

  test("the four tabs fit a 320px phone without scrolling sideways", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await stubFeed(page, [item(1, true)]);
    await onboardAsStudent(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
    const tab = page.getByRole("tab", { name: "Newsletters" });
    const box = (await tab.boundingBox())!;
    expect(box.x + box.width).toBeLessThanOrEqual(320);
    expect(box.height).toBeGreaterThanOrEqual(40);
  });

  test("has no serious accessibility violations", async ({ page }) => {
    await stubFeed(page, [item(1, true)]);
    await onboardAsStudent(page);
    await page.getByRole("tab", { name: "Newsletters" }).click();
    await expect(page.locator("article")).toHaveCount(1);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });
});
