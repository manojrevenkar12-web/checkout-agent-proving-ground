import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

async function accessible(page: import("@playwright/test").Page) {
  await page.waitForTimeout(900);
  const r = await new AxeBuilder({ page }).analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
}

test("outcomes, changes and feeds read the committed report", async ({ page }) => {
  await page.goto("/#/outcomes");
  await expect(page.getByRole("heading", { name: /Bought exactly right/ })).toBeVisible();
  await expect(page.getByRole("region", { name: "Receipt" })).toContainText("Wrong orders per 1,000");
  await accessible(page);
  await page.goto("/#/changes");
  await expect(page.getByRole("heading", { name: /Checkouts keep working/ })).toBeVisible();
  await accessible(page);
  await page.goto("/#/data");
  await expect(page.getByRole("heading", { name: /Feeds that check themselves/ })).toBeVisible();
  await accessible(page);
});

test("buying twice with the same intent replays the ledger", async ({ page }) => {
  await page.goto("/#/order");
  const first = page.getByRole("button", { name: "Buy", exact: true }).first();
  await first.click();
  const result = page.getByRole("region", { name: "Result" });
  await expect(result).toContainText(/Bought|Not bought|declined|reconcile/, { timeout: 20_000 });
  await accessible(page);
  await first.click();
  await expect(result).toContainText(/Replayed from the ledger|Not bought yet/, { timeout: 20_000 });
});

test("a missing report, a failing service and a slow one each show their state", async ({ page }) => {
  await page.route("**/api/results", (r) => r.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "no evaluation yet" }) }));
  await page.goto("/#/outcomes");
  await expect(page.getByText("No evaluation yet")).toBeVisible();
  await page.unroute("**/api/results");
  await page.route("**/api/results", (r) => r.fulfill({ status: 500, contentType: "application/json", body: "{}" }));
  await page.reload();
  await expect(page.getByRole("alert")).toContainText("500");
  await page.unroute("**/api/results");
  await page.route("**/api/results", async (r) => {
    await new Promise((res) => setTimeout(res, 1500));
    await r.continue();
  });
  await page.reload();
  await expect(page.getByRole("status", { name: "Loading the outcome report" })).toBeVisible();
  await page.route("**/api/orders", (r) => r.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "the agent pool is busy" }) }));
  await page.goto("/#/order");
  await page.getByRole("button", { name: "Buy", exact: true }).first().click();
  await expect(page.getByRole("alert")).toContainText("busy");
});
