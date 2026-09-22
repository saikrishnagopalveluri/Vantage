import { expect, test, type Page } from "@playwright/test";
import { accuracy, applySpeedAnswer, newSpeedGame, type SpeedGame } from "../src/lib/speed-round";
import type { QuizQuestion } from "../src/lib/quiz";
import { onboardAsStudent } from "./helpers";

const q = (n: number): QuizQuestion => ({
  id: `q${n}`, kind: "concept", prompt: `Question ${n}: which one is right?`, context: null,
  options: ["A wrong answer", "The right answer", "Another wrong one", "One more wrong"], answer: 1,
  explain: `Explanation ${n}.`, field: "Marketing", level: 3,
});

test.describe("rules", () => {
  test("a right pick scores, a wrong one does not, and nothing costs a life", () => {
    const right = applySpeedAnswer(newSpeedGame(), q(1), 1);
    expect(right.right).toBe(true);
    expect(right.game.correct).toBe(1);
    expect(right.game.answers).toHaveLength(1);

    const wrong = applySpeedAnswer(right.game, q(2), 0);
    expect(wrong.right).toBe(false);
    expect(wrong.game.correct).toBe(1); // unchanged
    expect(wrong.game.answers).toHaveLength(2);
  });

  test("accuracy is a whole-number percentage and never divides by zero", () => {
    expect(accuracy(newSpeedGame())).toBe(0);
    let game: SpeedGame = newSpeedGame();
    game = applySpeedAnswer(game, q(1), 1).game; // right
    game = applySpeedAnswer(game, q(2), 0).game; // wrong
    game = applySpeedAnswer(game, q(3), 1).game; // right
    expect(accuracy(game)).toBe(67);
  });
});

// readSpeedBest/saveSpeedIfBest touch window.localStorage, so a Node-context unit test can't exercise them
// (the same reason quiz.spec.ts's "rules" section never unit-tests readBest/saveIfBest either). Reaching the
// over screen needs the full 60s round to elapse, so that path isn't covered here yet either.

// ---- playing it ---------------------------------------------------------------------------------------------------------

async function stubSpeedQuiz(page: Page) {
  let counter = 0;
  await page.route("**/api/quiz/**", async (route) => {
    const questions = Array.from({ length: 10 }, () => q(counter++));
    return route.fulfill({ contentType: "application/json", body: JSON.stringify({ level: 3, questions }) });
  });
}

const dialog = (page: Page) => page.getByRole("dialog");

test.describe("playing Speed Round", () => {
  test("is listed on the Games page with its own tagline", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/games");
    const tile = page.getByRole("button", { name: "Speed Round" });
    await expect(tile).toBeVisible();
    await expect(tile).toContainText(/one minute/i);
  });

  test("starting it shows a question, and answering moves on to the next one by itself", async ({ page }) => {
    await stubSpeedQuiz(page);
    await onboardAsStudent(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Speed Round" }).click();
    await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("How many can you get in a minute?");
    await dialog(page).getByRole("button", { name: "Start" }).click();
    await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 0");
    await dialog(page).getByRole("group").getByRole("button", { name: /The right answer/ }).click();
    await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 1", { timeout: 3000 });
  });

  test("has no serious accessibility violations at the intro", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Speed Round" }).click();
    const AxeBuilder = (await import("@axe-core/playwright")).default;
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });
});
