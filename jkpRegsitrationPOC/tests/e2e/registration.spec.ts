import { test, expect } from '@playwright/test'

test.describe('Satsangi Registration Flow', () => {
  test('redirects to /create by default', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/create/)
  })

  test('shows the full registration form with all sections', async ({ page }) => {
    await page.goto('/create')
    await expect(page.getByText('Personal Details')).toBeVisible()
    await expect(page.getByText('Address Details')).toBeVisible()
    await expect(page.getByText('Other Details')).toBeVisible()
    await expect(page.getByRole('button', { name: /register satsangi/i })).toBeVisible()
  })

  test('validates required fields', async ({ page }) => {
    await page.goto('/create')
    await page.getByRole('button', { name: /register satsangi/i }).click()
    await expect(page.getByText(/first name, last name and phone number are required/i)).toBeVisible()
  })

  test('can create a satsangi and find them via search', async ({ page }) => {
    const ts = Date.now()

    await page.goto('/create')
    await page.locator('input[name="first_name"]').fill(`E2E${ts}`)
    await page.locator('input[name="last_name"]').fill('Tester')
    await page.locator('input[name="phone_number"]').fill('9999000011')
    await page.getByRole('button', { name: /register satsangi/i }).click()

    await expect(page.getByText(/registered! satsangi id/i)).toBeVisible({ timeout: 5000 })
    await expect(page).toHaveURL(/\/search/, { timeout: 10000 })
    await expect(page.getByText(`E2E${ts} Tester`)).toBeVisible({ timeout: 5000 })
  })

  test('can search by phone number', async ({ page }) => {
    const uniquePhone = `555${Date.now().toString().slice(-7)}`
    const ts = Date.now()

    await page.goto('/create')
    await page.locator('input[name="first_name"]').fill(`Phone${ts}`)
    await page.locator('input[name="last_name"]').fill('Test')
    await page.locator('input[name="phone_number"]').fill(uniquePhone)
    await page.getByRole('button', { name: /register satsangi/i }).click()
    await expect(page).toHaveURL(/\/search/, { timeout: 10000 })

    const searchInput = page.getByPlaceholder(/search by name/i)
    await searchInput.fill(uniquePhone)
    await expect(page.getByText(`Phone${ts} Test`)).toBeVisible({ timeout: 5000 })
  })

  test('can search by satsangi ID', async ({ page }) => {
    const ts = Date.now()

    await page.goto('/create')
    await page.locator('input[name="first_name"]').fill(`ID${ts}`)
    await page.locator('input[name="last_name"]').fill('Test')
    await page.locator('input[name="phone_number"]').fill('1112223333')
    await page.getByRole('button', { name: /register satsangi/i }).click()
    await expect(page).toHaveURL(/\/search/, { timeout: 10000 })

    const card = page.locator('h3', { hasText: `ID${ts} Test` }).locator('..')
    const idBadge = card.locator('span.font-mono').first()
    const satsangiId = await idBadge.textContent()
    expect(satsangiId).toBeTruthy()

    const searchInput = page.getByPlaceholder(/search by name/i)
    await searchInput.fill(satsangiId!)
    await expect(page.getByText(`ID${ts} Test`)).toBeVisible({ timeout: 5000 })
  })

  test('navigation between pages works', async ({ page }) => {
    await page.goto('/create')
    await page.getByRole('link', { name: /search/i }).click()
    await expect(page).toHaveURL(/\/search/)

    await page.getByRole('link', { name: /add devotee/i }).click()
    await expect(page).toHaveURL(/\/create/)
    await expect(page.getByText('Personal Details')).toBeVisible()
  })

  test('shows no results for nonsense query', async ({ page }) => {
    await page.goto('/search')
    const searchInput = page.getByPlaceholder(/search by name/i)
    await searchInput.fill('zzzznonexistent99999')
    await expect(page.getByText('No satsangis found.')).toBeVisible({ timeout: 5000 })
  })

  test('dropdowns work correctly', async ({ page }) => {
    await page.goto('/create')
    const genderSelect = page.getByRole('combobox', { name: /gender/i })
    await genderSelect.selectOption('Male')
    await expect(genderSelect).toHaveValue('Male')

    const nationalitySelect = page.getByRole('combobox', { name: /nationality/i })
    await expect(nationalitySelect).toHaveValue('Indian')
  })
})
