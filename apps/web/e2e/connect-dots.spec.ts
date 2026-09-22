import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { CHAIN_TARGET, extendChain, startChain, type ChainDot } from "../src/lib/connect-dots";
import { onboardAsStudent } from "./helpers";

const dot = (id: string, title: string): ChainDot => ({ id, title });

test.describe("rules", () => {
  test("a chain starts with the given dot and only unused neighbors as options", () => {
    const state = startChain(dot("1", "Brand Manager"), [dot("2", "Marketing Manager"), dot("1", "Brand Manager")]);
    expect(state.chain).toEqual([dot("1", "Brand Manager")]);
    expect(state.options).toEqual([dot("2", "Marketing Manager")]); // the start itself can't be offered back
    expect(state.status).toBe("playing");
  });

  test("extending adds the picked dot and replaces the options with its own unused neighbors", () => {
    let state = startChain(dot("1", "A"), [dot("2", "B"), dot("3", "C")]);
    state = extendChain(state, dot("2", "B"), [dot("1", "A"), dot("3", "C"), dot("4", "D")]);
    expect(state.chain.map((d) => d.id)).toEqual(["1", "2"]);
    expect(state.options.map((d) => d.id)).toEqual(["3", "4"]); // "1" is filtered: already in the chain
  });

  test("picking something not currently offered is a no-op", () => {
    const state = startChain(dot("1", "A"), [dot("2", "B")]);
    const same = extendChain(state, dot("9", "Not offered"), [dot("8", "X")]);
    expect(same).toEqual(state);
  });

  test("reaching the target length wins, even if the winning dot has no neighbors of its own", () => {
    let state = startChain(dot("1", "A"), [dot("2", "B")]);
    for (let i = 2; i < CHAIN_TARGET; i++) {
      state = extendChain(state, dot(String(i), `Role ${i}`), [dot(String(i + 1), `Role ${i + 1}`)]);
    }
    expect(state.chain).toHaveLength(CHAIN_TARGET - 1);
    state = extendChain(state, dot(String(CHAIN_TARGET), `Role ${CHAIN_TARGET}`), []); // no further neighbors at all
    expect(state.status).toBe("won");
    expect(state.chain).toHaveLength(CHAIN_TARGET);
  });

  test("running out of unused neighbors before the target breaks the chain", () => {
    let state = startChain(dot("1", "A"), [dot("2", "B")]);
    state = extendChain(state, dot("2", "B"), [dot("1", "A")]); // "2"'s only neighbor is "1", already used
    expect(state.status).toBe("lost");
    expect(state.chain).toHaveLength(2);
  });
});

// readChainBest/saveChainIfBest touch window.localStorage; see the other games' specs for why that
// isn't unit-tested in the Node-context test runner here either.

// ---- playing it ---------------------------------------------------------------------------------------------------------

const GRAPH: Record<string, { title: string; related: string[] }> = {
  r1: { title: "Brand Manager", related: ["r2"] },
  r2: { title: "Marketing Manager", related: ["r1", "r3"] },
  r3: { title: "Product Marketing Manager", related: ["r2", "r4"] },
  r4: { title: "Growth Marketing Manager", related: ["r3", "r5"] },
  r5: { title: "Digital Marketing Manager", related: ["r4", "r6"] },
  r6: { title: "Performance Marketing Manager", related: ["r5"] },
  dead: { title: "Isolated Role", related: [] },
};

// Onboarding does its own real role/company/skill searches, so the stub must go on after it, not before.
async function stubRoles(page: Page, startId: string) {
  await page.route("**/api/taxonomy/roles**", (route) => {
    const parts = new URL(route.request().url()).pathname.split("/").filter(Boolean);
    const id = parts.at(-1) === "roles" ? null : parts.at(-1)!;
    if (!id) return route.fulfill({ contentType: "application/json", body: JSON.stringify([{ id: startId, title: GRAPH[startId].title }]) });
    const node = GRAPH[id];
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id,
        title: node.title,
        domain: null,
        description: null,
        canonical: null,
        aliases: [],
        variants: [],
        capabilities: [],
        companies: [],
        companies_total: 0,
        related_roles: node.related.map((rid) => ({ role: { id: rid, title: GRAPH[rid].title }, shared_capabilities: ["Excel"], similarity: 0.5 })),
      }),
    });
  });
}

const dialog = (page: Page) => page.getByRole("dialog");

test.describe("playing Connect the Dots", () => {
  test.use({ serviceWorkers: "block" });

  test("is listed on the Games page with its own tagline", async ({ page }) => {
    await onboardAsStudent(page);
    await page.goto("/games");
    const tile = page.getByRole("button", { name: "Connect the Dots" });
    await expect(tile).toBeVisible();
    await expect(tile).toContainText(/chain six/i);
  });

  test("picking through a straight chain of six roles wins", async ({ page }) => {
    await onboardAsStudent(page);
    await stubRoles(page, "r1");
    await page.goto("/games");
    await page.getByRole("button", { name: "Connect the Dots" }).click();
    await dialog(page).getByRole("button", { name: "Start" }).click();

    for (const nextTitle of ["Marketing Manager", "Product Marketing Manager", "Growth Marketing Manager", "Digital Marketing Manager", "Performance Marketing Manager"]) {
      await dialog(page).getByRole("list", { name: "Roles you can connect next" }).getByRole("button", { name: nextTitle }).click();
    }
    await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("6 roles connected");
    await expect(dialog(page)).toContainText("Chain complete");
  });

  test("a start with no connections breaks the chain immediately, honestly", async ({ page }) => {
    await onboardAsStudent(page);
    await stubRoles(page, "dead");
    await page.goto("/games");
    await page.getByRole("button", { name: "Connect the Dots" }).click();
    await dialog(page).getByRole("button", { name: "Start" }).click();
    await expect(dialog(page).getByRole("heading", { level: 1 })).toContainText("1 role connected");
    await expect(dialog(page)).toContainText("Chain broken");
  });

  test("has no serious accessibility violations at the intro", async ({ page }) => {
    await onboardAsStudent(page);
    await stubRoles(page, "r1");
    await page.goto("/games");
    await page.getByRole("button", { name: "Connect the Dots" }).click();
    await dialog(page).getByRole("heading", { level: 1 }).waitFor();
    await page.waitForTimeout(400); // let the intro's .rise fade-in (320ms) settle before scanning colors
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });
});
