import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import {
  LIVES,
  RANKS,
  accuracy,
  applyAnswer,
  intents,
  isOver,
  levelFor,
  newGame,
  nextRank,
  parseResult,
  pointsFor,
  rankFor,
  resultOf,
  resultQuery,
  secondsFor,
  shareText,
  shareUrl,
  type QuizQuestion,
} from "../src/lib/quiz";
import { onboardAsStudent } from "./helpers";

const q = (n: number, level = 1): QuizQuestion => ({
  id: `q${n}`, kind: "concept", prompt: `Question ${n}: which one is right?`, context: null,
  options: ["A wrong answer", "The right answer", "Another wrong one", "One more wrong"], answer: 1,
  explain: `Explanation ${n}.`, field: "Marketing", level,
});

// ---- the rules, without a browser -------------------------------------------------------------------------------------

test.describe("rules", () => {
  test("a new level every four right answers, up to ten", () => {
    expect([0, 3, 4, 7, 8, 35, 36, 200].map(levelFor)).toEqual([1, 1, 2, 2, 3, 9, 10, 10]);
  });

  test("less time as the level rises, never under eight seconds", () => {
    expect([1, 2, 3, 5, 7, 8, 10].map(secondsFor)).toEqual([22, 20, 18, 14, 10, 8, 8]);
  });

  test("points: base rises with level, speed adds, streak multiplies up to double", () => {
    expect(pointsFor({ level: 1, secondsLeft: 0, streak: 0 })).toBe(110);
    expect(pointsFor({ level: 1, secondsLeft: 20, streak: 0 })).toBe(210);
    expect(pointsFor({ level: 1, secondsLeft: 20, streak: 5 })).toBe(315);
    expect(pointsFor({ level: 1, secondsLeft: 20, streak: 50 })).toBe(420); // capped at x2
    expect(pointsFor({ level: 3, secondsLeft: 0, streak: 0 })).toBeGreaterThan(pointsFor({ level: 1, secondsLeft: 0, streak: 0 }));
    expect(pointsFor({ level: 1, secondsLeft: -5, streak: 0 })).toBe(110); // never negative time
  });

  test("titles by right answers, and the next one to aim for", () => {
    expect([0, 4, 5, 9, 10, 25, 49, 50, 70, 500].map((n) => rankFor(n).title)).toEqual([
      "Intern", "Intern", "Analyst", "Analyst", "Associate", "Senior Manager", "Director", "Partner", "Managing Director", "Managing Director",
    ]);
    expect(nextRank(3)).toEqual({ title: "Analyst", needed: 2 });
    expect(nextRank(70)).toBeNull();
  });

  test("a right answer scores and extends the streak", () => {
    const { game, points } = applyAnswer(newGame(), q(1), 1, 10);
    expect(game).toMatchObject({ lives: LIVES, correct: 1, streak: 1, bestStreak: 1, level: 1 });
    expect(points).toBe(game.score);
    expect(points).toBeGreaterThan(0);
  });

  test("a wrong answer costs a life, scores nothing and ends the streak", () => {
    let game = applyAnswer(newGame(), q(1), 1, 10).game;
    game = applyAnswer(game, q(2), 1, 10).game;
    const before = game.score;
    const result = applyAnswer(game, q(3), 0, 10);
    expect(result.game).toMatchObject({ lives: LIVES - 1, streak: 0, bestStreak: 2, score: before });
    expect(result.points).toBe(0);
  });

  test("running out of time counts as wrong", () => {
    const { game } = applyAnswer(newGame(), q(1), null, 0);
    expect(game.lives).toBe(LIVES - 1);
    expect(game.answers[0]).toMatchObject({ picked: null, right: false });
  });

  test("three wrong answers end the game, whenever they come", () => {
    let game = newGame();
    for (const pick of [1, 0, 1, 1, 2, 3]) {
      if (!isOver(game)) game = applyAnswer(game, q(game.answers.length), pick, 5).game;
    }
    expect(isOver(game)).toBe(true);
    expect(game.lives).toBe(0);
    expect(game.answers).toHaveLength(6); // right, wrong, right, right, wrong, wrong
  });

  test("the fourth right answer raises the level", () => {
    let game = newGame();
    const flags: boolean[] = [];
    for (let i = 0; i < 5; i++) {
      const r = applyAnswer(game, q(i), 1, 5);
      game = r.game;
      flags.push(r.leveledUp);
    }
    expect(flags).toEqual([false, false, false, true, false]);
    expect(game.level).toBe(2);
  });

  test("a long game never breaks the rules: fifty right answers reach a title, level ten and no negative numbers", () => {
    let game = newGame();
    for (let i = 0; i < 50; i++) game = applyAnswer(game, q(i), 1, 3).game;
    expect(game.level).toBe(10);
    expect(rankFor(game.correct).title).toBe("Partner");
    expect(game.score).toBeGreaterThan(0);
    expect(accuracy(game)).toBe(100);
  });

  test("accuracy is a whole-number percentage and never divides by zero", () => {
    expect(accuracy(newGame())).toBe(0);
    let game = applyAnswer(newGame(), q(1), 1, 5).game;
    game = applyAnswer(game, q(2), 0, 5).game;
    game = applyAnswer(game, q(3), 0, 5).game;
    expect(accuracy(game)).toBe(33);
  });
});

