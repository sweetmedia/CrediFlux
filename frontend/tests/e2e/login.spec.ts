import { expect, test } from "@playwright/test";

test("la página de login carga", async ({ page }) => {
  const response = await page.goto("/login");
  expect(response?.ok()).toBeTruthy();
  await expect(page.locator("input[type=email], input[name=email]").first()).toBeVisible();
});
