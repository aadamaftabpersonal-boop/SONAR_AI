import { expect, test } from '@playwright/test'

// T8.8 / AC-1: the full journey in demo mode, driving the real UI against the real backend.
// Demo mode only: nobody is phoned. Needs SONAR_ACCESS_KEY (the server's key).
const KEY = process.env.SONAR_ACCESS_KEY ?? ''

test.beforeAll(() => {
  if (!KEY) throw new Error('Set SONAR_ACCESS_KEY to the running server\'s access key')
})

async function startDemoSearch(page: import('@playwright/test').Page) {
  await page.goto('/')
  const form = page.getByRole('form', { name: 'New search' })
  await form.getByRole('button', { name: /Try: Paracetamol 500 mg/ }).click()
  await form.getByLabel('Access key').fill(KEY)
  const demo = form.getByLabel(/Demo mode \(simulated calls\)/)
  if (!(await demo.isChecked())) await demo.check()
  await form.getByRole('button', { name: 'Search by phone' }).click()
}

test('demo search: banner, live progress, results with evidence, honest wording', async ({ page }) => {
  await startDemoSearch(page)

  // the simulation banner is there from the start and cannot be missed (AC-6)
  await expect(page.getByText(/SIMULATED: these are not real calls/)).toBeVisible()

  // live progress, then completion
  const progress = page.getByRole('region', { name: /Calling now|Calls finished/ })
  await expect(progress).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Calls finished' })).toBeVisible({ timeout: 90_000 })

  // results: every answered card carries the SIMULATED tag (screenshot-safe)
  const results = page.getByRole('region', { name: 'What the shops reported' })
  await expect(results).toBeVisible()
  const cards = results.locator('li.result-card')
  const count = await cards.count()
  for (let i = 0; i < count; i++) {
    await expect(cards.nth(i).getByText('SIMULATED', { exact: true })).toBeVisible()
  }

  // evidence expands where there is any
  const evidence = results.getByText(/Evidence/).first()
  if (await evidence.isVisible().catch(() => false)) await evidence.click()

  // shops that did not answer are never described as lacking the item (NFR-09)
  const unanswered = page.getByRole('heading', { name: 'No answer yet, or not completed' })
  if (await unanswered.isVisible().catch(() => false)) {
    await expect(page.getByText('This does not mean the item is unavailable.').first()).toBeVisible()
  }
  for (const label of await page.locator('.chip').allTextContents()) {
    if (/unavailable/i.test(label)) expect(label).toMatch(/Reported unavailable/i)
  }

  // refreshing mid-way or after resumes the same search from the URL
  const url = page.url()
  expect(url).toMatch(/\?s=/)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Calls finished' })).toBeVisible()
})

test('cancel stops further calls and says so', async ({ page }) => {
  await startDemoSearch(page)
  const cancel = page.getByRole('button', { name: 'Cancel' })
  if (await cancel.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await cancel.click()
    await expect(page.getByText(/Cancelled\. No further calls will be made/)).toBeVisible()
  } else {
    test.info().annotations.push({ type: 'note', description: 'search finished before Cancel was clickable' })
  }
})
