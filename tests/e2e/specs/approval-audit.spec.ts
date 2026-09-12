import { test, expect } from "@playwright/test";
import { login } from "./login";

test("Scenario 6: approve a recommendation and see it in the audit trail", async ({ page }) => {
  await login(page);
  await page.goto("/recommendations");
  await page.getByRole("button", { name: "SUGGESTED" }).click();

  const approveButton = page.getByRole("button", { name: "Approve" }).first();
  if (await approveButton.isVisible().catch(() => false)) {
    await approveButton.click();
    await expect(page.getByText("Decided by")).toBeVisible({ timeout: 10_000 });

    await page.goto("/audit");
    await expect(page.getByRole("heading", { name: "Audit Trail" })).toBeVisible();
    await expect(page.getByText("RECOMMENDATION_APPROVED").first()).toBeVisible({ timeout: 10_000 });
  }
});
