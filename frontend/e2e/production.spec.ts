import { test, expect } from '@playwright/test';

test('production debugger loads the demo trace and can create a replay branch', async ({ page, request }) => {
  const health = await request.get('https://ai-time-travel-debugger-api.onrender.com/health');
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toMatchObject({ status: 'ok' });

  const trace = await request.get('https://ai-time-travel-debugger-api.onrender.com/api/v1/traces/trc_demo_001');
  expect(trace.ok()).toBeTruthy();
  const traceData = await trace.json();
  expect(traceData.steps.length).toBeGreaterThan(0);

  await page.goto('/');
  await expect(page.getByText('Agent Time-Travel Debugger')).toBeVisible();
  await expect(page.getByText('TIMELINE SCRUBBER')).toBeVisible();
  await expect(page.getByText(/Loaded \d+ recorded steps/)).toBeVisible();

  const fork = page.getByRole('button', { name: /Fork & Replay Branch/ });
  await expect(fork).toBeEnabled();
  await fork.click();
  await expect(page.getByText(/Created trc_branch_/)).toBeVisible();
});
