import { test, expect } from "@playwright/test";
import { login } from "./login";

test("Scenario 3: anomaly evidence -> waste event -> recommendation", async ({ page }) => {
  await login(page);

  await page.goto("/anomalies");
  await expect(page.getByRole("heading", { name: "Energy Anomalies" })).toBeVisible();
  const firstRow = page.locator("table tbody tr").first();
  await firstRow.click();
  await expect(page.getByText("Conclusion")).toBeVisible();

  await page.goto("/waste");
  await expect(page.getByRole("heading", { name: "Waste Detection" })).toBeVisible();
  const wasteRow = page.locator("table tbody tr").first();
  await wasteRow.click();
  await expect(page.getByText("Why was this flagged?")).toBeVisible();

  await page.goto("/recommendations");
  await expect(page.getByRole("heading", { name: "Recommendations" })).toBeVisible();
});
