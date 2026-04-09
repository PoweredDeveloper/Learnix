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
  await expect(
    page.getByRole("heading", { name: /Create a New Course/i }),
  ).toBeVisible();
});

test("learnix header is visible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Learnix")).toBeVisible();
});

test("navigation links work", async ({ page }) => {
  await page.goto("/create-course");
  await page.getByText("Back to Dashboard").click();
  await expect(page).toHaveURL("/");
});
