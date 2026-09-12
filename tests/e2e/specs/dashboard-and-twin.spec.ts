import { test, expect } from "@playwright/test";
import { login } from "./login";

test("Scenario 1: dashboard -> building -> zone -> energy", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Energy Command Center" })).toBeVisible();
  await expect(page.getByText("Today's Energy")).toBeVisible();

  await page.goto("/buildings");
  await expect(page.getByRole("heading", { name: "Buildings" })).toBeVisible();
  await page.getByRole("link", { name: /Harborview Headquarters/ }).click();
  await expect(page.getByRole("heading", { name: "Harborview Headquarters" })).toBeVisible();
  await expect(page.getByText("Building Digital Twin")).toBeVisible();

  await page.goto("/energy");
  await expect(page.getByRole("heading", { name: "Energy Consumption Analytics" })).toBeVisible();
  await expect(page.getByText("Data Quality")).toBeVisible();
});