test.describe("sharing", () => {
  const game = (() => {
    let g = newGame();
    for (let i = 0; i < 12; i++) g = applyAnswer(g, q(i), 1, 8).game;
    return applyAnswer(g, q(99), 0, 8).game;
  })();

  test("the result in the link is only numbers and a title index", () => {
    const r = resultOf(game);
    expect(resultQuery(r)).toMatch(/^s=\d+&c=12&k=12&l=4&t=2$/);
    expect(shareUrl("https://vantage.example", r)).toBe(`https://vantage.example/quiz/share?${resultQuery(r)}`);
  });

  test("the post reads like a person wrote it and names no one", () => {
    const text = shareText(resultOf(game));
    expect(text).toContain("Vantage pop quiz");
    expect(text).toContain("12 right");
    expect(text).toContain(RANKS[2].title);
    expect(text).not.toMatch(/@|email|profile|password/i);
    expect(text).not.toContain("—");
  });

  test("scores are written the Indian way", () => {
    expect(shareText({ score: 123456, correct: 1, bestStreak: 1, level: 1, rank: 0 })).toContain("1,23,456");
  });

  test("links to each network carry the address and the text, safely encoded", () => {
    const url = "https://v.example/quiz/share?s=10&c=1&k=1&l=1&t=0";
    expect(intents.linkedin(url)).toBe(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`);
    expect(intents.x("A & B", url)).toContain("text=A%20%26%20B");
    expect(intents.whatsapp("hi", url)).toContain(encodeURIComponent(`hi ${url}`));
  });

  const hostile: Record<string, string | string[] | undefined>[] = [
    { s: "<script>alert(1)</script>", c: "x", k: "", l: "abc", t: "9" },
    { s: "-500", c: "-1", k: "-1", l: "-3", t: "-2" },
    { s: "99999999999999999", c: "1e99", k: "Infinity", l: "1000", t: "500" },
    { s: ["12", "34"], c: undefined },
    {},
  ];
  for (const [i, input] of hostile.entries()) {
    test(`hostile input #${i} becomes safe numbers in range`, () => {
      const r = parseResult(input);
      for (const n of [r.score, r.correct, r.bestStreak, r.level, r.rank]) expect(Number.isInteger(n)).toBe(true);
      expect(r.score).toBeGreaterThanOrEqual(0);
      expect(r.score).toBeLessThanOrEqual(999_999);
      expect(r.level).toBeGreaterThanOrEqual(1);
      expect(r.level).toBeLessThanOrEqual(10);
      expect(r.rank).toBeGreaterThanOrEqual(0);
      expect(r.rank).toBeLessThan(RANKS.length);
    });
  }
});

// ---- the shared page and its preview picture -----------------------------------------------------------------------------

