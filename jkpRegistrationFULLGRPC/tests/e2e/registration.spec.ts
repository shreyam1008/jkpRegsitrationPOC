/**
 * E2E tests — real browser, real backend.
 *
 * Playwright auto-starts a Vite dev server on :5175 with VITE_GRPC_URL
 * pointing to localhost:8080. The backend must be running separately:
 *   cd server && uv run task dev
 */

import { test, expect } from '@playwright/test'

test.describe('Search Page', () => {
  test('loads and shows heading', async ({ page }) => {
    await page.goto('/search')
    await expect(page.getByRole('heading', { name: 'Devotees' })).toBeVisible()
  })

  test('has search input', async ({ page }) => {
    await page.goto('/search')
    await expect(page.getByPlaceholder(/search by name/i)).toBeVisible()
  })

  test('displays results from the backend', async ({ page }) => {
    await page.goto('/search')
    // Wait for shimmer to disappear and real results to load
    await expect(page.locator('.animate-pulse')).toHaveCount(0, { timeout: 10_000 })
    // Should have at least one result card (data exists from previous tests)
    const cards = page.locator('button.animate-card-in')
    await expect(cards.first()).toBeVisible({ timeout: 5_000 })
  })
})

test.describe('Create Page', () => {
  test('navigates from search to create', async ({ page }) => {
    await page.goto('/search')
    await page.getByRole('button', { name: /add devotee/i }).click()
    await expect(page.getByRole('heading', { name: /add new devotee/i })).toBeVisible()
  })

  test('renders all form sections', async ({ page }) => {
    await page.goto('/create')
    await expect(page.getByText('Personal', { exact: true })).toBeVisible()
    await expect(page.getByText('Government ID', { exact: true })).toBeVisible()
    await expect(page.getByText('Visit', { exact: true })).toBeVisible()
    await expect(page.getByText('Documents', { exact: true })).toBeVisible()
  })

  test('shows required field indicators', async ({ page }) => {
    await page.goto('/create')
    // The 3 mandatory fields + nationality + country have red asterisks
    const requiredMarkers = page.locator('span.text-red-400')
    await expect(requiredMarkers).toHaveCount(5)
  })

  test('back button returns to search', async ({ page }) => {
    await page.goto('/create')
    await page.getByText('Back to Search').click()
    await expect(page.getByRole('heading', { name: 'Devotees' })).toBeVisible()
  })
})
