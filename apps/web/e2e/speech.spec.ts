import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { SAMPLE, chunk, pickVoice, scriptFor, speakable, upgradeTip, voiceGender, voiceOptions, voiceQuality } from "../src/lib/speech";

/** A voice as the browser reports it; only the fields the picker reads. */
const v = (name: string, lang: string, isDefault = false) => ({ name, lang, default: isDefault, localService: true, voiceURI: name }) as SpeechSynthesisVoice;

const WINDOWS = [
  v("Microsoft Zira - English (United States)", "en-US", true),
  v("Microsoft David - English (United States)", "en-US"),
  v("Microsoft Heera - English (India)", "en-IN"),
  v("Microsoft Ravi - English (India)", "en-IN"),
  v("Google हिन्दी", "hi-IN"),
  v("Google Deutsch", "de-DE"),
];

// ---- the logic, without a browser -------------------------------------------------------------------------

test.describe("voice choice", () => {
  const cases: [string, "female" | "male" | null][] = [
    ["Microsoft Zira - English (United States)", "female"],
    ["Microsoft David - English (United States)", "male"],
    ["Google UK English Female", "female"],
    ["Google UK English Male", "male"],
    ["Microsoft Aria Online (Natural) - English (United States)", "female"],
    ["Microsoft Guy Online (Natural) - English (United States)", "male"],
    ["Microsoft Neerja Online (Natural) - English (India)", "female"],
    ["Microsoft Prabhat Online (Natural) - English (India)", "male"],
    ["Samantha", "female"],
    ["Daniel", "male"],
    ["Google US English", null],
    ["Default voice", null],
    ["", null],
  ];
  for (const [name, gender] of cases) {
    test(`"${name}" is ${gender ?? "unknown"}`, () => {
      expect(voiceGender(name)).toBe(gender);
    });
  }

  test("a female voice is never mistaken for a male one because 'female' contains 'male'", () => {
    expect(voiceGender("Google UK English Female")).toBe("female");
  });

  test("Indian English comes first, in the gender asked for", () => {
    expect(pickVoice(WINDOWS, "female").voice?.name).toContain("Heera");
    expect(pickVoice(WINDOWS, "male").voice?.name).toContain("Ravi");
    expect(pickVoice(WINDOWS, "female").approximated).toBe(false);
    expect(pickVoice(WINDOWS, "female").pitch).toBe(1);
  });

  test("natural (neural) voices beat the older ones of the same language", () => {
    const voices = [v("Microsoft Zira - English (United States)", "en-US"), v("Microsoft Aria Online (Natural) - English (United States)", "en-US")];
    expect(pickVoice(voices, "female").voice?.name).toContain("Aria");
  });

  test("only English voices are used, whatever the gender", () => {
    const voices = [v("Google हिन्दी", "hi-IN"), v("Google Deutsch Female", "de-DE")];
    expect(pickVoice(voices, "female").voice).toBeNull();
  });

  test("with no male voice the closest one is used and pitch is lowered", () => {
    const picked = pickVoice([v("Microsoft Zira - English (United States)", "en-US"), v("Google US English", "en-US")], "male");
    expect(picked.approximated).toBe(true);
    expect(picked.pitch).toBeLessThan(1);
    expect(picked.voice?.name).toBe("Google US English"); // a neutral voice is closer to male than a female one
  });

  test("with no female voice pitch is raised", () => {
    const picked = pickVoice([v("Microsoft David - English (United States)", "en-US")], "female");
    expect(picked.approximated).toBe(true);
    expect(picked.pitch).toBeGreaterThan(1);
  });

  test("no voices at all gives no voice, without throwing", () => {
    expect(pickVoice([], "female")).toMatchObject({ voice: null, approximated: true });
  });

  test("picking does not reorder the list it was given", () => {
    const copy = [...WINDOWS];
    pickVoice(WINDOWS, "male");
    expect(WINDOWS).toEqual(copy);
  });
});