test.describe("shared result page", () => {
  const url = "/quiz/share?s=2340&c=14&k=9&l=4&t=2";

  test("shows the score and title to anyone, signed in or not", async ({ page }) => {
    await page.goto(url);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Someone scored 2,340");
    await expect(page.getByLabel("The result")).toContainText("Associate");
    await expect(page.getByLabel("The result")).toContainText("14");
    await expect(page.getByRole("link", { name: "Try Vantage" })).toHaveAttribute("href", "/");
  });

  test("has the tags social networks read for a preview card", async ({ page }) => {
    await page.goto(url);
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", "2,340 points on the Vantage pop quiz");
    await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /\/quiz\/share\/image\?s=2340&c=14&k=9&l=4&t=2$/);
    await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", "summary_large_image");
    await expect(page.locator('meta[property="og:description"]')).toHaveAttribute("content", /14 right.*Associate/);
  });

  test("is kept out of search results", async ({ page }) => {
    await page.goto(url);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  });

  test("the preview picture is a real image of the right size", async ({ request }) => {
    const res = await request.get("/quiz/share/image?s=2340&c=14&k=9&l=4&t=2");
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("image/png");
    const body = await res.body();
    expect(body.byteLength).toBeGreaterThan(5000);
    expect(body.subarray(1, 4).toString()).toBe("PNG");
    expect(body.readUInt32BE(16)).toBe(1200); // width and height sit in the PNG header
    expect(body.readUInt32BE(20)).toBe(630);
  });

  test("nothing typed into the link is run or shown as markup", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto("/quiz/share?s=%3Cscript%3Ewindow.__x%3D1%3C%2Fscript%3E&c=%22%3E%3Cimg%20src%3Dx%20onerror%3Dwindow.__x%3D1%3E&t=%3Cb%3E");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Someone scored 0");
    expect(await page.evaluate(() => (window as unknown as { __x?: number }).__x)).toBeUndefined();
    expect(await page.locator('main img:not([alt="DOT Club logo"]), main script').count()).toBe(0);
    expect(errors).toEqual([]);
  });

  test("a missing or broken link still gives a sensible page and image", async ({ page, request }) => {
    await page.goto("/quiz/share");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Someone scored 0");
    expect((await request.get("/quiz/share/image?s=abc")).status()).toBe(200);
  });

  test("has no serious accessibility violations", async ({ page }) => {
    await page.goto(url);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });
});

// ---- the game in a browser -------------------------------------------------------------------------------------------------

interface Requests {
  levels: number[];
  excludes: string[][];
}

/** Answers quiz requests with predictable questions, and remembers what was asked. */
async function stubQuiz(page: Page, options: { fail?: boolean } = {}): Promise<Requests> {
  const seen: Requests = { levels: [], excludes: [] };
  let counter = 0;
  await page.route("**/api/quiz/**", async (route) => {
    const url = new URL(route.request().url());
    if (options.fail) return route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "boom" }) });
    const level = Number(url.searchParams.get("level"));
    seen.levels.push(level);
    seen.excludes.push((url.searchParams.get("exclude") ?? "").split(",").filter(Boolean));
    const questions = Array.from({ length: 8 }, () => q(counter++, level));
    return route.fulfill({ contentType: "application/json", body: JSON.stringify({ level, questions }) });
  });
  return seen;
}

