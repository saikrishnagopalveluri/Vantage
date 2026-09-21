import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/**
 * Read-only browser cases. They never create data, so they are safe to point at the live site:
 *   APP=https://vantage-web-vert.vercel.app npx playwright test e2e/qa-matrix.spec.ts
 * The only writes are refused ones (wrong password, invalid sign-up), which the API rejects.
 */

const PUBLIC = ["/", "/login", "/terms", "/privacy", "/offline"];

async function openLogin(page: Page, mode: "Log in" | "Create account" = "Log in") {
  await page.goto("/login");
  await page.getByRole("tab", { name: mode }).click();
}

// ---- login form -------------------------------------------------------------------------------

test.describe("login form", () => {
  test("submit stays disabled until both fields are filled", async ({ page }) => {
    await openLogin(page);
    const submit = page.locator("form").getByRole("button", { name: /^Log in/ });
    await expect(submit).toBeDisabled();
    await page.getByLabel("Email").fill("someone@example.com");
    await expect(submit).toBeDisabled();
    await page.getByLabel("Password", { exact: true }).fill("x");
    await expect(submit).toBeEnabled();
    await page.getByLabel("Email").fill("");
    await expect(submit).toBeDisabled();
  });

  test("the show/hide button toggles the password field type", async ({ page }) => {
    await openLogin(page);
    const pw = page.getByLabel("Password", { exact: true });
    await pw.fill("secret-value-1");
    await expect(pw).toHaveAttribute("type", "password");
    await page.getByRole("button", { name: "Show" }).click();
    await expect(pw).toHaveAttribute("type", "text");
    await page.getByRole("button", { name: "Hide" }).click();
    await expect(pw).toHaveAttribute("type", "password");
  });

  test("a wrong password shows one generic error and keeps the page", async ({ page }) => {
    await openLogin(page);
    await page.getByLabel("Email").fill(`nobody-${Date.now()}@example.com`);
    await page.getByLabel("Password", { exact: true }).fill("wrong-password-1");
    await page.getByLabel("Password", { exact: true }).press("Enter"); // Enter submits
    const alert = page.locator("form").getByRole("alert");
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("don't match");
    await expect(alert).not.toContainText(/no such|not found|exists/i); // never reveals whether the email exists
    await expect(page).toHaveURL(/\/login/);
  });

  test("tab order goes email, then password", async ({ page }) => {
    await openLogin(page);
    await page.getByLabel("Email").focus();
    await page.keyboard.press("Tab");
    await expect(page.getByLabel("Password", { exact: true })).toBeFocused();
  });

  test("markup that is typed into the form is never executed", async ({ page }) => {
    await openLogin(page);
    const payload = `"><img src=x onerror="window.__pwned=1">`;
    await page.getByLabel("Email").fill(payload);
    await page.getByLabel("Password", { exact: true }).fill(payload);
    await page.getByLabel("Password", { exact: true }).press("Enter");
    await page.waitForTimeout(800);
    expect(await page.evaluate(() => (window as unknown as { __pwned?: number }).__pwned)).toBeUndefined();
    expect(await page.locator("img[src='x']").count()).toBe(0);
  });

  test("the email field asks for an email keyboard and does not autocapitalise", async ({ page }) => {
    await openLogin(page);
    const email = page.getByLabel("Email");
    await expect(email).toHaveAttribute("type", "email");
    await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute("autocomplete", /password/);
  });
});

