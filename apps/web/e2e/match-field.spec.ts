import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { BOARD_SIZE, ROUND_SECONDS, accuracy, buildQueue, fillBoard, matchShareCard, newMatchState, selectLeft, tryMatch, type MatchState } from "../src/lib/match-field";
import { onboardAsStudent } from "./helpers";

const company = (id: string, name: string, industry: string | null) => ({ id, name, industry: industry ? { name: industry } : null });

test.describe("rules", () => {
  test("the board holds companies with distinct industries, skipping ones with no industry or a repeat", () => {
    const state = newMatchState([
      company("1", "Alpha", "Consulting"),
      company("2", "Beta", "Consulting"), // same industry as Alpha: only one of them can be on screen at once
      company("3", "Gamma", "Finance"),
      company("4", "Delta", null), // no industry: skipped
      company("5", "Epsilon", "Retail"),
      company("6", "Zeta", "Tech"),
    ]);
    const industries = state.board.map((p) => p.right);
    expect(new Set(industries).size).toBe(industries.length); // every industry on screen is unique
    expect(state.board.length).toBeLessThanOrEqual(4); // Consulting, Finance, Retail, Tech: 4 distinct industries available
  });

  test("a right match scores, clears the pair off the board and slides in a replacement", () => {
    const pool = [company("a", "Alpha", "Consulting"), company("b", "Beta", "Finance"), company("c", "Gamma", "Retail")];
    const { board, queue } = fillBoard([], buildQueue(pool), 2); // a 2-wide board, one pair left in the queue
    let state: MatchState = { board, leftOrder: board.map((p) => p.id), rightOrder: board.map((p) => p.id), queue, selectedLeft: null, correct: 0, mistakes: 0 };
    const firstId = board[0].id;
    state = selectLeft(state, firstId);
    const right = tryMatch(state, firstId);
    expect(right.correct).toBe(true);
    expect(right.state.correct).toBe(1);
    expect(right.state.board.some((p) => p.id === firstId)).toBe(false); // solved pair is gone
    expect(right.state.board).toHaveLength(2); // refilled from the queue
  });

  test("a wrong pair clears the pick, costs nothing but a mistake, and the clock never stops for it", () => {
    const pool = [company("a", "Alpha", "Consulting"), company("b", "Beta", "Finance")];
    const state = newMatchState(pool);
    const [first, second] = state.board;
    const selected = selectLeft(state, first.id);
    const wrong = tryMatch(selected, second.id);
    expect(wrong.correct).toBe(false);
    expect(wrong.state.mistakes).toBe(1);
    expect(wrong.state.selectedLeft).toBeNull();
    expect(wrong.state.board).toHaveLength(2); // nothing removed
  });

  test("tapping the same company twice deselects it", () => {
    const state = newMatchState([company("a", "Alpha", "Consulting")]);
    const id = state.board[0].id;
    let s = selectLeft(state, id);
    expect(s.selectedLeft).toBe(id);
    s = selectLeft(s, id);
    expect(s.selectedLeft).toBeNull();
  });

  test("accuracy is a whole-number percentage and never divides by zero", () => {
    const empty = newMatchState([]);
    expect(accuracy(empty)).toBe(0);
    expect(accuracy({ ...empty, correct: 3, mistakes: 1 })).toBe(75);
  });

  test("the share card carries how many were matched and the accuracy", () => {
    const card = matchShareCard({ ...newMatchState([]), correct: 4, mistakes: 1 });
    expect(card).toMatchObject({ game: "MATCH THE FIELD", headlineLabel: "matched", headline: "4", accent: "80%" });
  });
});

// readMatchBest/saveMatchIfBest touch window.localStorage, so a Node-context unit test can't exercise them
// (the same reason speed-round.spec.ts's "rules" section skips them too).

// ---- playing it ---------------------------------------------------------------------------------------------------------

const INDUSTRIES = ["Consulting", "Finance & Banking", "Marketing", "Software Engineering", "Retail", "Logistics"];

async function stubCompanies(page: Page) {
  await page.route("**/api/taxonomy/companies**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(INDUSTRIES.map((industry, i) => company(`c${i}`, `Company ${i}`, industry))),
    }),
  );
}

const dialog = (page: Page) => page.getByRole("dialog");

// The app's service worker would otherwise answer /api/taxonomy/companies itself, ahead of this stub.
test.use({ serviceWorkers: "block" });