/** Counts the sounds the game asks for, without making any noise. */
async function stubAudio(page: Page) {
  await page.addInitScript(() => {
    let started = 0;
    class Ctx {
      state = "running";
      currentTime = 0;
      destination = {};
      resume() {}
      createOscillator() {
        return { type: "", frequency: { setValueAtTime() {} }, connect: (n: unknown) => n, start: () => started++, stop() {} };
      }
      createGain() {
        return { gain: { setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect: (n: unknown) => n };
      }
    }
    Object.defineProperty(window, "AudioContext", { value: Ctx, configurable: true });
    (window as unknown as { __tones: () => number }).__tones = () => started;
  });
}

const tones = (page: Page) => page.evaluate(() => (window as unknown as { __tones: () => number }).__tones());
const dialog = (page: Page) => page.getByRole("dialog");
const right = (page: Page) => dialog(page).getByRole("button", { name: /The right answer/ });
const wrong = (page: Page) => dialog(page).getByRole("button", { name: /A wrong answer/ });
const lives = (page: Page, n: number) => expect(dialog(page).getByRole("img", { name: `${n} of ${LIVES} lives left` })).toBeVisible();

async function openByTripleTap(page: Page) {
  const logo = page.getByRole("link", { name: /Vantage/ }).filter({ visible: true }).first();
  await logo.click({ clickCount: 3, delay: 40 });
  await expect(dialog(page)).toBeVisible();
}

async function start(page: Page) {
  await dialog(page).getByRole("button", { name: "Start" }).click();
  await expect(right(page)).toBeVisible();
}

test.describe("opening the game", () => {
  test("tapping the logo three times opens the quiz", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await expect(dialog(page)).toHaveCount(0);
    await openByTripleTap(page);
    await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("How well do you know your field?");
  });

  test("two taps are not enough, and neither are three that are spread out", async ({ page }) => {
    await onboardAsStudent(page);
    const logo = page.getByRole("link", { name: /Vantage/ }).filter({ visible: true }).first();
    await logo.click();
    await logo.click();
    await page.waitForTimeout(300);
    await expect(dialog(page)).toHaveCount(0);
    await page.waitForTimeout(1000);
    await logo.click();
    await page.waitForTimeout(900);
    await logo.click();
    await page.waitForTimeout(900);
    await logo.click();
    await expect(dialog(page)).toHaveCount(0);
  });

  test("the Profile page has a plain button for it too", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await page.goto("/profile");
    await page.getByRole("button", { name: "Play the pop quiz" }).click();
    await expect(dialog(page)).toBeVisible();
  });

  test("the intro explains the rules and how to leave", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await expect(dialog(page)).toContainText(/three wrong/i);
    await expect(dialog(page)).toContainText("22s");
    await expect(dialog(page).getByRole("button", { name: "Close the quiz" })).toBeVisible();
    await dialog(page).getByRole("button", { name: "Close the quiz" }).click();
    await expect(dialog(page)).toHaveCount(0);
  });

  test("focus is trapped inside the game and the page behind cannot be reached", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press("Tab");
      // Focus stays in the dialog, or leaves the page for the browser's own toolbar (then the page reports the body). It never reaches the page behind.
      expect(await page.evaluate(() => document.activeElement === document.body || !!document.activeElement?.closest("dialog"))).toBe(true);
    }
  });
});

test.describe("playing", () => {
  test("a right answer scores, shows why, and moves on by itself", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 0");
    await expect(dialog(page)).toContainText("Level 1");
    await right(page).click();
    await expect(dialog(page)).toContainText(/Correct\. \+\d+/);
    await expect(dialog(page)).toContainText("Explanation 0.");
    await lives(page, 3);
    await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 1", { timeout: 6000 });
  });

  test("a wrong answer costs a life, shows the right one and waits for you", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await wrong(page).click();
    await expect(dialog(page)).toContainText("Not quite.");
    await expect(dialog(page)).toContainText("The answer is The right answer.");
    await lives(page, 2);
    await page.waitForTimeout(2800);
    await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 0"); // still there: no auto-advance on a miss
    await dialog(page).getByRole("button", { name: "Next question" }).click();
    await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 1");
  });

  test("keys 1 to 4 and A to D answer", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await page.keyboard.press("2");
    await expect(dialog(page)).toContainText(/Correct/);
    await dialog(page).getByRole("button", { name: /Next question/ }).click().catch(() => {});
    await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 1", { timeout: 6000 });
    await page.keyboard.press("a");
    await expect(dialog(page)).toContainText("Not quite.");
  });

  test("the hearts, the score and the streak follow the play", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    for (let i = 0; i < 3; i++) {
      await right(page).click();
      await expect(dialog(page)).toContainText(/Correct/);
      await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText(`Question ${i + 1}`, { timeout: 6000 });
    }
    await expect(dialog(page)).toContainText("Streak 3");
    await wrong(page).click();
    await expect(dialog(page)).not.toContainText("Streak 3");
    await lives(page, 2);
  });

  test("four right answers raise the level, and the very next question is already a harder one", async ({ page }) => {
    const asked = await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    for (let i = 0; i < 4; i++) {
      await right(page).click();
      await expect(dialog(page)).toContainText(/Correct/);
      if (i < 3) await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText(`Question ${i + 1}`, { timeout: 6000 });
    }
    await expect(dialog(page)).toContainText("Level 2. Harder questions and less time from here.");
    // The four easy questions that were still queued are replaced by a batch asked for at level 2.
    await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 8", { timeout: 8000 });
    await expect(dialog(page)).toContainText("Level 2");
    expect(asked.levels[0]).toBe(1);
    expect(asked.levels).toContain(2);
  });

  test("more questions are fetched before the queue runs dry, and never repeat what was already asked", async ({ page }) => {
    const asked = await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    // Three right and two wrong keeps the level at 1, so the queue is not replaced by a level-up and the top-up can be seen.
    for (const [i, correct] of [true, false, true, false, true].entries()) {
      await (correct ? right(page) : wrong(page)).click();
      if (!correct) await dialog(page).getByRole("button", { name: "Next question" }).click();
      await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText(`Question ${i + 1}`, { timeout: 6000 });
    }
    expect(asked.levels.length).toBeGreaterThanOrEqual(2);
    expect(asked.excludes[1]).toEqual(expect.arrayContaining(["q0", "q1", "q7"])); // the ids seen so far are sent back
  });

  test("running out of time counts as a wrong answer", async ({ page }) => {
    test.setTimeout(90_000);
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await expect(dialog(page)).toContainText("Time's up.", { timeout: 30_000 });
    await lives(page, 2);
  });

  test("Escape asks before leaving mid-game, and keeping on playing works", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await right(page).click();
    await page.keyboard.press("Escape");
    await expect(dialog(page).getByRole("alertdialog", { name: "Leave the quiz?" })).toBeVisible();
    await dialog(page).getByRole("button", { name: "Keep playing" }).click();
    await expect(dialog(page)).toBeVisible();
    await page.keyboard.press("Escape");
    await dialog(page).getByRole("button", { name: "Leave", exact: true }).click();
    await expect(dialog(page)).toHaveCount(0);
  });

  test("Escape on the intro just closes it", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await page.keyboard.press("Escape");
    await expect(dialog(page)).toHaveCount(0);
  });
});