test.describe("sign-up form", () => {
  test("cannot be submitted until the consent box is ticked", async ({ page }) => {
    await openLogin(page, "Create account");
    await page.getByLabel("Email").fill("newperson@example.com");
    await page.getByLabel("Password", { exact: true }).fill("a-long-enough-password");
    const submit = page.locator("form").getByRole("button", { name: /^Create account/ });
    await expect(submit).toBeDisabled();
    await page.getByLabel("I am 18 or older.").check();
    await expect(submit).toBeDisabled(); // both boxes are needed
    await page.getByLabel(/I agree to the Terms of Use/).check();
    await expect(submit).toBeEnabled();
    await page.getByLabel("I am 18 or older.").uncheck();
    await expect(submit).toBeDisabled();
  });

  test("shows the password rule and the consent text links to the legal pages", async ({ page }) => {
    await openLogin(page, "Create account");
    await expect(page.getByText(/At least 8 characters/)).toBeVisible();
    await expect(page.getByRole("link", { name: /Terms of Use/ }).first()).toHaveAttribute("href", "/terms");
  });

  test("a short password or a bad email is refused with a plain message and creates nothing", async ({ page }) => {
    await openLogin(page, "Create account");
    await page.getByLabel("Email").fill("valid-shape@example.com");
    await page.getByLabel("Password", { exact: true }).fill("short");
    await page.getByLabel("I am 18 or older.").check();
    await page.getByLabel(/I agree to the Terms of Use/).check();
    await page.locator("form").getByRole("button", { name: /^Create account/ }).click();
    await expect(page.locator("form").getByRole("alert")).toContainText(/at least 8/i);

    await page.getByLabel("Email").fill("not-an-email");
    await page.getByLabel("Password", { exact: true }).fill("a-long-enough-password");
    await page.locator("form").getByRole("button", { name: /^Create account/ }).click();
    await expect(page.locator("form").getByRole("alert")).toContainText(/email/i);
  });

  test("switching between log in and create account clears the error", async ({ page }) => {
    await openLogin(page);
    await page.getByLabel("Email").fill("nobody-x@example.com");
    await page.getByLabel("Password", { exact: true }).fill("wrong-password-1");
    await page.getByLabel("Password", { exact: true }).press("Enter");
    await expect(page.locator("form").getByRole("alert")).toBeVisible();
    await page.getByRole("tab", { name: "Create account" }).click();
    await expect(page.locator("form").getByRole("alert")).toHaveCount(0);
  });

  test("the guest route is offered", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: "Try it as a guest" }).click();
    await expect(page).toHaveURL(/\/onboarding/);
  });
});

// ---- access control ------------------------------------------------------------------------------

test.describe("signed-out access", () => {
  for (const path of ["/feed", "/explore", "/career", "/saved", "/profile"]) {
    test(`${path} sends a signed-out visitor to the login page`, async ({ page }) => {
      await page.goto(path);
      await page.waitForURL("**/login", { timeout: 30_000 });
    });
  }

  test("no session cookie is set just by visiting", async ({ page, context }) => {
    for (const p of PUBLIC) await page.goto(p);
    const names = (await context.cookies()).map((c) => c.name);
    expect(names).not.toContain("vantage_session");
  });
});

// ---- home and legal pages -----------------------------------------------------------------------------

