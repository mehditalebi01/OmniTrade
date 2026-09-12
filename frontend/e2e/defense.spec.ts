import { expect, test } from '@playwright/test';

async function signIn(page: import('@playwright/test').Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Sign in' }).click();
}

test('workflow lab validates the visible graph, supports undo, and gives safe suggestions', async ({ page }) => {
  await signIn(page);
  await page.getByRole('tab', { name: 'Workflow Lab' }).click();
  await expect(page.getByText('Advanced Workflow Lab')).toBeVisible();
  await page.locator('.react-flow__node[data-id="start"]').click({ force: true });
  await expect(page.getByText('Smart next nodes')).toBeVisible();
  await page.keyboard.press('Delete');
  await page.getByRole('button', { name: 'Validate' }).click();
  await expect(page.getByText(/validation errors/)).toBeVisible();
  await page.keyboard.press('Control+z');
  await page.getByRole('button', { name: 'Validate' }).click();
  await expect(page.getByText('Graph is valid')).toBeVisible();
});

test('analysis options are closed selectors and reports show agent views', async ({ page }) => {
  await signIn(page);
  await expect(page.getByText('From market evidence to an explainable decision.')).toBeVisible();
  await page.getByRole('tab', { name: 'New Analysis' }).click();
  await expect(page.getByText('Specialist branches')).toBeVisible();
  await expect(page.getByLabel('Stock ticker')).toHaveAttribute('role', 'combobox');
  await expect(page.getByLabel('Quick analysis model')).toHaveAttribute('role', 'combobox');
  await expect(page.getByLabel('Deep reasoning model')).toHaveAttribute('role', 'combobox');
  await expect(page.getByLabel('Model calls')).toHaveValue('30');
  await page.getByRole('tab', { name: 'Reports' }).click();
  await expect(page.getByText('Browse saved reports and read every agent point of view.')).toBeVisible();
  await expect(page.getByText('Specialist analyst views')).toBeVisible();
  await expect(page.getByText('Bull and bear research debate')).toBeVisible();
  await expect(page.getByText('Risk team views')).toBeVisible();
});
