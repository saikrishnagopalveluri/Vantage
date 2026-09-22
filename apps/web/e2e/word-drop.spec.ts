import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { MAX_GUESSES, newWordState, pickWord, scoreGuess, submitGuess } from "../src/lib/word-drop";
import { onboardAsStudent } from "./helpers";

test.describe("rules", () => {
  test("only picks a clean single word within the length range", () => {
    const word = pickWord([
      { name: "Excel" },
      { name: "Power BI" }, // has a space: skipped
      { name: "SQL" }, // too short (under 4): skipped
      { name: "C++" }, // punctuation: skipped
      { name: "Tableau" },
    ]);
    expect(["EXCEL", "TABLEAU"]).toContain(word);
  });

  test("returns null when nothing in the batch is usable", () => {
    expect(pickWord([{ name: "Power BI" }, { name: "SQL" }, { name: "C++" }])).toBeNull();
  });

  test("scores letters correctly, including a repeated letter that's already spoken for by an exact match", () => {
    // Target EXCEL, guess LEVEL. The guess's own L (index 0) and E (index 1) aren't exact matches, but
    // EXCEL's own E at index 0 and C at index 2 are unmatched leftovers, so the guess's E (not its L,
    // which was already used up by the exact match at index 4) can still mark "present" against them.
    const states = scoreGuess("LEVEL", "EXCEL");
    expect(states).toEqual(["absent", "present", "absent", "correct", "correct"]);
  });

  test("a guess with no shared letters is all absent, and the exact word is all correct", () => {
    expect(scoreGuess("ZZZZZ", "EXCEL")).toEqual(["absent", "absent", "absent", "absent", "absent"]);
    expect(scoreGuess("EXCEL", "EXCEL")).toEqual(["correct", "correct", "correct", "correct", "correct"]);
  });

  test("six wrong guesses end the round; the right guess ends it early as a win", () => {
    let state = newWordState("EXCEL");
    for (let i = 0; i < MAX_GUESSES - 1; i++) state = submitGuess(state, "ZZZZZ");
    expect(state.status).toBe("playing");
    state = submitGuess(state, "ZZZZZ");
    expect(state.status).toBe("lost");
    expect(state.guesses).toHaveLength(MAX_GUESSES);

    const won = submitGuess(newWordState("EXCEL"), "EXCEL");
    expect(won.status).toBe("won");
    expect(won.guesses).toHaveLength(1);
  });

  test("a guess of the wrong length is ignored, not counted", () => {
    const state = submitGuess(newWordState("EXCEL"), "AB");
    expect(state.guesses).toHaveLength(0);
  });
});

// readWordBest/saveWordIfBest touch window.localStorage; see match-field.spec.ts and speed-round.spec.ts
// for why that isn't unit-tested in the Node-context test runner here either.

// ---- playing it ---------------------------------------------------------------------------------------------------------

async function stubCapabilities(page: Page) {
  await page.route("**/api/taxonomy/capabilities**", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify([{ id: "1", name: "Excel", kind: "tool" }]) }),
  );
}

const dialog = (page: Page) => page.getByRole("dialog");

// The app's service worker would otherwise answer /api/taxonomy/capabilities itself, ahead of this stub.
test.use({ serviceWorkers: "block" });

test.describe("playing Word Drop", () => {
  test("is listed on the Games page with its own tagline", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/games");
    const tile = page.getByRole("button", { name: "Word Drop" });
    await expect(tile).toBeVisible();
    await expect(tile).toContainText(/six tries/i);
  });

  test("a wrong guess of the right length is accepted, and the right guess wins", async ({ page }) => {
    // Onboarding does its own real skills search ("Excel"), so the stub goes on after, not before.
    await onboardAsStudent(page);
    await stubCapabilities(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Word Drop" }).click();
    await dialog(page).getByRole("button", { name: "Start" }).click();

    const input = dialog(page).getByLabel("Your guess");
    await expect(input).toBeVisible();

    await input.fill("ZEBRA"); // wrong, but 5 letters like EXCEL
    await dialog(page).getByRole("button", { name: "Guess" }).click();
    await expect(dialog(page).locator('[aria-live="off"]').getByText("1")).toBeVisible();

    await input.fill("EXCEL");
    await dialog(page).getByRole("button", { name: "Guess" }).click();
    await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("Solved in 2 guesses");
  });

  test("a guess of the wrong length shows a message instead of submitting", async ({ page }) => {
    await onboardAsStudent(page);
    await stubCapabilities(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Word Drop" }).click();
    await dialog(page).getByRole("button", { name: "Start" }).click();

    await dialog(page).getByLabel("Your guess").fill("AB");
    await dialog(page).getByRole("button", { name: "Guess" }).click();
    await expect(dialog(page).getByText("Needs to be 5 letters.")).toBeVisible();
  });

  test("has no serious accessibility violations at the intro and while playing", async ({ page }) => {
    await onboardAsStudent(page);
    await stubCapabilities(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Word Drop" }).click();
    await dialog(page).getByRole("heading", { level: 1 }).waitFor();
    await page.waitForTimeout(400); // the intro's .rise fade-in runs 320ms; let it finish before scanning colors
    let results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);

    await dialog(page).getByRole("button", { name: "Start" }).click();
    await expect(dialog(page).getByLabel("Your guess")).toBeVisible();
    results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });
});
