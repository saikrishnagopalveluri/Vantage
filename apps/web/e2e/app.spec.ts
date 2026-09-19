import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/** Tick the two boxes a guest must tick before we keep any data. Accounts agreed at sign-up, so they don't see them. */
async function agree(page: Page) {
  const adult = page.getByLabel("I am 18 or older.");
  if ((await adult.count()) === 0) return;
  await adult.check();
  await page.getByLabel(/I agree to the Terms of Use/).check();
}

/** Walk the real onboarding as a student who wants Marketing / Brand Manager. */
async function onboardAsStudent(page: Page) {
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
}

test("a student can onboard and gets a personal feed with reasons", async ({ page }) => {
  await onboardAsStudent(page);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Good (morning|afternoon|evening)/);
  const first = page.locator("article").first();
  await expect(first).toBeVisible();
  await expect(first.getByText("Why it matters to you")).toBeVisible();
  await expect(first.getByText("What to do")).toBeVisible();
});

test("a story's summary and pointers stay hidden until you ask for them", async ({ page }) => {
  await onboardAsStudent(page);
  const card = page.locator("article").first();
  await expect(card.getByRole("region", { name: "Summary" })).toBeHidden();
  await expect(card.getByText("Quick pointers")).toHaveCount(0);
  const toggle = card.getByRole("button", { name: "Summary and pointers" });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await expect(card.getByRole("button", { name: "Hide summary" })).toHaveAttribute("aria-expanded", "true");
  await expect(card.getByRole("region", { name: "Summary" })).toBeVisible();
  await expect(card.getByRole("region", { name: "Summary" })).toContainText(/Read the full story at|didn't share more/);
  await card.getByRole("button", { name: "Hide summary" }).click();
  await expect(card.getByRole("region", { name: "Summary" })).toBeHidden();
});

test("a reader can follow at most four fields", async ({ page }) => {
  await page.goto("/onboarding");
  await page.getByRole("radio", { name: /I'm a student/ }).click();
  await agree(page);
  await page.getByRole("button", { name: "Continue" }).click();

  for (const field of ["Marketing", "Finance & Banking", "Data & AI", "Healthcare & Life Sciences"]) {
    await page.getByRole("button", { name: new RegExp(`^${field}`) }).click();
  }
  await expect(page.getByText("4 of 4")).toBeVisible();
  const fifth = page.getByRole("button", { name: /^Legal & Compliance/ });
  await expect(fifth).toHaveAttribute("aria-disabled", "true");
  await fifth.click({ force: true }); // aria-disabled, so nothing happens
  await expect(fifth).toHaveAttribute("aria-pressed", "false");

  await page.getByRole("button", { name: /^Data & AI/ }).click();
  await expect(page.getByText("3 of 4")).toBeVisible();
  await expect(fifth).toHaveAttribute("aria-disabled", "false");
});

test("chosen fields stay in view as removable chips", async ({ page }) => {
  await page.goto("/onboarding");
  await page.getByRole("radio", { name: /I'm a student/ }).click();
  await agree(page);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: /^Marketing/ }).click();
  await page.getByRole("button", { name: /^Legal & Compliance/ }).click();
  const chosen = page.getByRole("list", { name: "Chosen fields" });
  await expect(chosen.getByRole("button", { name: "Remove Marketing" })).toBeVisible();
  await page.getByRole("button", { name: /^Hospitality/ }).scrollIntoViewIfNeeded();
  await expect(chosen).toBeInViewport(); // the bar sticks while the long list scrolls
  await chosen.getByRole("button", { name: "Remove Marketing" }).click();
  await expect(page.getByText("1 of 4")).toBeVisible();
  await expect(chosen.getByRole("button", { name: "Remove Marketing" })).toHaveCount(0);
});

test("the feed says when it was updated and can be refreshed", async ({ page }) => {
  await onboardAsStudent(page);
  await expect(page.getByText(/Updated (just now|\d+m ago)/)).toBeVisible();
  await page.getByRole("button", { name: "Refresh" }).click();
  await expect(page.getByText(/Updated just now/)).toBeVisible();
  await expect(page.locator("article").first()).toBeVisible();
});

test("the app shell appears before the profile has loaded", async ({ page }) => {
  await onboardAsStudent(page);
  await page.route("**/api/profile/*", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await route.continue();
  });
  await page.goto("/explore");
  await expect(page.getByRole("navigation", { name: "Main" }).first()).toBeVisible({ timeout: 1000 });
  await expect(page.getByRole("heading", { level: 1, name: /See what each job asks for/ })).toBeVisible();
});

test("management students get quick picks for roles, companies and skills", async ({ page }) => {
  await page.goto("/onboarding");
  await page.getByRole("radio", { name: /I'm a student/ }).click();
  await agree(page);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: /^Marketing/ }).click();
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByText("Popular with management students")).toBeVisible();
  const roleQuick = page.getByRole("list", { name: /Popular target roles for management students/i });
  await roleQuick.getByRole("button", { name: /^\+ / }).first().click();
  await expect(page.getByRole("list", { name: "Selected: Target roles" }).getByRole("button", { name: /^Remove / })).toHaveCount(1);
  await page.getByRole("button", { name: "Continue" }).click();

  const companyQuick = page.getByRole("list", { name: /Popular companies for management students/i });
  await companyQuick.getByRole("button", { name: /^\+ / }).first().click();
  await expect(page.getByRole("list", { name: "Selected: Companies" }).getByRole("button", { name: /^Remove / })).toHaveCount(1);
  await page.getByRole("button", { name: "Continue" }).click();

  const skillQuick = page.getByRole("list", { name: /Popular skills and tools for management students/i });
  await expect(skillQuick.getByRole("button", { name: /^\+ / }).first()).toBeVisible();
});

test("the new fields are there: digital transformation, platform businesses and B2B", async ({ page }) => {
  await page.goto("/onboarding");
  await page.getByRole("radio", { name: /I'm a student/ }).click();
  await agree(page);
  await page.getByRole("button", { name: "Continue" }).click();
  for (const field of ["Digital Transformation", "Platform Businesses", "B2B Business"]) {
    await expect(page.getByRole("button", { name: new RegExp(`^${field}`) })).toBeVisible();
  }
});

test("job descriptions: add two and see what is missing across them", async ({ page }) => {
  await onboardAsStudent(page);
  await page.goto("/career");
  await page.getByRole("tab", { name: "Job descriptions" }).click();
  await expect(page.getByText("No job descriptions yet")).toBeVisible();

  const add = async (title: string, text: string) => {
    await page.getByRole("button", { name: "Add a job description" }).first().click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Paste the job description").fill(text);
    await dialog.getByLabel(/Name it/).fill(title);
    await dialog.getByRole("button", { name: "Add job description" }).click();
    await expect(dialog).toBeHidden();
  };
  await add("Brand Manager at HUL", "Brand Manager. You will own the brand plan, report in Power BI and Excel, and pull insight with SQL every week.");
  await add("Marketing Analyst", "Marketing Analyst. Daily work in Excel, Power BI and SQL, with a weekly readout to the brand team.");

  await expect(page.getByRole("heading", { name: /Across your 2 job descriptions/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Brand Manager at HUL" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Marketing Analyst" })).toBeVisible();
  await expect(page.getByText("2/2").first()).toBeVisible(); // asked for in both

  await page.getByRole("button", { name: "Remove Marketing Analyst" }).click();
  await expect(page.getByRole("heading", { name: "Marketing Analyst" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: /Across your job description/ })).toBeVisible();
});

test("text with no known skills is turned down with a helpful message", async ({ page }) => {
  await onboardAsStudent(page);
  await page.goto("/career");
  await page.getByRole("tab", { name: "Job descriptions" }).click();
  await page.getByRole("button", { name: "Add a job description" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Paste the job description").fill("We want a friendly person who enjoys long walks and quiet afternoons in a very nice office.");
  await dialog.getByRole("button", { name: "Add job description" }).click();
  await expect(dialog.getByRole("alert")).toContainText("couldn't find any skills");
});

test("the home page introduces the app, shows live numbers and lets you peek at a role", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Career news that fits you." })).toBeVisible();
  await expect(page.getByText("Right now")).toBeVisible();
  await expect(page.getByText("job titles", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "A news feed built around your next move" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "What we are careful about" })).toBeVisible();

  await page.getByLabel("Job title").fill("brand manager");
  await page.getByRole("button", { name: /^Brand Manager\s+Marketing/ }).click(); // the result, not the example chip
  await expect(page.getByRole("heading", { level: 4, name: "Brand Manager" })).toBeVisible();
  await expect(page.getByText("Skills", { exact: true })).toBeVisible();
  await expect(page.getByText(/companies in our lists hire for this kind of work/)).toBeVisible();

  await page.getByText("Do I need an account?").click();
  await expect(page.getByText(/You can try Vantage as a guest/)).toBeVisible();
});

test("signed-out visitors are sent to the login page", async ({ page }) => {
  await page.goto("/feed");
  await page.waitForURL("**/login");
  await expect(page.getByRole("heading", { level: 1, name: "Welcome back" })).toBeVisible();
});

test("an account: sign up, onboard, see the email, log out, log back in", async ({ page }) => {
  const email = `e2e+${Date.now()}${Math.floor(Math.random() * 1e4)}@example.com`;
  const password = "correct horse battery";

  await page.goto("/login?mode=signup");
  await expect(page.getByRole("heading", { level: 1, name: "Make your account" })).toBeVisible();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("short");
  await expect(page.getByRole("button", { name: "Create account" })).toBeDisabled(); // until both boxes are ticked
  await agree(page);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.locator("form").getByRole("alert")).toContainText("at least 8 characters");

  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/onboarding");

  await page.getByRole("radio", { name: /I'm a student/ }).click();
  await agree(page);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: /^Marketing/ }).click();
  for (const _ of ["roles", "companies", "skills"]) await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Show me my feed" }).click();
  await page.waitForURL("**/feed");

  await page.goto("/profile");
  await expect(page.getByText(email.toLowerCase())).toBeVisible();
  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL((url) => url.pathname === "/");
  await expect(page.getByRole("link", { name: "Log in" }).first()).toBeVisible();

  await page.goto("/feed"); // the cookie is gone, so the app sends you to log in
  await page.waitForURL("**/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("not the password");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.locator("form").getByRole("alert")).toContainText("match");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/feed");
  await expect(page.locator("article").first()).toBeVisible();
});

test("nothing is kept until a guest confirms their age and agrees to the terms", async ({ page }) => {
  await page.goto("/onboarding");
  await page.getByRole("radio", { name: /I'm a student/ }).click();
  const next = page.getByRole("button", { name: "Continue" });
  await expect(next).toBeDisabled();
  await page.getByLabel("I am 18 or older.").check();
  await expect(next).toBeDisabled();
  await page.getByLabel(/I agree to the Terms of Use/).check();
  await expect(next).toBeEnabled();
  await page.getByLabel("I am 18 or older.").uncheck();
  await expect(next).toBeDisabled();
});

test("the terms and privacy policy pages are there and cover the DPDP Act and the GDPR", async ({ page }) => {
  await page.goto("/terms");
  await expect(page.getByRole("heading", { level: 1, name: "Terms of Use" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Information, not advice" })).toBeVisible();
  await expect(page.getByText(/You must be 18 or older/)).toBeVisible();

  await page.goto("/privacy");
  await expect(page.getByRole("heading", { level: 1, name: "Privacy Policy" })).toBeVisible();
  await expect(page.getByText(/Digital Personal\s+Data Protection Act, 2023/)).toBeVisible();
  await expect(page.getByText(/General Data Protection Regulation/)).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Your rights", exact: true })).toBeVisible();
  await expect(page.getByText("Grievance officer", { exact: true })).toBeVisible();
  await expect(page.getByRole("note")).toContainText("not legal advice"); // shown until the operator fills in their details
});

test("your data: download a copy, then delete it all as a guest", async ({ page }) => {
  await onboardAsStudent(page);
  await page.goto("/profile");
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download my data" }).click()]);
  expect(download.suggestedFilename()).toBe("vantage-my-data.json");

  await page.getByRole("button", { name: "Delete my account and data" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText(/can't be undone/)).toBeVisible();
  await dialog.getByRole("button", { name: "Yes, delete everything" }).click();
  await page.waitForURL((url) => url.pathname === "/");
  await expect(page.getByText("Your account and data have been deleted.")).toBeVisible();
  await page.goto("/feed");
  await page.waitForURL("**/login"); // nothing left on this device
});

test("deleting an account asks for the password first", async ({ page }) => {
  const email = `e2e+del${Date.now()}${Math.floor(Math.random() * 1e4)}@example.com`;
  await page.goto("/login?mode=signup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct horse battery");
  await agree(page);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/onboarding");
  await page.getByRole("radio", { name: /I'm a student/ }).click();
  await expect(page.getByLabel("I am 18 or older.")).toHaveCount(0); // an account already agreed
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: /^Marketing/ }).click();
  for (const _ of ["roles", "companies", "skills"]) await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Show me my feed" }).click();
  await page.waitForURL("**/feed");

  await page.goto("/profile");
  await page.getByRole("button", { name: "Delete my account and data" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Yes, delete everything" })).toBeDisabled();
  await dialog.getByLabel("Enter your password to confirm").fill("not my password");
  await dialog.getByRole("button", { name: "Yes, delete everything" }).click();
  await expect(dialog.getByRole("alert")).toContainText("Enter your password");
  await dialog.getByLabel("Enter your password to confirm").fill("correct horse battery");
  await dialog.getByRole("button", { name: "Yes, delete everything" }).click();
  await page.waitForURL((url) => url.pathname === "/");
  await expect(page.getByText("Your account and data have been deleted.")).toBeVisible();

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct horse battery");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.locator("form").getByRole("alert")).toContainText("don't match"); // the account is really gone
});

test("saving a story adds it to the reading list", async ({ page }) => {
  await onboardAsStudent(page);
  const card = page.locator("article").first();
  const title = (await card.locator("h2").innerText()).trim();
  await card.getByRole("button", { name: "Save" }).click();
  await expect(card.getByRole("button", { name: "Saved" })).toBeVisible();
  await page.goto("/saved");
  await expect(page.getByRole("heading", { name: /^Your reading list$/ })).toBeVisible();
  await expect(page.getByText(title.slice(0, 40), { exact: false }).first()).toBeVisible();
});

test("explore: pick a field, open a niche role, follow it, and see its gaps", async ({ page }) => {
  await onboardAsStudent(page);
  await page.goto("/explore");
  await page.getByRole("button", { name: /Finance & Banking/ }).click();
  await page.getByPlaceholder(/Search job titles/).fill("actuar");
  await page.getByRole("link", { name: /^Actuarial Analyst/ }).first().click(); // the curated role ranks first, ahead of imported title variants

  await expect(page.getByRole("heading", { level: 1, name: "Actuarial Analyst" })).toBeVisible();
  await expect(page.getByText("What employers ask for")).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: /^Actuarial Modeling$/ })).toBeVisible();
  await page.getByRole("button", { name: /Follow this role/ }).click();
  await expect(page.getByRole("button", { name: /Following/ })).toBeVisible();

  await page.goto("/career");
  await expect(page.getByRole("heading", { name: /Actuarial Analyst/ }).first()).toBeVisible();
});

test("search finds roles, companies and skills from anywhere", async ({ page, isMobile }) => {
  await onboardAsStudent(page);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible(); // the shell (and its key handler) is mounted
  if (isMobile) await page.getByRole("button", { name: "Search" }).click();
  else await page.keyboard.press("/");
  await page.getByPlaceholder(/Try/).fill("kubernetes");
  await expect(page.getByRole("dialog").getByText("Kubernetes").first()).toBeVisible();
  await page.getByPlaceholder(/Try/).fill("infosys");
  await expect(page.getByRole("dialog").getByRole("link", { name: /Infosys/ }).first()).toBeVisible(); // the company and any stories about it
});

test("theme choice sticks after a reload", async ({ page }) => {
  await onboardAsStudent(page);
  await page.goto("/profile");
  await page.getByRole("tab", { name: "Dark" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("tab", { name: "System" }).click();
  await expect(page.locator("html")).not.toHaveAttribute("data-theme", /.+/);
});

test("getting the job switches the profile from job hunting to working", async ({ page }) => {
  await onboardAsStudent(page);
  await page.goto("/profile");
  await page.getByRole("button", { name: "I got the job" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByPlaceholder("Search companies").fill("ITC");
  await dialog.getByRole("button", { name: /^ITC/ }).first().click();
  await dialog.getByPlaceholder("Search roles").fill("Brand Manager");
  await dialog.getByRole("button", { name: /^Brand Manager/ }).first().click();
  await dialog.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByRole("main").getByText("Brand Manager at ITC")).toBeVisible();
  await expect(page.getByRole("button", { name: "I changed jobs" })).toBeVisible();
});

test.describe("accessibility (axe, WCAG 2 A/AA)", () => {
  for (const path of ["/feed", "/explore", "/career", "/profile"]) {
    test(`no serious violations on ${path}`, async ({ page }) => {
      await onboardAsStudent(page);
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      if (path === "/feed") await expect(page.locator("article").first()).toBeVisible(); // stories arrive after the heading
      await page.waitForTimeout(800); // let entrance animations finish so contrast is measured on final colours
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
      const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(serious.map((v) => `${v.id}: ${v.nodes.length} nodes`)).toEqual([]);
    });
  }
});

test("the job description screen and its add sheet have no serious accessibility violations", async ({ page }) => {
  await onboardAsStudent(page);
  await page.goto("/career");
  await page.getByRole("tab", { name: "Job descriptions" }).click();
  await page.getByRole("button", { name: "Add a job description" }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.waitForTimeout(600);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious.map((v) => `${v.id}: ${v.nodes.length} nodes`)).toEqual([]);
});

test("the home page and login page have no serious accessibility violations", async ({ page }) => {
  for (const path of ["/", "/login", "/terms", "/privacy"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForTimeout(800);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${path} ${v.id}: ${v.nodes.length} nodes`)).toEqual([]);
  }
});

test("the onboarding screen has no serious accessibility violations", async ({ page }) => {
  await page.goto("/onboarding");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.waitForTimeout(600);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious.map((v) => `${v.id}: ${v.nodes.length} nodes`)).toEqual([]);
});
