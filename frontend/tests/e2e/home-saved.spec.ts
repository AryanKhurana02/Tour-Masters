import { test, expect } from '@playwright/test';

test.describe('Landing & Saved pages', () => {
  test('Saved trips page shows eyebrow and Data note', async ({ page, baseURL }) => {
    // Visit the saved trips route (uses baseURL from playwright.config.ts)
    await page.goto('/saved');

    // Eyebrow expected on saved page (design: "SAVED ON THIS DEVICE")
    const eyebrow = page.getByText(/SAVED ON THIS DEVICE/i);
    await expect(eyebrow).toBeVisible({ timeout: 5000 });

    // Data note present at page end
    const dataNote = page.getByText(/About this data/i);
    await expect(dataNote).toBeVisible({ timeout: 5000 });

    // Crowd numbers include the word "estimated" somewhere on the page
    const estimated = page.getByText(/estimated/i);
    await expect(estimated).toBeVisible({ timeout: 5000 });
  });
});
