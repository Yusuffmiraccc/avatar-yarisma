import { expect, test, type Route } from '@playwright/test';

const origin = 'http://127.0.0.1:5173';
const lot = {
  lot_id: 1,
  lot_code: 'ET-2026-001',
  product_code: 'ET-KIYMA',
  product_name: 'Dana kıyma',
  role: 'SOURCE',
  depth: 0,
  produced_quantity: '100.000',
  on_hand_quantity: '0.000',
  unit_code: 'KG',
  is_blocked: false,
  supplier_code: 'TED-01',
  supplier_name: 'Demo Tedarikçi',
};
const shipments = [
  { shipment_id: 101, shipment_code: 'SEV-2026-045-A', lot_id: 1, lot_code: 'ET-2026-001', customer_id: 11, customer_code: 'MRK-A', customer_name: 'Market A', quantity: '30.000', unit_code: 'KG', shipped_at: '2026-10-01T10:00:00Z' },
  { shipment_id: 102, shipment_code: 'SEV-2026-045-B', lot_id: 1, lot_code: 'ET-2026-001', customer_id: 12, customer_code: 'MRK-B', customer_name: 'Market B', quantity: '25.000', unit_code: 'KG', shipped_at: '2026-10-02T10:00:00Z' },
  { shipment_id: 103, shipment_code: 'SEV-2026-045-C', lot_id: 1, lot_code: 'ET-2026-001', customer_id: 13, customer_code: 'MRK-C', customer_name: 'Market C', quantity: '30.000', unit_code: 'KG', shipped_at: '2026-10-03T10:00:00Z' },
];
const simulation = {
  origin_lot_codes: ['ET-2026-001'],
  lots: [lot],
  shipments,
  customers: [
    { customer_id: 11, customer_code: 'MRK-A', customer_name: 'Market A', total_quantity: '30.000', lots: { 'ET-2026-001': '30.000' } },
    { customer_id: 12, customer_code: 'MRK-B', customer_name: 'Market B', total_quantity: '25.000', lots: { 'ET-2026-001': '25.000' } },
    { customer_id: 13, customer_code: 'MRK-C', customer_name: 'Market C', total_quantity: '30.000', lots: { 'ET-2026-001': '30.000' } },
  ],
  remaining_stock_total: '0.000',
  second_tier: [],
  second_tier_note: 'İkinci kademe dağıtım yalnızca sistemde kayıtlıysa gösterilir.',
};

