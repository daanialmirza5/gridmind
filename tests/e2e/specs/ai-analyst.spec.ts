import { test, expect } from "@playwright/test";
import { login } from "./login";

test("Scenario 5: ask AI analyst and inspect grounded evidence", async ({ page }) => {
  await login(page);
  await page.goto("/ai-analyst");
  await expect(page.getByRole("heading", { name: "AI Energy Analyst" })).toBeVisible();

  await page.getByText("What are the largest savings opportunities?").click();
  await expect(page.getByText("confidence")).toBeVisible({ timeout: 15_000 });
  await page.getByText("Evidence used").first().click();
  await expect(page.locator("pre").first()).toBeVisible();
});
