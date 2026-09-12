import { test, expect } from "@playwright/test";
import { login } from "./login";

test("Scenario 4: run optimization scenario, compare, and save", async ({ page }) => {
  await login(page);
  await page.goto("/optimization");
  await expect(page.getByRole("heading", { name: "Energy Optimization Lab" })).toBeVisible();

  await page.getByRole("button", { name: "balanced" }).first().click();
  await expect(page.getByText("Baseline vs Scenario")).toBeVisible();
  await expect(page.getByText("Comfort impact")).toBeVisible({ timeout: 15_000 });

  await page.getByRole("button", { name: "Save scenario" }).click();
  await expect(page.getByText("Scenario saved")).toBeVisible({ timeout: 10_000 });

  await page.goto("/scenarios");
  await expect(page.getByRole("heading", { name: "Scenario Comparison" })).toBeVisible();
  await expect(page.locator("table tbody tr").first()).toBeVisible();
});
