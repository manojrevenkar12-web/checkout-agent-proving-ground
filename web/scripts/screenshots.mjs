// Screenshots for the README: node scripts/screenshots.mjs (with the service on BASE serving web/dist).
import { chromium } from "@playwright/test";
const base = process.env.BASE ?? "http://localhost:8080";
const browser = await chromium.launch(process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {});
const page = await browser.newPage({ viewport: { width: 1360, height: 980 } });
for (const view of ["outcomes", "changes", "data"]) {
  await page.goto(`${base}/#/${view}`);
  await page.waitForTimeout(1300);
  await page.screenshot({ path: `../docs/screenshots/${view}.png` });
}
await page.goto(`${base}/#/order`);
await page.getByRole("button", { name: "Buy", exact: true }).first().click();
await page.waitForTimeout(2500);
await page.screenshot({ path: "../docs/screenshots/order.png" });
await browser.close();
