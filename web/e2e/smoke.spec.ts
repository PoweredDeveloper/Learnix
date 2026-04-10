import { test, expect } from "@playwright/test";

test("admin dev page loads", async ({ page }) => {
  await page.goto("/admin");
  await expect(
    page.getByRole("heading", { name: /Dev admin/i }),
  ).toBeVisible();
});

test("dashboard page loads without session key", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/Open this app/i)).toBeVisible();
});

test("create course page loads", async ({ page }) => {
  await page.goto("/create-course");
  await expect(page.getByRole("heading", { name: /New course/i })).toBeVisible();
});

test("settings page loads", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: /Settings/i })).toBeVisible();
});

test("learnix header is visible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Learnix")).toBeVisible();
});

test("navigation links work", async ({ page }) => {
  await page.goto("/create-course");
  await page.getByText("Back to dashboard").click();
  await expect(page).toHaveURL("/");
});