test('admin traces ET-2026-001, activates a recall, and a blocked sale is rejected', async ({ page }) => {
  let recallStatus = 'DRAFT';
  let recallCreated = false;

  const fulfillJson = (route: Route, payload: unknown, status = 200) => route.fulfill({
    status,
    contentType: 'application/json',
    headers: { 'access-control-allow-origin': origin },
    body: JSON.stringify(payload),
  });
  const recall = () => ({
    id: 501,
    recall_code: 'GERI-2026-001',
    reason_code: 'QUALITY_ISSUE',
    reason_text: 'Test senaryosu kalite bildirimi.',
    status: recallStatus,
    started_at: recallStatus === 'DRAFT' ? null : '2026-10-26T09:00:00Z',
    total_shipped_quantity: '85.000',
    second_tier_note: 'İkinci kademe dağıtım kayıtlı değil.',
    lots: [{ lot_id: 1, lot_code: 'ET-2026-001', role: 'SOURCE', blocked_at: recallStatus === 'DRAFT' ? null : '2026-10-26T09:00:00Z' }],
    impacts: [],
  });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace('/api/v1', '');
    const method = request.method();

    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: {
        'access-control-allow-origin': origin,
        'access-control-allow-methods': 'GET,POST,PATCH,PUT,DELETE,OPTIONS',
        'access-control-allow-headers': 'Authorization,Content-Type,Idempotency-Key,X-Auth-Retry',
      } });
      return;
    }
    if (path === '/auth/login' && method === 'POST') {
      await fulfillJson(route, { access_token: 'e2e-access', refresh_token: 'e2e-refresh' });
    } else if (path === '/auth/me') {
      await fulfillJson(route, { id: 1, email: 'admin@avatar.demo', display_name: 'Demo Yönetici', roles: ['ADMIN'], permissions: ['reports:read', 'traceability:read', 'recalls:read', 'recalls:manage', 'recalls:resolve', 'lots:read', 'sales:create', 'sales:read', 'costs:read', 'documents:manage'] });
    } else if (path === '/reports/dashboard') {
      await fulfillJson(route, { active_recalls: recallStatus === 'ACTIVE' ? 1 : 0, blocked_lots: recallStatus === 'ACTIVE' ? 1 : 0, completed_production_orders: 1, shipments_shipped: 3, lots_in_stock: 1, open_alerts: 0, stock_value: '0.00' });
    } else if (path === '/recalls' && method === 'GET') {
      await fulfillJson(route, { items: recallCreated ? [recall()] : [], page: 1, page_size: 20, total: recallCreated ? 1 : 0 });
    } else if (path === '/recalls' && method === 'POST') {
      recallCreated = true;
      await fulfillJson(route, recall(), 201);
    } else if (path === '/recalls/501' && method === 'GET') {
      await fulfillJson(route, recall());
    } else if (path === '/recalls/501/simulation') {
      await fulfillJson(route, simulation);
    } else if (path === '/recalls/501/activate' && method === 'POST') {
      recallStatus = 'ACTIVE';
      await fulfillJson(route, recall());
    } else if (path === '/reports/recalls/501/notification-list') {
      await fulfillJson(route, { recall_code: 'GERI-2026-001', status: recallStatus, items: [], second_tier_note: 'İkinci kademe dağıtım kayıtlı değil.' });
    } else if (path === '/traceability/lots/by-code/ET-2026-001/forward') {
      await fulfillJson(route, simulation);
    } else if (path === '/traceability/lots/by-code/ET-2026-001/backward') {
      await fulfillJson(route, { target_lot_code: 'ET-2026-001', lots: [lot], orders: [], suppliers: [{ code: 'TED-01', name: 'Demo Tedarikçi' }] });
    } else if (path === '/lots') {
      await fulfillJson(route, { items: [{ id: 1, lot_code: 'ET-2026-001', product_id: 1, product_code: 'ET-KIYMA', product_name: 'Dana kıyma', supplier_id: 1, status: 'ACTIVE', unit_code: 'KG', initial_quantity: '100.000', on_hand_quantity: recallStatus === 'ACTIVE' ? '0.000' : '15.000', expiry_date: null, received_at: '2026-09-20T10:00:00Z', location_code: 'A1', is_blocked: recallStatus === 'ACTIVE' }], page: 1, page_size: 100, total: 1 });
    } else if (path === '/documents/extract-file' && method === 'POST') {
      expect(request.headers()['content-type']).toMatch(/^multipart\/form-data; boundary=/);
      const body = request.postDataBuffer()?.toString('latin1') || '';
      expect(body).toContain('filename="invoice.txt"');
      expect(body).toContain('name="doc_type"');
      await fulfillJson(route, { id: 701, doc_type: 'INVOICE', source_name: 'invoice.txt', proposed: {}, status: 'PENDING_REVIEW', created_at: '2026-10-26T09:00:00Z' }, 201);
    } else if (path === '/alerts') {
      await fulfillJson(route, { items: [], page: 1, page_size: 5, total: 0 });
    } else if (path === '/sales' && method === 'POST') {
      await fulfillJson(route, { error: { code: 'LOT_BLOCKED', message: 'Geri çağırma nedeniyle lot bloke.' }, request_id: 'e2e-blocked-sale' }, 409);
    } else if (path === '/inventory/movements') {
      await fulfillJson(route, { items: [], page: 1, page_size: 100, total: 0 });
    } else {
      await fulfillJson(route, { items: [], page: 1, page_size: 20, total: 0 });
    }
  });

  await page.goto('/login');
  await page.getByLabel('E-posta').fill('admin@avatar.demo');
  await page.getByLabel('Parola').fill('Avatar-Demo-2026!');
  await page.getByRole('button', { name: 'Giriş yap' }).click();
  await expect(page.getByRole('heading', { name: 'Ana pano' })).toBeVisible();

  await page.getByRole('link', { name: 'Belgeler' }).click();
  await page.getByLabel('Dosya', { exact: true }).setInputFiles({ name: 'invoice.txt', mimeType: 'text/plain', buffer: Buffer.from('Tedarikçi: Test\nDana eti 1 kg 9,70 9,70 lot ET-2026-001') });
  await page.getByRole('button', { name: 'Dosyadan öneri çıkar' }).click();
  await expect(page.getByText('Dosyadan belge önerisi çıkarıldı; stok kaydı oluşmadı.')).toBeVisible();

  await page.getByRole('link', { name: 'Lot izlenebilirliği' }).click();
  await expect(page.getByText('Market A')).toBeVisible();
  await expect(page.getByText('Market B')).toBeVisible();
  await expect(page.getByText('Market C')).toBeVisible();

  await page.getByRole('link', { name: 'Geri çağırmalar' }).click();
  await page.getByRole('button', { name: 'Geri çağırma oluştur' }).click();
  await page.getByLabel('Vaka kodu', { exact: true }).fill('GERI-2026-001');
  await page.getByLabel('Neden kodu', { exact: true }).fill('QUALITY_ISSUE');
  await page.getByPlaceholder('ET-2026-001').fill('ET-2026-001');
  await page.getByLabel('Gerekçe', { exact: true }).fill('Test senaryosu kalite bildirimi.');
  await page.getByRole('button', { name: 'Taslağı oluştur' }).click();
  await page.getByRole('button', { name: 'GERI-2026-001 detayını aç' }).click();

  const marketRows = page.getByRole('table').first();
  await expect(marketRows.getByRole('row', { name: /Market A/ })).toContainText('30');
  await expect(marketRows.getByRole('row', { name: /Market B/ })).toContainText('25');
  await expect(marketRows.getByRole('row', { name: /Market C/ })).toContainText('30');
  await page.getByRole('button', { name: 'Geri çağırmayı aktive et' }).click();
  await page.getByRole('button', { name: 'Aktivasyonu onayla' }).click();
  await expect(page.getByText('Geri alınamaz aktivasyon:')).toBeVisible();
  await expect(page.getByText('Aktif', { exact: true })).toBeVisible();

  const saleAttempt = await page.evaluate(async () => {
    const response = await fetch('http://127.0.0.1:8000/api/v1/sales', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer e2e-access', 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({ customer_id: 11, lines: [{ lot_id: 1, quantity: '1.000' }] }),
    });
    return { status: response.status, body: await response.json() };
  });
  expect(saleAttempt.status).toBe(409);
  expect(saleAttempt.body.error.code).toBe('LOT_BLOCKED');
});