test.describe("the end", () => {
  async function loseAll(page: Page, rightFirst = 2) {
    for (let i = 0; i < rightFirst; i++) {
      await right(page).click();
      await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText(`Question ${i + 1}`, { timeout: 6000 });
    }
    for (let i = 0; i < LIVES; i++) {
      await wrong(page).click();
      await dialog(page).getByRole("button", { name: i === LIVES - 1 ? "See your result" : "Next question" }).click();
    }
  }

  test("three wrong answers end it with a score, a title and a way to play again", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await loseAll(page);
    await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("You made it to Intern");
    await expect(dialog(page)).toContainText("Game over");
    await expect(dialog(page).getByText(/^[\d,]+ points$/)).toBeVisible();
    await expect(dialog(page)).toContainText("3 more right answers would have made you Analyst.");
    await expect(dialog(page)).toContainText("New best");
    await dialog(page).getByRole("button", { name: "Play again" }).click();
    await expect(right(page)).toBeVisible();
    await lives(page, 3);
  });

  test("the best score is remembered, and only a better one is called new", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await loseAll(page, 3);
    await expect(dialog(page)).toContainText("New best");
    await dialog(page).getByRole("button", { name: "Play again" }).click();
    await expect(right(page)).toBeVisible();
    await loseAll(page, 0); // a worse game
    await expect(dialog(page)).not.toContainText("New best");
    await expect(dialog(page)).toContainText(/your best is [\d,]+/);
    const best = await page.evaluate(() => JSON.parse(localStorage.getItem("vantage.quiz.best") ?? "{}"));
    expect(best.correct).toBe(3);
  });

  test("what you missed is listed with the right answers", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await loseAll(page, 1);
    await dialog(page).getByText("What you missed").click();
    await expect(dialog(page)).toContainText("Answer: The right answer.");
  });

  test("the post buttons carry the score and open safely in a new tab", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await loseAll(page, 2);
    const section = dialog(page).getByRole("region", { name: "Post your score" });
    await expect(section).toContainText("Not your name, email or profile");
    for (const [name, host] of [["LinkedIn", "linkedin.com"], ["X", "twitter.com"], ["WhatsApp", "wa.me"]] as const) {
      const link = section.getByRole("link", { name });
      await expect(link).toHaveAttribute("href", new RegExp(host));
      await expect(link).toHaveAttribute("target", "_blank");
      await expect(link).toHaveAttribute("rel", /noopener/);
      expect(decodeURIComponent((await link.getAttribute("href")) ?? "")).toContain("/quiz/share?s=");
    }
  });

  test("Save image downloads a real picture", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await loseAll(page, 2);
    const [download] = await Promise.all([page.waitForEvent("download"), dialog(page).getByRole("button", { name: "Save image" }).click()]);
    expect(download.suggestedFilename()).toBe("vantage-pop-quiz.png");
    const path = await download.path();
    const fs = await import("node:fs");
    const bytes = fs.readFileSync(path);
    expect(bytes.subarray(1, 4).toString()).toBe("PNG");
    expect(bytes.readUInt32BE(16)).toBe(1080);
    expect(bytes.readUInt32BE(20)).toBe(1350);
    expect(bytes.byteLength).toBeGreaterThan(20_000);
    await expect(dialog(page).getByRole("region", { name: "Post your score" })).toContainText("Image saved");
  });

  test("Copy text puts the post and the link on the clipboard", async ({ page, context, browserName }) => {
    test.skip(browserName !== "chromium", "clipboard permissions are set up for Chromium");
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await loseAll(page, 2);
    await dialog(page).getByRole("button", { name: "Copy text" }).click();
    const text = await page.evaluate(() => navigator.clipboard.readText());
    expect(text).toContain("Vantage pop quiz");
    expect(text).toMatch(/\/quiz\/share\?s=\d+&c=2&k=2&l=1&t=0$/);
  });

  test("the share button uses the phone's own sheet, with the picture attached, when there is one", async ({ page }) => {
    await page.addInitScript(() => {
      const calls: unknown[] = [];
      (window as unknown as { __shared: unknown[] }).__shared = calls;
      Object.defineProperty(navigator, "share", { configurable: true, value: async (data: unknown) => void calls.push(data) });
      Object.defineProperty(navigator, "canShare", { configurable: true, value: () => true });
    });
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await loseAll(page, 2);
    await dialog(page).getByRole("button", { name: "Share", exact: true }).click();
    await expect.poll(() => page.evaluate(() => (window as unknown as { __shared: unknown[] }).__shared.length)).toBe(1);
    const shared = await page.evaluate(() => {
      const d = (window as unknown as { __shared: { title: string; text: string; url: string; files?: File[] }[] }).__shared[0];
      return { title: d.title, text: d.text, url: d.url, file: d.files?.[0]?.name, type: d.files?.[0]?.type };
    });
    expect(shared.title).toBe("My Vantage pop quiz score");
    expect(shared.url).toContain("/quiz/share?s=");
    expect(shared.file).toBe("vantage-pop-quiz.png");
    expect(shared.type).toBe("image/png");
  });

  test("the score counts up, or just appears when motion is reduced", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await loseAll(page, 3);
    const spoken = (await dialog(page).getByText(/^[\d,]+ points$/).innerText()).replace(" points", "");
    await expect(dialog(page).getByTestId("score")).toHaveText(spoken, { timeout: 1000 });
  });
});

