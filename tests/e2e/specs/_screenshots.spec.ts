import { test } from "@playwright/test";
import { login } from "./login";
import fs from "fs";

const OUT_DIR = "../../docs/screenshots";

test.describe("screenshot capture (not part of CI assertions)", () => {
  test.beforeAll(() => {
    fs.mkdirSync(OUT_DIR, { recursive: true });
  });

  test("capture key pages", async ({ page }) => {
    await login(page);
    await page.waitForSelector("text=24H FORECAST");
    await page.waitForFunction(() => document.querySelectorAll(".recharts-line-curve").length > 0, { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${OUT_DIR}/dashboard.png` });

    await page.goto("/buildings/bld-hq");
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `${OUT_DIR}/digital-twin.png` });

    await page.goto("/optimization");
    await page.getByRole("button", { name: "balanced" }).first().click();
    await page.waitForSelector("text=Comfort impact", { timeout: 15000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${OUT_DIR}/optimization-lab.png` });

    await page.goto("/anomalies");
    await page.waitForTimeout(800);
    await page.locator("table tbody tr").first().click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${OUT_DIR}/anomalies.png` });

    await page.goto("/ai-analyst");
    await page.getByText("What are the largest savings opportunities?").click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `${OUT_DIR}/ai-analyst.png` });

    await page.goto("/energy-flow");
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `${OUT_DIR}/energy-flow.png` });
  });
});