test.describe("playing Match the Field", () => {
  test("is listed on the Games page with its own tagline", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/games");
    const tile = page.getByRole("button", { name: "Match the Field" });
    await expect(tile).toBeVisible();
    await expect(tile).toContainText(/industry/i);
  });

  test("selecting a company then its industry matches the pair and refills the board, and a wrong pick doesn't", async ({ page }) => {
    // Onboarding does its own real company search ("Hindustan Unilever"), so the stub goes on after,
    // not before, or it would swallow that search too.
    await onboardAsStudent(page);
    await stubCompanies(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Match the Field" }).click();
    await dialog(page).getByRole("button", { name: "Start" }).click();

    const companies = dialog(page).getByRole("list", { name: "Companies" }).getByRole("button");
    const industries = dialog(page).getByRole("list", { name: "Industries" }).getByRole("button");
    await expect(companies).toHaveCount(BOARD_SIZE);

    // A wrong pick: leaves the board full and doesn't crash the round.
    await companies.first().click();
    const firstName = (await companies.first().innerText()).trim();
    const correctIndustry = INDUSTRIES[Number(firstName.replace("Company ", ""))];
    await industries.filter({ hasNotText: correctIndustry }).first().click();
    await expect(companies.first()).toBeEnabled();
    await expect(companies).toHaveCount(BOARD_SIZE);

    // A right pick: the matched counter climbs and the board stays full (refilled from the 6th company).
    await companies.first().click();
    await industries.filter({ hasText: correctIndustry }).click();
    await expect(dialog(page).getByText("matched")).toBeVisible();
    await expect(companies).toHaveCount(BOARD_SIZE);
  });

  test("has no serious accessibility violations at the intro and while playing", async ({ page }) => {
    await onboardAsStudent(page);
    await stubCompanies(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Match the Field" }).click();
    let results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);

    await dialog(page).getByRole("button", { name: "Start" }).click();
    await expect(dialog(page).getByRole("list", { name: "Companies" }).getByRole("button")).toHaveCount(BOARD_SIZE);
    results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });
});

// ---- sharing a score -----------------------------------------------------------------------------------------------

/** The 60s round is timed off performance.now(), which Playwright's fake clock also advances, so the
 *  over screen (and the ShareBar on it) can be reached without a real minute of waiting. */
async function playToOver(page: Page) {
  await page.clock.install();
  await onboardAsStudent(page);
  await stubCompanies(page);
  await page.goto("/games");
  await page.getByRole("button", { name: "Match the Field" }).click();
  await dialog(page).getByRole("button", { name: "Start" }).click();

  const companies = dialog(page).getByRole("list", { name: "Companies" }).getByRole("button");
  const industries = dialog(page).getByRole("list", { name: "Industries" }).getByRole("button");
  await expect(companies).toHaveCount(BOARD_SIZE);
  const firstName = (await companies.first().innerText()).trim();
  const correctIndustry = INDUSTRIES[Number(firstName.replace("Company ", ""))];
  await companies.first().click();
  await industries.filter({ hasText: correctIndustry }).click();
  await expect(dialog(page).getByText("matched")).toBeVisible();

  await page.clock.fastForward(ROUND_SECONDS * 1000 + 500);
  await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("matched in", { timeout: 3000 });
}

test.describe("sharing a score", () => {
  test("the share links point at the Games page, and WhatsApp/X also carry the score", async ({ page }) => {
    await playToOver(page);
    const section = dialog(page).getByRole("region", { name: "Post your score" });
    for (const [name, host] of [["LinkedIn", "linkedin.com"], ["X", "twitter.com"], ["WhatsApp", "wa.me"]] as const) {
      const link = section.getByRole("link", { name });
      await expect(link).toHaveAttribute("href", new RegExp(host));
      expect(decodeURIComponent((await link.getAttribute("href")) ?? "")).toContain("/games");
    }
    // LinkedIn's share-offsite endpoint only takes a URL, not pre-filled text — only X and WhatsApp carry the score.
    for (const name of ["X", "WhatsApp"] as const) {
      const href = await section.getByRole("link", { name }).getAttribute("href");
      expect(decodeURIComponent(href ?? "")).toContain("1 company to their industry");
    }
  });

  test("Save image downloads a real picture", async ({ page }) => {
    await playToOver(page);
    const [download] = await Promise.all([page.waitForEvent("download"), dialog(page).getByRole("button", { name: "Save image" }).click()]);
    expect(download.suggestedFilename()).toBe("vantage-match-the-field.png");
    const path = await download.path();
    const fs = await import("node:fs");
    const bytes = fs.readFileSync(path!);
    expect(bytes.subarray(1, 4).toString()).toBe("PNG");
    expect(bytes.readUInt32BE(16)).toBe(1080);
    expect(bytes.readUInt32BE(20)).toBe(1350);
  });

  test("the share button uses the phone's own sheet, with the picture attached, when there is one", async ({ page }) => {
    await page.addInitScript(() => {
      const calls: unknown[] = [];
      (window as unknown as { __shared: unknown[] }).__shared = calls;
      Object.defineProperty(navigator, "share", { configurable: true, value: async (data: unknown) => void calls.push(data) });
      Object.defineProperty(navigator, "canShare", { configurable: true, value: () => true });
    });
    await playToOver(page);
    await dialog(page).getByRole("button", { name: "Share", exact: true }).click();
    await expect.poll(() => page.evaluate(() => (window as unknown as { __shared: unknown[] }).__shared.length)).toBe(1);
    const shared = await page.evaluate(() => {
      const d = (window as unknown as { __shared: { title: string; url: string; files?: File[] }[] }).__shared[0];
      return { title: d.title, url: d.url, file: d.files?.[0]?.name, type: d.files?.[0]?.type };
    });
    expect(shared.title).toBe("My Vantage Match the Field score");
    expect(shared.url).toContain("/games");
    expect(shared.file).toBe("vantage-match-the-field.png");
    expect(shared.type).toBe("image/png");
  });
});