test.describe("what is read out", () => {
  const brief = {
    paragraphs: ["HUL named a new marketing head this week", "She joins from a rival firm. The move follows a reshuffle."],
    pointers: ["New head starts next month", "Reports to the CEO"],
  };

  test("headline, then the summary, then the pointers, each introduced aloud", () => {
    const text = scriptFor("HUL appoints new CMO", brief);
    expect(text.startsWith("HUL appoints new CMO.")).toBe(true);
    expect(text.indexOf("Summary.")).toBeGreaterThan(0);
    expect(text.indexOf("Quick pointers.")).toBeGreaterThan(text.indexOf("Summary."));
    expect(text.indexOf("Reports to the CEO.")).toBeGreaterThan(text.indexOf("Quick pointers."));
  });

  test("every sentence ends with a full stop so the voice pauses", () => {
    const text = scriptFor("Headline without a full stop", brief);
    expect(text).toContain("HUL named a new marketing head this week.");
    expect(text).toContain("New head starts next month.");
  });

  test("existing punctuation is kept, not doubled", () => {
    expect(scriptFor("Is this working?", null)).toBe("Is this working?");
    expect(scriptFor("Done!", null)).toBe("Done!");
  });

  test("no brief means just the headline", () => {
    expect(scriptFor("Only a headline", null)).toBe("Only a headline.");
    expect(scriptFor("Only a headline", { paragraphs: [], pointers: [] })).toBe("Only a headline.");
  });

  test("no pointers means no 'Quick pointers' heading", () => {
    expect(scriptFor("T", { paragraphs: ["One paragraph here"], pointers: [] })).not.toContain("Quick pointers");
  });

  test("symbols and markup are made speakable", () => {
    expect(speakable("Sales & marketing")).toBe("Sales and marketing");
    expect(speakable("Revenue of ₹500 crore")).toBe("Revenue of rupees 500 crore");
    expect(speakable("<b>Bold</b> claim  with   gaps")).toBe("Bold claim with gaps");
    expect(speakable("See https://example.com/a?b=1 for more")).toBe("See for more");
  });

  test("text is split at sentence ends into pieces a browser can speak without cutting off", () => {
    const text = Array.from({ length: 30 }, (_, i) => `This is sentence number ${i} about the quarter.`).join(" ");
    const pieces = chunk(text);
    expect(pieces.length).toBeGreaterThan(5);
    for (const p of pieces) {
      expect(p.length).toBeLessThanOrEqual(180);
      expect(p.endsWith(".")).toBe(true);
    }
    expect(pieces.join(" ")).toBe(text); // nothing lost, nothing repeated
  });

  test("one very long sentence is still cut into safe pieces", () => {
    const long = "word ".repeat(200).trim() + ".";
    const pieces = chunk(long);
    expect(pieces.every((p) => p.length <= 180)).toBe(true);
    expect(pieces.join(" ").replace(/\s+/g, " ")).toBe(long);
  });

  test("empty text gives no pieces", () => {
    expect(chunk("")).toEqual([]);
    expect(chunk("   ")).toEqual([]);
  });
});

// ---- the controls, in a page with a stand-in speech engine ----------------------------------------------------------

interface Spoken {
  text: string;
  voice: string | null;
  pitch: number;
  rate: number;
}
declare global {
  interface Window {
    __spoken: Spoken[];
    __calls: string[];
    __finish: () => void;
  }
}

