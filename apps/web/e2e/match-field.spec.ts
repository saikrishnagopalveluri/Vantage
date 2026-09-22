import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { MIN_PAIRS, isSolved, newMatchState, pickPairs, selectLeft, tryMatch } from "../src/lib/match-field";
import { onboardAsStudent } from "./helpers";

const company = (id: string, name: string, industry: string | null) => ({ id, name, industry: industry ? { name: industry } : null });

test.describe("rules", () => {
  test("picks companies with distinct industries, skipping ones with no industry or a repeat", () => {
    const pairs = pickPairs([
      company("1", "Alpha", "Consulting"),
      company("2", "Beta", "Consulting"), // same industry as Alpha: only one of them can be used
      company("3", "Gamma", "Finance"),
      company("4", "Delta", null), // no industry: skipped
      company("5", "Epsilon", "Retail"),
      company("6", "Zeta", "Tech"),
    ]);
    const industries = pairs.map((p) => p.right);
    expect(new Set(industries).size).toBe(industries.length); // every industry on screen is unique
    expect(pairs.length).toBeLessThanOrEqual(4); // Consulting, Finance, Retail, Tech: 4 distinct industries available
  });

  test("a right match locks the pair in; a wrong one clears the pick and costs nothing else", () => {
    const pairs = [{ id: "a", left: "Alpha", right: "Consulting" }, { id: "b", left: "Beta", right: "Finance" }];
    let state = newMatchState(pairs);
    state = selectLeft(state, "a");
    expect(state.selectedLeft).toBe("a");

    const wrong = tryMatch(state, "b");
    expect(wrong.correct).toBe(false);
    expect(wrong.state.matched.size).toBe(0);
    expect(wrong.state.selectedLeft).toBeNull(); // the pick clears either way
    expect(wrong.state.mistakes).toBe(1);

    state = selectLeft(wrong.state, "a");
    const right = tryMatch(state, "a");
    expect(right.correct).toBe(true);
    expect(right.state.matched.has("a")).toBe(true);
    expect(isSolved(right.state)).toBe(false); // "b" is still unmatched
  });

  test("tapping the same company twice deselects it, and a matched one can't be reselected", () => {
    const pairs = [{ id: "a", left: "Alpha", right: "Consulting" }];
    let state = newMatchState(pairs);
    state = selectLeft(state, "a");
    state = selectLeft(state, "a");
    expect(state.selectedLeft).toBeNull();

    state = selectLeft(state, "a");
    state = tryMatch(state, "a").state;
    expect(isSolved(state)).toBe(true);
    state = selectLeft(state, "a");
    expect(state.selectedLeft).toBeNull(); // matched companies don't select
  });
});

// ---- playing it ---------------------------------------------------------------------------------------------------------

const INDUSTRIES = ["Consulting", "Finance & Banking", "Marketing", "Software Engineering", "Retail"];

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

  test("selecting a company then its industry matches the pair, and a wrong pick doesn't", async ({ page }) => {
    // Onboarding does its own real company search ("Hindustan Unilever"), so the stub goes on after,
    // not before, or it would swallow that search too.
    await onboardAsStudent(page);
    await stubCompanies(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Match the Field" }).click();
    await dialog(page).getByRole("button", { name: "Start" }).click();

    const companies = dialog(page).getByRole("list", { name: "Companies" }).getByRole("button");
    const industries = dialog(page).getByRole("list", { name: "Industries" }).getByRole("button");
    await expect(companies).toHaveCount(MIN_PAIRS + 1); // all 5 distinct industries stub in

    // A wrong pick: leaves both pickable and doesn't crash the round.
    await companies.first().click();
    const firstName = (await companies.first().innerText()).trim();
    const correctIndustry = INDUSTRIES[Number(firstName.replace("Company ", ""))];
    await industries.filter({ hasNotText: correctIndustry }).first().click();
    await expect(companies.first()).toBeEnabled();

    // Match every pair correctly, by name.
    for (let i = 0; i < (await companies.count()); i++) {
      const name = (await companies.nth(i).innerText()).trim();
      const industry = INDUSTRIES[Number(name.replace("Company ", ""))];
      await companies.nth(i).click();
      await industries.filter({ hasText: industry }).click();
    }
    await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("All five in");
  });

  test("has no serious accessibility violations at the intro and while playing", async ({ page }) => {
    await onboardAsStudent(page);
    await stubCompanies(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Match the Field" }).click();
    let results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);

    await dialog(page).getByRole("button", { name: "Start" }).click();
    await expect(dialog(page).getByRole("list", { name: "Companies" }).getByRole("button")).toHaveCount(MIN_PAIRS + 1);
    results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });
});
