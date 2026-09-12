import { Page } from "@playwright/test";

export async function login(page: Page, username = "energy.manager", password = "gridmind-demo") {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/dashboard");
}
