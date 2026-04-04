import { test, expect } from "@playwright/test";

test("home loads heading", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Smart Study Assistant/i })).toBeVisible();
});
