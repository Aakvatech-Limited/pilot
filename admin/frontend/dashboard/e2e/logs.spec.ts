import { expect, test } from '@playwright/test'

test('Opens a log file', async ({ page }) => {
  await page.goto('/insights/logs')
  await page.getByRole('button', { name: /^frappe\.log/ }).click()

  await expect(page).toHaveURL(/file=frappe\.log/)
})

test('Searches log files', async ({ page }) => {
  await page.goto('/insights/logs')
  await page.getByPlaceholder('Search log files').fill('frappe.log')

  await expect(page.getByRole('button', { name: /^frappe\.log/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /^database\.log/ })).toBeHidden()
})
