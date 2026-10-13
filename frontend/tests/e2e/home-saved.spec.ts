import { test, expect } from '@playwright/test';

test.describe('Landing & Saved pages', () => {
  test('trip planner submits through the API and displays recommendations', async ({ page }) => {
    const pageErrors: string[] = [];
    const apiFailures: string[] = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('requestfailed', request => {
      if (new URL(request.url()).pathname.startsWith('/api/')) {
        apiFailures.push(request.url());
      }
    });

    await page.goto('/plan');

    await expect(page.getByRole('heading', { name: /Stay on the quieter side/i })).toBeVisible();
    await page.getByRole('button', { name: /Find my quieter places/i }).click();

    await expect(page).toHaveURL(/\/results$/);
    await expect(page.getByText(/Quieter matches · Uttarakhand/i)).toBeVisible();
    await expect(page.getByRole('region', { name: 'Estimated crowd level' }).first()).toBeVisible();
    await expect(page.getByRole('alert')).toHaveCount(0);
    expect(pageErrors).toEqual([]);
    expect(apiFailures).toEqual([]);
  });

  test('Saved trips page shows the empty state and data note', async ({ page }) => {
    // Visit the saved trips route (uses baseURL from playwright.config.ts)
    await page.goto('/saved');

    // Eyebrow expected on saved page (design: "SAVED ON THIS DEVICE")
    const eyebrow = page.getByText(/SAVED ON THIS DEVICE/i);
    await expect(eyebrow).toBeVisible({ timeout: 5000 });

    // Data note present at page end
    const dataNote = page.getByText(/About this data/i);
    await expect(dataNote).toBeVisible({ timeout: 5000 });

    await expect(page.getByRole('heading', { name: /No saved stays yet/i })).toBeVisible();
  });
});