test.describe("when things go wrong", () => {
  test("a failing server gives a clear message and a way to retry", async ({ page }) => {
    await stubQuiz(page, { fail: true });
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await dialog(page).getByRole("button", { name: "Start" }).click();
    await expect(dialog(page).getByRole("alert")).toContainText("We couldn't start the quiz");
    await expect(dialog(page).getByRole("button", { name: "Try again" })).toBeVisible();
    await expect(dialog(page)).not.toContainText(/Traceback|boom/);
  });

  test("retrying after a failure works once the server is back", async ({ page }) => {
    let healthy = false;
    await page.route("**/api/quiz/**", (route) =>
      healthy
        ? route.fulfill({ contentType: "application/json", body: JSON.stringify({ level: 1, questions: [q(1), q(2), q(3), q(4)] }) })
        : route.fulfill({ status: 503, contentType: "application/json", body: "{}" }),
    );
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await dialog(page).getByRole("button", { name: "Start" }).click();
    await expect(dialog(page).getByRole("alert")).toBeVisible();
    healthy = true;
    await dialog(page).getByRole("button", { name: "Try again" }).click();
    await expect(right(page)).toBeVisible();
  });

  test("an empty answer from the server is treated as a failure, not a blank screen", async ({ page }) => {
    await page.route("**/api/quiz/**", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ level: 1, questions: [] }) }));
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await dialog(page).getByRole("button", { name: "Start" }).click();
    await expect(dialog(page).getByRole("alert")).toContainText(/couldn't/i);
  });
});

