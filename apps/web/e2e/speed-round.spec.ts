import { expect, test, type Page } from "@playwright/test";
import { ROUND_SECONDS, accuracy, applySpeedAnswer, newSpeedGame, speedShareCard, type SpeedGame } from "../src/lib/speed-round";
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

  test("the share card carries the score, accuracy and how many were answered", () => {
    let game: SpeedGame = newSpeedGame();
    game = applySpeedAnswer(game, q(1), 1).game; // right
    game = applySpeedAnswer(game, q(2), 0).game; // wrong
    const card = speedShareCard(game);
    expect(card).toMatchObject({ game: "SPEED ROUND", headlineLabel: "right", headline: "1", accent: "50%" });
    expect(card.stats).toContainEqual({ value: "2", label: "answered" });
  });
});

// readSpeedBest/saveSpeedIfBest touch window.localStorage, so a Node-context unit test can't exercise them
// (the same reason quiz.spec.ts's "rules" section never unit-tests readBest/saveIfBest either).

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

// ---- sharing a score -----------------------------------------------------------------------------------------------

/** The 60s round is timed off performance.now(), which Playwright's fake clock also advances, so the
 *  over screen (and the ShareBar on it) can be reached without a real minute of waiting. */
async function playToOver(page: Page) {
  await page.clock.install();
  await stubSpeedQuiz(page);
  await onboardAsStudent(page);
  await page.goto("/games");
  await page.getByRole("button", { name: "Speed Round" }).click();
  await dialog(page).getByRole("button", { name: "Start" }).click();
  await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 0");
  await dialog(page).getByRole("group").getByRole("button", { name: /The right answer/ }).click();
  await page.clock.fastForward(ROUND_SECONDS * 1000 + 500);
  await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("right in", { timeout: 3000 });
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
      expect(decodeURIComponent(href ?? "")).toContain("1 right in 60 seconds");
    }
  });

  test("Save image downloads a real picture", async ({ page }) => {
    await playToOver(page);
    const [download] = await Promise.all([page.waitForEvent("download"), dialog(page).getByRole("button", { name: "Save image" }).click()]);
    expect(download.suggestedFilename()).toBe("vantage-speed-round.png");
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
      const d = (window as unknown as { __shared: { title: string; text: string; url: string; files?: File[] }[] }).__shared[0];
      return { title: d.title, url: d.url, file: d.files?.[0]?.name, type: d.files?.[0]?.type };
    });
    expect(shared.title).toBe("My Vantage Speed Round score");
    expect(shared.url).toContain("/games");
    expect(shared.file).toBe("vantage-speed-round.png");
    expect(shared.type).toBe("image/png");
  });
});
