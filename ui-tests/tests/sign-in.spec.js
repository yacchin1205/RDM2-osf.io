const { test, expect } = require('@playwright/test');

test.describe('Sign In Flow', () => {
  test('should complete sign-in flow successfully', async ({ page }) => {
    // Get username from environment variable
    const username = process.env.TEST_USERNAME;
    if (!username) {
      throw new Error('TEST_USERNAME environment variable is required');
    }

    console.log('Navigating to localhost:5000...');
    await page.goto('/');

    console.log('Looking for Sign In button...');
    const signInButton = page.locator('[data-test-sign-in-button]');
    await signInButton.waitFor({ timeout: 10000 });
    await signInButton.click();

    console.log('Waiting for sign-in page to load...');
    await page.waitForLoadState('networkidle');

    console.log(`Entering username: ${username}`);
    const usernameField = page.locator('#username');
    await usernameField.waitFor({ timeout: 10000 });
    await usernameField.fill(username);

    console.log('Clicking submit button...');
    const submitButton = page.locator('#submit');
    await submitButton.waitFor({ timeout: 10000 });
    await submitButton.click();

    console.log('Waiting for page response after submit...');
    await page.waitForLoadState('networkidle', { timeout: 30000 });

    console.log('Sign-in flow completed successfully!');
  });
});