test.describe("sound", () => {
  test("right and wrong answers make a sound, and the toggle silences them", async ({ page }) => {
    await stubAudio(page);
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    const afterStart = await tones(page);
    expect(afterStart).toBeGreaterThan(0);
    await right(page).click();
    await expect.poll(() => tones(page)).toBeGreaterThan(afterStart);
    await expect(dialog(page).getByRole("heading", { level: 2 })).toContainText("Question 1", { timeout: 6000 });
    await dialog(page).getByRole("button", { name: "Sound on" }).click();
    await expect(dialog(page).getByRole("button", { name: "Sound off" })).toBeVisible();
    const muted = await tones(page);
    await wrong(page).click();
    await page.waitForTimeout(400);
    expect(await tones(page)).toBe(muted);
    expect(await page.evaluate(() => localStorage.getItem("vantage.quiz.sound"))).toBe("off");
  });

  test("the choice is remembered next time", async ({ page }) => {
    await stubAudio(page);
    await stubQuiz(page);
    await onboardAsStudent(page);
    await page.evaluate(() => localStorage.setItem("vantage.quiz.sound", "off"));
    await openByTripleTap(page);
    await expect(dialog(page).getByRole("button", { name: "Sound off" })).toBeVisible();
    await start(page);
    expect(await tones(page)).toBe(0);
  });
});

test.describe("design and access", () => {
  const screens: [string, (p: Page) => Promise<void>][] = [
    ["the intro", async () => {}],
    ["a question", async (p) => start(p)],
    ["an answer with its explanation", async (p) => { await start(p); await wrong(p).click(); }],
  ];
  for (const [name, setup] of screens) {
    test(`${name} has no serious accessibility violations`, async ({ page }) => {
      await stubQuiz(page);
      await onboardAsStudent(page);
      await openByTripleTap(page);
      await setup(page);
      const results = await new AxeBuilder({ page }).include("dialog").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
      expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
    });
  }

  test("the game over screen has no serious accessibility violations", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    for (let i = 0; i < LIVES; i++) {
      await wrong(page).click();
      await dialog(page).getByRole("button", { name: i === LIVES - 1 ? "See your result" : "Next question" }).click();
    }
    await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("You made it to");
    const results = await new AxeBuilder({ page }).include("dialog").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });

  test("dark theme keeps the answer colours readable", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await wrong(page).click();
    const results = await new AxeBuilder({ page }).include("dialog").withRules(["color-contrast"]).analyze();
    expect(results.violations).toEqual([]);
  });

  test("nothing scrolls sideways on a small phone", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    const overflow = () => dialog(page).evaluate((d) => d.scrollWidth - d.clientWidth);
    expect(await overflow()).toBeLessThanOrEqual(1);
    await wrong(page).click();
    expect(await overflow()).toBeLessThanOrEqual(1);
  });

  test("every answer is a real button at least 44px tall, so it is easy to tap", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    const buttons = dialog(page).getByRole("group").getByRole("button");
    expect(await buttons.count()).toBe(4);
    for (const b of await buttons.all()) expect((await b.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  });

  test("the question is announced: focus lands on it and the result is in a live region", async ({ page }) => {
    await stubQuiz(page);
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await start(page);
    await expect(dialog(page).getByRole("heading", { level: 2 })).toBeFocused();
    await wrong(page).click();
    await expect(dialog(page).getByRole("status").filter({ hasText: "Not quite." })).toBeVisible();
    await expect(dialog(page).getByRole("button", { name: "Next question" })).toBeFocused();
  });
});

test.describe("with the real server", () => {
  test("real questions from the real data, four options each", async ({ page }) => {
    await onboardAsStudent(page);
    await openByTripleTap(page);
    await dialog(page).getByRole("button", { name: "Start" }).click();
    for (let i = 0; i < 3; i++) {
      const options = dialog(page).getByRole("group").getByRole("button");
      await expect(options).toHaveCount(4);
      await expect(dialog(page).getByRole("heading", { level: 2 })).not.toBeEmpty();
      await options.first().click();
      const next = dialog(page).getByRole("button", { name: /Next question|See your result/ });
      await next.click();
      if (await dialog(page).getByRole("heading", { level: 1 }).count()) break; // game over is fine too
    }
  });
});