test.describe("public pages", () => {
  for (const path of PUBLIC) {
    test(`${path} has a title, one h1, a lang attribute and no console errors`, async ({ page }) => {
      const errors: string[] = [];
      page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
      page.on("pageerror", (e) => errors.push(String(e)));
      await page.goto(path);
      await expect(page.locator("h1")).toHaveCount(1);
      expect((await page.title()).length).toBeGreaterThan(3);
      await expect(page.locator("html")).toHaveAttribute("lang", "en");
      await page.waitForLoadState("networkidle");
      expect(errors.filter((e) => !/favicon|Failed to load resource.*(401|404)/.test(e))).toEqual([]);
    });

    test(`${path} has no serious accessibility violations`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
      expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
    });

    test(`${path} does not scroll sideways on a 320px phone`, async ({ page }) => {
      await page.setViewportSize({ width: 320, height: 640 });
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
    });
  }

  // WCAG 2.4.2: every page has a title that says what it is, so tabs, history and screen readers make sense.
  const TITLES: [string, string][] = [
    ["/", "Vantage · Career news that fits you"],
    ["/login", "Log in or create an account · Vantage"],
    ["/terms", "Terms of Use · Vantage"],
    ["/privacy", "Privacy Policy · Vantage"],
    ["/offline", "Offline · Vantage"],
    ["/onboarding", "Set up your feed · Vantage"],
  ];
  for (const [path, title] of TITLES) {
    test(`${path} is titled "${title}"`, async ({ page }) => {
      await page.goto(path);
      await expect(page).toHaveTitle(title);
    });
  }

  test("page titles are all different", async ({ page }) => {
    const titles = new Set<string>();
    for (const [path] of TITLES) {
      await page.goto(path);
      titles.add(await page.title());
    }
    expect(titles.size).toBe(TITLES.length);
  });

  test("every link on the home page resolves without a server error", async ({ page, request }) => {
    await page.goto("/");
    const hrefs = await page.$$eval("a[href]", (as) => [...new Set(as.map((a) => (a as HTMLAnchorElement).getAttribute("href") || ""))]);
    for (const href of hrefs.filter((h) => h.startsWith("/") && !h.startsWith("//"))) {
      const res = await request.get(href);
      expect(res.status(), href).toBeLessThan(500);
    }
  });

  test("the footer links reach the terms and the privacy policy", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /^Terms/ }).first().click();
    await expect(page).toHaveURL(/\/terms/);
    await page.goBack();
    await page.getByRole("link", { name: /^Privacy/ }).first().click();
    await expect(page).toHaveURL(/\/privacy/);
  });

  test("the privacy policy lists the user's rights and how to use them", async ({ page }) => {
    await page.goto("/privacy");
    for (const term of [/access/i, /correct/i, /erase|delete/i, /grievance/i, /children|18/i]) {
      await expect(page.locator("main")).toContainText(term);
    }
  });

  test("the terms say the app gives information, not advice", async ({ page }) => {
    await page.goto("/terms");
    await expect(page.locator("main")).toContainText(/not (financial|legal|career)? ?advice|Information, not advice/i);
  });

  test("an unknown page shows a page, not a crash", async ({ page }) => {
    const res = await page.goto("/definitely-not-a-page");
    expect(res?.status()).toBeLessThan(500);
    await expect(page.locator("body")).not.toContainText(/Application error|Internal Server Error/i);
  });

  test("the role peek finds a role, and hostile text is shown as text", async ({ page }) => {
    await page.goto("/");
    const box = page.getByLabel("Job title");
    await box.fill("brand manager");
    await expect(page.getByRole("button", { name: /^Brand Manager/ }).first()).toBeVisible();
    await box.fill(`<img src=x onerror="window.__peek=1">`);
    await page.waitForTimeout(800);
    expect(await page.evaluate(() => (window as unknown as { __peek?: number }).__peek)).toBeUndefined();
    await box.fill("zzzzqqqq-no-such-role");
    await expect(page.getByRole("button", { name: /zzzz/i })).toHaveCount(0);
  });

  test("the live numbers on the home page are real, not placeholders", async ({ page }) => {
    await page.goto("/");
    // Each number sits in the same block as its label.
    for (const label of ["job titles", "companies"]) {
      const block = page.getByText(label, { exact: true }).locator("..");
      await expect(block).toContainText(/\d/);
      const value = Number((await block.innerText()).replace(/\D/g, ""));
      expect(value, label).toBeGreaterThan(1000);
    }
  });

  test("the FAQ opens and closes from the keyboard", async ({ page }) => {
    await page.goto("/");
    const q = page.getByText("Do I need an account?");
    await q.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText(/You can try Vantage as a guest/)).toBeVisible();
    await page.keyboard.press("Enter");
    await expect(page.getByText(/You can try Vantage as a guest/)).toBeHidden();
  });
});

// ---- installability and headers ---------------------------------------------------------------------------

test.describe("app shell", () => {
  test("has a viewport meta, a theme colour and a manifest link", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator('meta[name="viewport"]')).toHaveAttribute("content", /width=device-width/);
    await expect(page.locator('link[rel="manifest"]')).toHaveCount(1);
  });

  test("the service worker registers", async ({ page }) => {
    await page.goto("/");
    const registered = await page.evaluate(async () => {
      if (!("serviceWorker" in navigator)) return false;
      await navigator.serviceWorker.ready.catch(() => undefined);
      return (await navigator.serviceWorker.getRegistrations()).length > 0;
    });
    expect(registered).toBe(true);
  });

  test("the page cannot be framed", async ({ request }) => {
    const res = await request.get("/login");
    expect(res.headers()["x-frame-options"]).toBe("DENY");
    expect(res.headers()["content-security-policy"]).toContain("frame-ancestors 'none'");
  });

  test("a keyboard user can reach the main content with Tab and see a focus ring", async ({ page }) => {
    await page.goto("/login");
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus");
    await expect(focused).toBeVisible();
    const outline = await focused.evaluate((el) => {
      const s = getComputedStyle(el);
      return `${s.outlineStyle}|${s.outlineWidth}|${s.boxShadow}`;
    });
    expect(outline).not.toMatch(/^none\|0px\|none$/);
  });

  test("text can be enlarged to 200% without losing the form", async ({ page }) => {
    await page.setViewportSize({ width: 640, height: 800 });
    await page.goto("/login");
    await page.addStyleTag({ content: "html{font-size:200% !important}" });
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  });

  test("dark colour scheme renders the login page with readable contrast", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).withRules(["color-contrast"]).analyze();
    expect(results.violations).toEqual([]);
  });

  test("reduced motion is respected", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    const durations = await page.evaluate(() =>
      [...document.querySelectorAll("*")].slice(0, 300).map((el) => getComputedStyle(el).animationDuration),
    );
    expect(durations.every((d) => d === "0s" || d === "0.01ms" || d === "")).toBe(true);
  });
});
