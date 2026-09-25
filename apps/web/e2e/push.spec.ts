import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { onboardAsStudent } from "./helpers";

// Real Chromium already supports the Push/Notification APIs, so the card's own support check
// (useSyncExternalStore reading pushSupported()) passes without mocking. What's stubbed is the
// permission prompt and the PushManager subscription itself, so the test doesn't depend on a
// real push service or a real service worker registration. Each call gets its own random endpoint:
// the backend's endpoint column is unique per device, and reusing one across tests/runs (against a
// real, file-backed dev database, not a fresh one per test) would collide with a previous run's row.
async function stubPush(page: import("@playwright/test").Page, permission: "default" | "granted" | "denied" = "default") {
  const endpoint = `https://push.test/mock-${Math.random().toString(36).slice(2)}`;
  await page.addInitScript(
    ({ initialPermission, endpoint }) => {
      const notificationMock = {
        permission: initialPermission as string,
        requestPermission: async () => {
          notificationMock.permission = notificationMock.permission === "default" ? "granted" : notificationMock.permission;
          return notificationMock.permission;
        },
      };
      let subscription: { endpoint: string; toJSON: () => object; unsubscribe: () => Promise<boolean> } | null = null;
      const fakeSubscription = () => ({
        endpoint,
        toJSON: () => ({ endpoint, keys: { p256dh: "mock-p256dh", auth: "mock-auth" } }),
        unsubscribe: async () => {
          subscription = null;
          return true;
        },
      });
      const pushManager = {
        getSubscription: async () => subscription,
        subscribe: async () => {
          subscription = fakeSubscription();
          return subscription;
        },
      };
      Object.defineProperty(window, "Notification", { configurable: true, value: notificationMock });
      Object.defineProperty(window, "PushManager", { configurable: true, value: function () {} });
      const readyRegistration = { pushManager };
      Object.defineProperty(navigator, "serviceWorker", {
        configurable: true,
        value: { ready: Promise.resolve(readyRegistration), register: async () => readyRegistration },
      });
    },
    { initialPermission: permission, endpoint },
  );
}

const dialog = (page: import("@playwright/test").Page) => page.getByRole("region", { name: "Notifications" });

test.describe("push notification preferences", () => {
  test("lists every category and turns notifications on, subscribing with the checked ones", async ({ page }) => {
    await stubPush(page, "default");
    await onboardAsStudent(page);
    await page.goto("/profile");

    const card = dialog(page);
    await expect(card.getByText("Daily streak")).toBeVisible();
    await expect(card.getByText("News alerts")).toBeVisible();
    await expect(card.getByText("Games calling")).toBeVisible();

    // Streak and News are checked by default; uncheck News, leave Streak checked.
    await card.getByLabel("News alerts").uncheck();
    await card.getByRole("button", { name: "Turn on notifications" }).click();
    await expect(card.getByRole("button", { name: "Turn off notifications" })).toBeVisible();
    await expect(card.getByLabel("Daily streak")).toBeChecked();
    await expect(card.getByLabel("News alerts")).not.toBeChecked();
  });

  test("turning notifications off unsubscribes and shows the enable button again", async ({ page }) => {
    await stubPush(page, "granted");
    await onboardAsStudent(page);
    await page.goto("/profile");
    const card = dialog(page);
    await card.getByRole("button", { name: "Turn on notifications" }).click();
    await expect(card.getByRole("button", { name: "Turn off notifications" })).toBeVisible();

    await card.getByRole("button", { name: "Turn off notifications" }).click();
    await expect(card.getByRole("button", { name: "Turn on notifications" })).toBeVisible();
  });

  test("a blocked permission shows a message instead of the toggles", async ({ page }) => {
    await stubPush(page, "denied");
    await onboardAsStudent(page);
    await page.goto("/profile");
    const card = dialog(page);
    await expect(card.getByText(/blocked for Vantage/)).toBeVisible();
    await expect(card.getByRole("button", { name: "Turn on notifications" })).toHaveCount(0);
  });

  test("has no serious accessibility violations", async ({ page }) => {
    await stubPush(page, "default");
    await onboardAsStudent(page);
    await page.goto("/profile");
    await expect(dialog(page).getByText("Daily streak")).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  });
});
