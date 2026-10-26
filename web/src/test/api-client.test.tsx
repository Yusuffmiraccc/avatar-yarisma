import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, __resetApiForTests, apiGet, apiPost, apiPostIdempotent, setSessionTokens } from '../api/client';

describe('API istemcisi', () => {
  beforeEach(() => { __resetApiForTests(); });
  afterEach(() => { vi.unstubAllGlobals(); __resetApiForTests(); });

  it('eşzamanlı üç 401 yanıtında tek refresh isteği yapar ve her isteği bir kez tekrarlar', async () => {
    let refreshCount = 0;
    let authorizedCount = 0;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const request = input instanceof Request ? input : new Request(input);
      const url = new URL(request.url);
      if (url.pathname.endsWith('/auth/refresh')) {
        refreshCount += 1;
        await new Promise((resolve) => setTimeout(resolve, 15));
        return Response.json({ access_token: 'fresh-access', refresh_token: 'rotated-refresh' });
      }
      if (url.pathname.endsWith('/auth/me')) {
        if (request.headers.get('Authorization') === 'Bearer old-access') return Response.json({ error: { code: 'UNAUTHENTICATED', message: 'Expired' } }, { status: 401 });
        authorizedCount += 1;
        return Response.json({ id: authorizedCount, email: 'test@example.com', display_name: 'Test', roles: ['ADMIN'], permissions: [] });
      }
      return Response.json({}, { status: 404 });
    }));
    setSessionTokens({ access_token: 'old-access', refresh_token: 'initial-refresh' });
    const users = await Promise.all([apiGet('/auth/me'), apiGet('/auth/me'), apiGet('/auth/me')]);
    expect(users).toHaveLength(3);
    expect(refreshCount).toBe(1);
    expect(authorizedCount).toBe(3);
    expect(window.sessionStorage.getItem('avatar.refresh')).toBe('rotated-refresh');
  });

  it('backend hata zarfındaki anlaşılır mesajı korur', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ error: { code: 'LOT_BLOCKED', message: 'Geri çağrılan lot sevk edilemez.' }, request_id: 'req-123' }, { status: 409 })));
    await expect(apiPost('/shipments/1/dispatch')).rejects.toMatchObject({ status: 409, code: 'LOT_BLOCKED', message: 'Geri çağrılan lot sevk edilemez.', requestId: 'req-123' });
  });

  it('ağ hatasında aynı kullanıcı eylemi için Idempotency-Key değerini korur', async () => {
    const keys: string[] = [];
    let calls = 0;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const request = input instanceof Request ? input : new Request(input);
      keys.push(request.headers.get('Idempotency-Key') || '');
      calls += 1;
      if (calls === 1) throw new TypeError('network down');
      return Response.json({ id: 7, sale_code: 'SAL-7' }, { status: 201 });
    }));
    await expect(apiPostIdempotent('/sales', { customer_id: 1, lines: [] }, 'sale-submit-1')).rejects.toThrow('network down');
    await apiPostIdempotent('/sales', { customer_id: 1, lines: [] }, 'sale-submit-1');
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBeTruthy();
    expect(keys[1]).toBe(keys[0]);
  });

  it('API hata örneğini istemci tipi olarak oluşturur', () => {
    const error = new ApiError(403, 'Yetkiniz yok.', 'FORBIDDEN');
    expect(error).toBeInstanceOf(Error);
    expect(error.status).toBe(403);
  });
});
