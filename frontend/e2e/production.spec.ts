import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test('production debugger and PostgreSQL health', async ({ page, request }) => {
  const health = await request.get('https://ai-time-travel-debugger-api.onrender.com/health');
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toMatchObject({ status: 'ok' });

  const dbHealth = await request.get('https://ai-time-travel-debugger-api.onrender.com/health/db');
  expect(dbHealth.ok()).toBeTruthy();
  const db = await dbHealth.json();
  expect(db.database).toBe('postgresql');
  expect(db.database_connected).toBe(true);

  const traceFile = fs.readFileSync('../examples/demo.trace');
  const upload = await request.post('https://ai-time-travel-debugger-api.onrender.com/api/v1/traces/upload', {
    multipart: {
      file: { name: 'demo.trace', mimeType: 'application/json', buffer: traceFile },
    },
  });
  expect(upload.ok()).toBeTruthy();

  const trace = await request.get('https://ai-time-travel-debugger-api.onrender.com/api/v1/traces/trc_demo_001');
  expect(trace.ok()).toBeTruthy();
  expect((await trace.json()).steps.length).toBe(4);

  await page.goto('/');
  await expect(page.getByText('Agent Time-Travel Debugger')).toBeVisible();
  await expect(page.getByText('TIMELINE SCRUBBER')).toBeVisible();
  await expect(page.getByText('Loaded 4 recorded steps')).toBeVisible();
  await expect(page.getByText('Inspector')).toBeVisible();

  const fork = page.getByRole('button', { name: /Fork & Replay Branch/ });
  await expect(fork).toBeEnabled();
  await fork.click();
  await expect(page.getByText(/Created trc_branch_/)).toBeVisible();
});
