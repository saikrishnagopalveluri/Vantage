import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { MAX_GUESSES, MAX_HINTS, hintText, newWordState, pickTarget, scoreGuess, submitGuess, takeHint, wordShareCard } from "../src/lib/word-drop";
import { onboardAsStudent } from "./helpers";

test.describe("rules", () => {
  test("only picks a clean single word within the length range, and keeps its kind", () => {
    const target = pickTarget([
      { name: "Excel", kind: "tool" },
      { name: "Power BI", kind: "tool" }, // has a space: skipped
      { name: "SQL", kind: "tool" }, // too short (under 4): skipped
      { name: "C++", kind: "tool" }, // punctuation: skipped
      { name: "Communication", kind: "skill" },
    ]);
    expect(target).not.toBeNull();
    expect(["EXCEL", "COMMUNICATION"]).toContain(target!.word);
    expect(target!.kind).toBe(target!.word === "EXCEL" ? "tool" : "skill");
  });

  test("returns null when nothing in the batch is usable", () => {
    expect(pickTarget([{ name: "Power BI", kind: "tool" }, { name: "SQL", kind: "tool" }, { name: "C++", kind: "tool" }])).toBeNull();
  });

  test("avoids a recently-seen word while another candidate is still available", () => {
    const pool = [{ name: "Excel", kind: "tool" as const }, { name: "Canva", kind: "tool" as const }];
    for (let i = 0; i < 20; i++) {
      const target = pickTarget(pool, ["EXCEL"]);
      expect(target!.word).toBe("CANVA");
    }
  });

  test("falls back to a recently-seen word rather than fail to start, once the pool is exhausted", () => {
    const pool = [{ name: "Excel", kind: "tool" as const }];
    const target = pickTarget(pool, ["EXCEL"]);
    expect(target!.word).toBe("EXCEL");
  });

  test("a hint reveals the kind, then the first letter, capped at MAX_HINTS and free of charge", () => {
    let state = newWordState({ word: "EXCEL", kind: "tool" });
    expect(hintText(state)).toEqual([]);
    state = takeHint(state);
    expect(hintText(state)).toEqual(["It's a tool."]);
    state = takeHint(state);
    expect(hintText(state)).toEqual(["It's a tool.", 'Starts with "E".']);
    state = takeHint(state); // a third click past MAX_HINTS does nothing
    expect(state.hintsUsed).toBe(MAX_HINTS);
    expect(hintText(state)).toHaveLength(MAX_HINTS);
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
    let state = newWordState({ word: "EXCEL", kind: "tool" });
    for (let i = 0; i < MAX_GUESSES - 1; i++) state = submitGuess(state, "ZZZZZ");
    expect(state.status).toBe("playing");
    state = submitGuess(state, "ZZZZZ");
    expect(state.status).toBe("lost");
    expect(state.guesses).toHaveLength(MAX_GUESSES);

    const won = submitGuess(newWordState({ word: "EXCEL", kind: "tool" }), "EXCEL");
    expect(won.status).toBe("won");
    expect(won.guesses).toHaveLength(1);
  });

  test("a guess of the wrong length is ignored, not counted", () => {
    const state = submitGuess(newWordState({ word: "EXCEL", kind: "tool" }), "AB");
    expect(state.guesses).toHaveLength(0);
  });

  test("the share card names the number of guesses and the word's category", () => {
    const won = submitGuess(newWordState({ word: "EXCEL", kind: "tool" }), "EXCEL");
    expect(wordShareCard(won)).toMatchObject({ game: "WORD DROP", headlineLabel: "solved in", headline: "1 guess" });
    expect(wordShareCard(won).stats).toContainEqual({ value: "Tool", label: "category" });
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

  test("hints reveal the kind, then the first letter, and run out after two", async ({ page }) => {
    await onboardAsStudent(page);
    await stubCapabilities(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Word Drop" }).click();
    await dialog(page).getByRole("button", { name: "Start" }).click();

    const hint = dialog(page).getByRole("button", { name: /Need a hint/ });
    await expect(hint).toHaveText("Need a hint? (2 left)");
    await hint.click();
    await expect(dialog(page).getByText("It's a tool.")).toBeVisible();
    await expect(hint).toHaveText("Need a hint? (1 left)");

    await hint.click();
    await expect(dialog(page).getByText('Starts with "E".')).toBeVisible();
    await expect(dialog(page).getByRole("button", { name: "No hints left" })).toBeDisabled();
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

// ---- sharing a score -----------------------------------------------------------------------------------------------

async function winToOver(page: Page) {
  await onboardAsStudent(page);
  await stubCapabilities(page);
  await page.goto("/games");
  await page.getByRole("button", { name: "Word Drop" }).click();
  await dialog(page).getByRole("button", { name: "Start" }).click();
  await dialog(page).getByLabel("Your guess").fill("EXCEL");
  await dialog(page).getByRole("button", { name: "Guess" }).click();
  await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("Solved in 1 guess");
}

test.describe("sharing a score", () => {
  test("only shows up after a win, never after losing (it would spoil the word)", async ({ page }) => {
    await onboardAsStudent(page);
    await stubCapabilities(page);
    await page.goto("/games");
    await page.getByRole("button", { name: "Word Drop" }).click();
    await dialog(page).getByRole("button", { name: "Start" }).click();
    for (let i = 0; i < MAX_GUESSES; i++) {
      await dialog(page).getByLabel("Your guess").fill("ZEBRA");
      await dialog(page).getByRole("button", { name: "Guess" }).click();
    }
    await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("The word was EXCEL");
    await expect(dialog(page).getByRole("region", { name: "Post your score" })).toHaveCount(0);
  });

  test("the share links point at the Games page, and WhatsApp/X also carry the win", async ({ page }) => {
    await winToOver(page);
    const section = dialog(page).getByRole("region", { name: "Post your score" });
    for (const [name, host] of [["LinkedIn", "linkedin.com"], ["X", "twitter.com"], ["WhatsApp", "wa.me"]] as const) {
      const link = section.getByRole("link", { name });
      await expect(link).toHaveAttribute("href", new RegExp(host));
      expect(decodeURIComponent((await link.getAttribute("href")) ?? "")).toContain("/games");
    }
    // LinkedIn's share-offsite endpoint only takes a URL, not pre-filled text — only X and WhatsApp carry the score.
    for (const name of ["X", "WhatsApp"] as const) {
      const href = await section.getByRole("link", { name }).getAttribute("href");
      expect(decodeURIComponent(href ?? "")).toContain("Word Drop in 1 guess");
    }
  });

  test("Save image downloads a real picture", async ({ page }) => {
    await winToOver(page);
    const [download] = await Promise.all([page.waitForEvent("download"), dialog(page).getByRole("button", { name: "Save image" }).click()]);
    expect(download.suggestedFilename()).toBe("vantage-word-drop.png");
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
    await winToOver(page);
    await dialog(page).getByRole("button", { name: "Share", exact: true }).click();
    await expect.poll(() => page.evaluate(() => (window as unknown as { __shared: unknown[] }).__shared.length)).toBe(1);
    const shared = await page.evaluate(() => {
      const d = (window as unknown as { __shared: { title: string; url: string; files?: File[] }[] }).__shared[0];
      return { title: d.title, url: d.url, file: d.files?.[0]?.name, type: d.files?.[0]?.type };
    });
    expect(shared.title).toBe("My Vantage Word Drop score");
    expect(shared.url).toContain("/games");
    expect(shared.file).toBe("vantage-word-drop.png");
    expect(shared.type).toBe("image/png");
  });
});
