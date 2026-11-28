import { test, expect } from '@playwright/test';
import fs from 'node:fs';

const API_URL = process.env.E2E_API_URL || 'https://ai-time-travel-debugger-api.onrender.com';

test('production debugger and PostgreSQL health', async ({ page, request }) => {
  const health = await request.get(`${API_URL}/health`);
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toMatchObject({ status: 'ok' });

  const dbHealth = await request.get(`${API_URL}/health/db`);
  expect(dbHealth.ok()).toBeTruthy();
  const db = await dbHealth.json();
  if (process.env.E2E_EXPECT_POSTGRES !== 'false') expect(db.database).toBe('postgresql');
  expect(db.database_connected).toBe(true);

  const traceFile = fs.readFileSync('../examples/demo.trace');
  const upload = await request.post(`${API_URL}/api/v1/traces/upload`, {
    multipart: {
      file: { name: 'demo.trace', mimeType: 'application/json', buffer: traceFile },
    },
  });
  expect(upload.ok()).toBeTruthy();

  const trace = await request.get(`${API_URL}/api/v1/traces/trc_demo_001`);
  expect(trace.ok()).toBeTruthy();
  expect((await trace.json()).steps.length).toBe(4);

  await page.goto('/');
  await expect(page.getByText('Agent Time-Travel Debugger')).toBeVisible();
  await expect(page.getByText('TIMELINE SCRUBBER')).toBeVisible();
  await expect(page.getByText('Loaded 4 recorded steps')).toBeVisible();
  await expect(page.getByText('Inspector')).toBeVisible();

  // Replay starts at step 3: the later refund result must not be reused,
  // while the earlier order lookup is a safe cache hit.
  const timeline = page.getByRole('slider');
  await timeline.focus();
  await timeline.press('ArrowRight');
  await timeline.press('ArrowRight');
  const toolPicker = page.getByRole('combobox', { name: 'Recorded tool call' });
  await toolPicker.selectOption('step_004');
  await page.getByRole('button', { name: 'Replay tool safely' }).click();
  await expect(page.getByText(/Cache miss for issue_refund before step_003/)).toBeVisible();
  await toolPicker.selectOption('step_002');
  await page.getByRole('button', { name: 'Replay tool safely' }).click();
  await expect(page.getByText(/Cached lookup_order result from before step_003/)).toBeVisible();

  const fork = page.getByRole('button', { name: /Fork & Replay Branch/ });
  await expect(fork).toBeEnabled();
  await fork.click();
  await expect(page.getByText(/Created trc_branch_/)).toBeVisible();
});
