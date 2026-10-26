import { QueryClient } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { invalidateInventoryQueries, invalidateProductionQueries } from '../lib/invalidate';

describe('yazma sonrası sorgu güncellemeleri', () => {
  afterEach(() => vi.restoreAllMocks());
  it('alış ve stok değişikliklerinde lot, hareket ve pano verisini yeniler', async () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, 'invalidateQueries').mockResolvedValue();
    await invalidateInventoryQueries(client);
    expect(spy.mock.calls.map(([filters]) => filters?.queryKey)).toEqual([['lots'], ['movements'], ['dashboard']]);
    client.clear();
  });
  it('üretim tamamlanınca emir detayı, maliyet, lot, hareket ve pano cache’ini yeniler', async () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, 'invalidateQueries').mockResolvedValue();
    await invalidateProductionQueries(client, 45);
    expect(spy.mock.calls.map(([filters]) => filters?.queryKey)).toEqual([['production'], ['production-order', 45], ['lots'], ['movements'], ['dashboard'], ['production-costs']]);
    client.clear();
  });
});