/** Replaces the browser's speech engine with one that records what it is asked to say. */
async function fakeSpeech(page: Page, voices: { name: string; lang: string }[] | null = WINDOWS) {
  await page.addInitScript((list) => {
    const spoken: Spoken[] = [];
    const calls: string[] = [];
    let queue: { onend?: () => void }[] = [];
    if (list === null) {
      // A browser with no speech support at all.
      delete (window as unknown as Record<string, unknown>).speechSynthesis;
      Object.defineProperty(window, "SpeechSynthesisUtterance", { value: undefined, configurable: true });
    } else {
      class Utterance {
        voice: { name: string; lang: string } | null = null;
        lang = "";
        pitch = 1;
        rate = 1;
        onstart?: () => void;
        onend?: () => void;
        onerror?: (e: { error: string }) => void;
        constructor(public text: string) {}
      }
      Object.defineProperty(window, "SpeechSynthesisUtterance", { value: Utterance, configurable: true });
      const voiceObjects = list.map((x, i) => ({ ...x, default: i === 0, localService: true, voiceURI: x.name }));
      Object.defineProperty(window, "speechSynthesis", {
        configurable: true,
        value: {
          getVoices: () => voiceObjects,
          speak: (u: Utterance) => {
            spoken.push({ text: u.text, voice: u.voice?.name ?? null, pitch: u.pitch, rate: u.rate });
            queue.push(u);
          },
          cancel: () => {
            calls.push("cancel");
            queue = [];
          },
          pause: () => calls.push("pause"),
          resume: () => calls.push("resume"),
          addEventListener: () => {},
          removeEventListener: () => {},
        },
      });
    }
    window.__spoken = spoken;
    window.__calls = calls;
    window.__finish = () => queue.forEach((u) => u.onend?.());
  }, voices);
}

async function agree(page: Page) {
  const adult = page.getByLabel("I am 18 or older.");
  if ((await adult.count()) === 0) return;
  await adult.check();
  await page.getByLabel(/I agree to the Terms of Use/).check();
}

