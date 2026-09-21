import { expect, type Page } from "@playwright/test";

/** Tick the two boxes a guest must tick before we keep any data. Accounts agreed at sign-up, so they don't see them. */
export async function agree(page: Page) {
  const adult = page.getByLabel("I am 18 or older.");
  if ((await adult.count()) === 0) return;
  await adult.check();
  await page.getByLabel(/I agree to the Terms of Use/).check();
}

/** Walk the real onboarding as a student who wants Marketing and Brand Manager, and land on the feed. */
export async function onboardAsStudent(page: Page) {
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
  await expect(page.locator("article").first()).toBeVisible();
}
