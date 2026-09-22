import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { onboardAsStudent } from "./helpers";

// The desktop sidebar carries a copy too and is hidden on a phone, so take the first copy that is actually on screen.
const credit = (page: Page) => page.getByText(/Powered by\s+DOT Club,\s+IBS Hyderabad/).filter({ visible: true }).first();

async function logoLoaded(page: Page) {
  const logo = page.getByRole("img", { name: "DOT Club logo" }).first();
  await logo.scrollIntoViewIfNeeded();
  await expect(logo).toBeVisible();
  // A broken image has no natural size, so this proves the file is really served and decodes.
  await expect.poll(() => logo.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  return logo;
}

test.describe("DOT Club partner credit", () => {
  test("the home page names the partner and shows the logo", async ({ page }) => {
    await page.goto("/");
    await expect(credit(page)).toBeVisible();
    await logoLoaded(page);
  });

  test("the login page carries it too", async ({ page }) => {
    await page.goto("/login");
    await expect(credit(page)).toBeVisible();
    await logoLoaded(page);
  });

  test("signed in, the profile page carries it, which is where phones see it", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/profile");
    await expect(credit(page)).toBeVisible();
    await logoLoaded(page);
  });

  test("on a laptop the sidebar shows it on every page", async ({ page, isMobile }) => {
    test.skip(isMobile, "the sidebar is for wider screens");
    await onboardAsStudent(page);
    for (const path of ["/feed", "/explore", "/saved"]) {
      await page.goto(path);
      await expect(page.locator("aside").getByText(/Powered by\s+DOT Club/)).toBeVisible();
    }
  });

  test("a shared quiz score page credits it as well", async ({ page }) => {
    await page.goto("/quiz/share?s=100&c=1&k=1&l=1&t=0");
    await expect(credit(page)).toBeVisible();
    await logoLoaded(page);
  });

  test("the quiz intro credits it", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/profile");
    await page.getByRole("button", { name: "Play the pop quiz" }).click();
    await expect(page.getByRole("dialog").getByText(/Powered by\s+DOT Club,\s+IBS Hyderabad/)).toBeVisible();
  });

  test("the logo files are served, small, and in the right formats", async ({ request }) => {
    for (const [path, type, maxKb] of [
      ["/partners/dot-club-sm.webp", "image/webp", 40],
      ["/partners/dot-club-sm.png", "image/png", 120],
      ["/partners/dot-club.webp", "image/webp", 80],
    ] as const) {
      const res = await request.get(path);
      expect(res.status(), path).toBe(200);
      expect(res.headers()["content-type"], path).toContain(type);
      expect((await res.body()).byteLength, path).toBeLessThan(maxKb * 1024);
    }
  });

  test("the logo has a text name and sits on a light tile, so it is readable in a dark theme", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto("/login");
    const logo = await logoLoaded(page);
    await expect(logo).toHaveAttribute("alt", "DOT Club logo");
    const tile = logo.locator("xpath=ancestor::span[1]");
    expect(await tile.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe("rgb(255, 255, 255)");
  });

  test("the image reserves its space, so the page does not jump when it loads", async ({ page }) => {
    await page.goto("/login");
    const logo = page.getByRole("img", { name: "DOT Club logo" }).first();
    await expect(logo).toHaveAttribute("width", /\d+/);
    await expect(logo).toHaveAttribute("height", /\d+/);
  });

  for (const path of ["/", "/login"]) {
    test(`${path} still has no serious accessibility violations with the credit on it`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
      expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
    });
  }

  test("nothing scrolls sideways on a small phone", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    for (const path of ["/", "/login", "/quiz/share?s=1&c=1&k=1&l=1&t=0"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), path).toBeLessThanOrEqual(1);
    }
  });

  test("the preview picture people see on LinkedIn or X carries the credit as text", async ({ request }) => {
    const res = await request.get("/quiz/share/image?s=100&c=1&k=1&l=1&t=0");
    expect(res.status()).toBe(200);
    expect((await res.body()).byteLength).toBeGreaterThan(5000);
  });
});