async function openFirstSummary(page: Page) {
  await page.goto("/onboarding");
  await page.getByRole("radio", { name: /I'm a student/ }).click();
  await agree(page);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: /^Marketing/ }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByPlaceholder("Search roles").fill("Brand Manager");
  await page.getByRole("button", { name: /^Brand Manager/ }).first().click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByPlaceholder("Search companies").fill("Hindustan");
  await page.getByRole("button", { name: /^Hindustan Unilever/ }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByPlaceholder("Search skills and tools").fill("Excel");
  await page.getByRole("button", { name: /^Excel/ }).first().click();
  await page.getByRole("button", { name: "Show me my feed" }).click();
  await page.waitForURL("**/feed");
  const card = page.locator("article").first();
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Summary and pointers" }).click();
  return card;
}

test.describe("listening to a summary", () => {
  test("the controls are in the opened summary, with the female voice chosen first", async ({ page }) => {
    await fakeSpeech(page);
    const card = await openFirstSummary(page);
    await expect(card.getByRole("button", { name: "Listen to the summary and pointers" })).toBeVisible();
    await expect(card.getByRole("button", { name: "Female", exact: true })).toHaveAttribute("aria-pressed", "true");
    await expect(card.getByRole("button", { name: "Male", exact: true })).toHaveAttribute("aria-pressed", "false");
    await expect(card.getByLabel("Speed")).toHaveValue("1");
  });

  test("listening reads the headline, the summary and the pointers in a female voice", async ({ page }) => {
    await fakeSpeech(page);
    const card = await openFirstSummary(page);
    const title = (await card.locator("h2").innerText()).trim();
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    const spoken = await page.evaluate(() => window.__spoken);
    expect(spoken.length).toBeGreaterThan(0);
    expect(spoken.map((s) => s.text).join(" ")).toContain("Summary.");
    expect(spoken[0].text.startsWith(title.split(" ").slice(0, 3).join(" "))).toBe(true);
    expect(new Set(spoken.map((s) => s.voice))).toEqual(new Set(["Microsoft Heera - English (India)"]));
    expect(spoken.every((s) => s.text.length <= 180 && s.pitch === 1 && s.rate === 1)).toBe(true);
    await expect(card.getByRole("button", { name: "Pause" })).toBeVisible();
  });

  test("switching to the male voice restarts in a male voice and remembers the choice", async ({ page }) => {
    await fakeSpeech(page);
    const card = await openFirstSummary(page);
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    await page.evaluate(() => (window.__spoken.length = 0));
    await card.getByRole("button", { name: "Male", exact: true }).click();
    await expect(card.getByRole("button", { name: "Male", exact: true })).toHaveAttribute("aria-pressed", "true");
    expect(await page.evaluate(() => window.__calls)).toContain("cancel"); // the old voice was stopped
    const spoken = await page.evaluate(() => window.__spoken);
    expect(spoken.length).toBeGreaterThan(0);
    expect(new Set(spoken.map((s) => s.voice))).toEqual(new Set(["Microsoft Ravi - English (India)"]));

    await page.reload();
    const again = page.locator("article").first();
    await again.getByRole("button", { name: "Summary and pointers" }).click();
    await expect(again.getByRole("button", { name: "Male", exact: true })).toHaveAttribute("aria-pressed", "true");
  });

  test("changing the speed changes how fast it is read", async ({ page }) => {
    await fakeSpeech(page);
    const card = await openFirstSummary(page);
    await card.getByLabel("Speed").selectOption("1.5");
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    expect((await page.evaluate(() => window.__spoken)).every((s) => s.rate === 1.5)).toBe(true);
  });

  test("pause, resume and stop", async ({ page }) => {
    await fakeSpeech(page);
    const card = await openFirstSummary(page);
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    await card.getByRole("button", { name: "Pause" }).click();
    await expect(card.getByRole("button", { name: "Resume" })).toBeVisible();
    await card.getByRole("button", { name: "Resume" }).click();
    await expect(card.getByRole("button", { name: "Pause" })).toBeVisible();
    await card.getByRole("button", { name: "Stop listening" }).click();
    await expect(card.getByRole("button", { name: "Listen to the summary and pointers" })).toBeVisible();
    const calls = await page.evaluate(() => window.__calls);
    expect(calls.filter((c) => c === "pause")).toHaveLength(1);
    expect(calls.filter((c) => c === "resume")).toHaveLength(1);
    expect(calls[calls.length - 1]).toBe("cancel");
  });

  test("it goes back to Listen by itself when the reading finishes", async ({ page }) => {
    await fakeSpeech(page);
    const card = await openFirstSummary(page);
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    await page.evaluate(() => window.__finish());
    await expect(card.getByRole("button", { name: "Listen to the summary and pointers" })).toBeVisible();
    await expect(card.getByRole("button", { name: "Stop listening" })).toHaveCount(0);
  });

  test("closing the summary stops the reading", async ({ page }) => {
    await fakeSpeech(page);
    const card = await openFirstSummary(page);
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    await page.evaluate(() => (window.__calls.length = 0));
    await card.getByRole("button", { name: "Hide summary" }).click();
    expect(await page.evaluate(() => window.__calls)).toContain("cancel");
  });

  test("only one story is read at a time", async ({ page }) => {
    await fakeSpeech(page);
    const first = await openFirstSummary(page);
    const cards = page.locator("article");
    test.skip((await cards.count()) < 2, "needs at least two stories in the feed");
    await first.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    const second = cards.nth(1);
    await second.getByRole("button", { name: "Summary and pointers" }).click();
    await second.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    await expect(first.getByRole("button", { name: "Pause" })).toHaveCount(0); // the first one stopped
    await expect(second.getByRole("button", { name: "Pause" })).toBeVisible();
  });

  test("with no male voice installed it says so and still reads", async ({ page }) => {
    await fakeSpeech(page, [{ name: "Microsoft Zira - English (United States)", lang: "en-US" }]);
    const card = await openFirstSummary(page);
    await card.getByRole("button", { name: "Male", exact: true }).click();
    await expect(card.getByText(/no male English voice/)).toBeVisible();
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    const spoken = await page.evaluate(() => window.__spoken);
    expect(spoken.length).toBeGreaterThan(0);
    expect(spoken.every((s) => s.pitch < 1)).toBe(true);
  });

  test("with no English voice at all it explains instead of failing", async ({ page }) => {
    await fakeSpeech(page, [{ name: "Google हिन्दी", lang: "hi-IN" }]);
    const card = await openFirstSummary(page);
    await expect(card.getByText(/no English voice installed/)).toBeVisible();
  });

  test("a browser without speech support gets a plain message, not a broken button", async ({ page }) => {
    await fakeSpeech(page, null);
    const card = await openFirstSummary(page);
    await expect(card.getByText(/Listening isn't available in this browser/)).toBeVisible();
    await expect(card.getByRole("button", { name: "Listen to the summary and pointers" })).toHaveCount(0);
  });

  test("the controls work with the keyboard and announce their state", async ({ page }) => {
    await fakeSpeech(page);
    const card = await openFirstSummary(page);
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).focus();
    await page.keyboard.press("Enter");
    await expect(card.getByRole("status")).toHaveText("Reading the summary.");
    await page.keyboard.press("Enter"); // the same button is now Pause
    await expect(card.getByRole("status")).toHaveText("Paused.");
  });

  test("the opened summary with listen controls has no serious accessibility violations", async ({ page }) => {
    await fakeSpeech(page);
    const card = await openFirstSummary(page);
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    const results = await new AxeBuilder({ page }).include("article").analyze();
    expect(results.violations.filter((x) => x.impact === "serious" || x.impact === "critical")).toEqual([]);
  });
});


// ---- nicer voices -------------------------------------------------------------------------------------------------------

const vv = (name: string, lang = "en-US", localService = true) => ({ name, lang, default: false, localService, voiceURI: name }) as SpeechSynthesisVoice;

test.describe("voice quality", () => {
  const cases: [string, boolean, string][] = [
    ["Microsoft Aria Online (Natural) - English (United States)", false, "natural"],
    ["Microsoft Prabhat Online (Natural) - English (India)", false, "natural"],
    ["en-US-Neural2-F", true, "natural"],
    ["Ava (Premium)", true, "enhanced"],
    ["Samantha (Enhanced)", true, "enhanced"],
    ["Siri Female (United States)", true, "enhanced"],
    ["Google UK English Female", false, "network"],
    ["Google US English", true, "network"],
    ["English India", false, "network"],
    ["Microsoft Zira - English (United States)", true, "basic"],
    ["Microsoft David Desktop - English (United States)", true, "basic"],
    ["eSpeak English", true, "basic"],
  ];
  for (const [name, local, quality] of cases) {
    test(`${name} is ${quality}`, () => {
      expect(voiceQuality({ name, localService: local })).toBe(quality);
    });
  }

  test("a natural voice beats an online one, which beats a basic one, whatever the accent", () => {
    const basic = vv("Microsoft Heera - English (India)", "en-IN");
    const online = vv("Google UK English Female", "en-GB", false);
    const natural = vv("Microsoft Aria Online (Natural) - English (United States)", "en-US", false);
    expect(pickVoice([basic, online], "female").voice).toBe(online);
    expect(pickVoice([basic, online, natural], "female").voice).toBe(natural);
  });

  test("Indian English breaks a tie between voices of the same quality", () => {
    const us = vv("Microsoft Aria Online (Natural) - English (United States)", "en-US", false);
    const india = vv("Microsoft Neerja Online (Natural) - English (India)", "en-IN", false);
    expect(pickVoice([us, india], "female").voice).toBe(india);
  });

  test("the old built-in desktop voices come last", () => {
    const desktop = vv("Microsoft Zira Desktop - English (United States)", "en-US");
    const plain = vv("Microsoft Zira - English (United States)", "en-US");
    expect(pickVoice([desktop, plain], "female").voice).toBe(plain);
  });

  test("a voice the reader picked by name is used even if a better one exists", () => {
    const basic = vv("Microsoft Zira - English (United States)");
    const natural = vv("Microsoft Aria Online (Natural) - English (United States)", "en-US", false);
    expect(pickVoice([basic, natural], "female", "Microsoft Zira - English (United States)").voice).toBe(basic);
    expect(pickVoice([basic, natural], "female", "Microsoft Zira - English (United States)").approximated).toBe(false);
  });

  test("a voice that has since gone, or is not English, falls back to the best one", () => {
    const natural = vv("Microsoft Aria Online (Natural) - English (United States)", "en-US", false);
    const hindi = vv("Google हिन्दी", "hi-IN", false);
    expect(pickVoice([natural, hindi], "female", "A voice that was uninstalled").voice).toBe(natural);
    expect(pickVoice([natural, hindi], "female", "Google हिन्दी").voice).toBe(natural);
  });

  test("the picker lists voices best first, matching the gender, then the ones that do not say", () => {
    const voices = [
      vv("Microsoft Zira - English (United States)"),
      vv("Microsoft Aria Online (Natural) - English (United States)", "en-US", false),
      vv("Microsoft David - English (United States)"),
      vv("Google US English", "en-US", false),
      vv("Google हिन्दी", "hi-IN", false),
    ];
    const female = voiceOptions(voices, "female");
    expect(female.matching.map((o) => o.name)).toEqual(["Microsoft Aria Online (Natural) - English (United States)", "Microsoft Zira - English (United States)"]);
    expect(female.matching[0].label).toContain("natural");
    expect(female.other.map((o) => o.name)).toEqual(["Google US English"]);
    expect(voiceOptions(voices, "male").matching.map((o) => o.name)).toEqual(["Microsoft David - English (United States)"]);
    expect([...female.matching, ...female.other].some((o) => o.name.includes("हिन्दी"))).toBe(false); // English only
  });

  test("labels are short enough to read in a menu", () => {
    const [o] = voiceOptions([vv("Microsoft Aria Online (Natural) - English (United States)", "en-US", false)], "female").matching;
    expect(o.label).toBe("Aria (en-US, natural)");
  });

  const uas: [string, RegExp][] = [
    ["Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)", /Spoken Content/],
    ["Mozilla/5.0 (Linux; Android 14; Pixel 7)", /Text-to-speech/],
    ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605", /System Settings/],
    ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Edg/120", /Narrator/],
    ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537", /Microsoft Edge/],
  ];
  for (const [ua, expected] of uas) {
    test(`the tip for ${ua.slice(13, 40)} mentions ${expected.source}`, () => {
      expect(upgradeTip(ua)).toMatch(expected);
    });
  }

  test("no tip text uses a dash or a list of three", () => {
    for (const [ua] of uas) expect(upgradeTip(ua)).not.toMatch(/\u2014|\u2013/);
  });
});

const NATURAL = [
  { name: "Microsoft Aria Online (Natural) - English (United States)", lang: "en-US" },
  { name: "Microsoft Jenny Online (Natural) - English (United States)", lang: "en-US" },
  { name: "Microsoft Guy Online (Natural) - English (United States)", lang: "en-US" },
  { name: "Microsoft Ryan Online (Natural) - English (United Kingdom)", lang: "en-GB" },
];

test.describe("choosing a voice", () => {
  test("the menu offers voices for the chosen gender, best first, and the reading uses the pick", async ({ page }) => {
    await fakeSpeech(page, [...WINDOWS.map((w) => ({ name: w.name, lang: w.lang })), ...NATURAL]);
    const card = await openFirstSummary(page);
    const menu = card.locator("select").filter({ hasText: "Best available" });
    await expect(menu.locator("option").first()).toHaveText("Best available");
    await expect(menu.locator('optgroup[label="Female voices"] option').first()).toContainText("natural");
    await menu.selectOption({ label: "Jenny (en-US, natural)" });
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    const spoken = await page.evaluate(() => window.__spoken);
    expect(new Set(spoken.map((x) => x.voice))).toEqual(new Set(["Microsoft Jenny Online (Natural) - English (United States)"]));
  });

  test("each gender remembers its own voice, across a reload", async ({ page }) => {
    await fakeSpeech(page, NATURAL);
    let card = await openFirstSummary(page);
    const menu = () => card.locator("select").filter({ hasText: "Best available" });
    await menu().selectOption({ label: "Jenny (en-US, natural)" });
    await card.getByRole("button", { name: "Male", exact: true }).click();
    await expect(menu()).toHaveValue(""); // nothing picked for male yet
    await menu().selectOption({ label: "Ryan (en-GB, natural)" });
    await page.reload();
    card = page.locator("article").first();
    await card.getByRole("button", { name: "Summary and pointers" }).click();
    await expect(menu()).toHaveValue("Microsoft Ryan Online (Natural) - English (United Kingdom)");
    await card.getByRole("button", { name: "Female", exact: true }).click();
    await expect(menu()).toHaveValue("Microsoft Jenny Online (Natural) - English (United States)");
  });

  test("'Best available' clears a pick", async ({ page }) => {
    await fakeSpeech(page, NATURAL);
    const card = await openFirstSummary(page);
    const menu = card.locator("select").filter({ hasText: "Best available" });
    await menu.selectOption({ label: "Jenny (en-US, natural)" });
    await menu.selectOption("");
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    const spoken = await page.evaluate(() => window.__spoken);
    expect(spoken[0].voice).toContain("Online (Natural)");
    await expect(menu).toHaveValue("");
  });

  test("changing the voice while it is reading carries on in the new one", async ({ page }) => {
    await fakeSpeech(page, NATURAL);
    const card = await openFirstSummary(page);
    await card.getByRole("button", { name: "Listen to the summary and pointers" }).click();
    await page.evaluate(() => (window.__spoken.length = 0));
    await card.locator("select").filter({ hasText: "Best available" }).selectOption({ label: "Jenny (en-US, natural)" });
    const spoken = await page.evaluate(() => window.__spoken);
    expect(spoken.length).toBeGreaterThan(0);
    expect(new Set(spoken.map((x) => x.voice))).toEqual(new Set(["Microsoft Jenny Online (Natural) - English (United States)"]));
  });

  test("Hear it says one short sample in the current voice and leaves the story alone", async ({ page }) => {
    await fakeSpeech(page, NATURAL);
    const card = await openFirstSummary(page);
    await card.locator("select").filter({ hasText: "Best available" }).selectOption({ label: "Jenny (en-US, natural)" });
    await card.getByRole("button", { name: "Hear a sample of this voice" }).click();
    const spoken = await page.evaluate(() => window.__spoken);
    expect(spoken).toHaveLength(1);
    expect(spoken[0]).toMatchObject({ text: SAMPLE, voice: "Microsoft Jenny Online (Natural) - English (United States)" });
    await expect(card.getByRole("button", { name: "Listen to the summary and pointers" })).toBeVisible(); // the story is not playing
  });

  test("a tip about nicer voices shows only when the voice in use is a plain built-in one", async ({ page }) => {
    await fakeSpeech(page, [{ name: "Microsoft Zira - English (United States)", lang: "en-US" }]);
    const card = await openFirstSummary(page);
    await expect(card.getByText(/For nicer voices/)).toBeVisible();
  });

  test("no tip when a natural voice is in use", async ({ page }) => {
    await fakeSpeech(page, NATURAL);
    const card = await openFirstSummary(page);
    await expect(card.getByText(/For nicer voices/)).toHaveCount(0);
  });

  test("the menu, the sample button and the tip have no serious accessibility violations", async ({ page }) => {
    await fakeSpeech(page, [{ name: "Microsoft Zira - English (United States)", lang: "en-US" }, ...NATURAL]);
    await openFirstSummary(page);
    const results = await new AxeBuilder({ page }).include("article").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((x) => x.impact === "serious" || x.impact === "critical")).toEqual([]);
  });
});
