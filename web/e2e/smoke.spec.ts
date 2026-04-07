import { test, expect } from "@playwright/test";

test("user home loads heading", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Smart Study Assistant/i })).toBeVisible();
});

test("admin dev page loads", async ({ page }) => {
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: /Dev admin/i })).toBeVisible();
});
