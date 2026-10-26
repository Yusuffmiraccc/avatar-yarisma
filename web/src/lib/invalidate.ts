import type { QueryClient } from '@tanstack/react-query';

export function invalidateInventoryQueries(queryClient: QueryClient) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ['lots'] }),
    queryClient.invalidateQueries({ queryKey: ['movements'] }),
    queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
  ]);
}

export function invalidateProductionQueries(queryClient: QueryClient, orderId: number) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ['production'] }),
    queryClient.invalidateQueries({ queryKey: ['production-order', orderId] }),
    queryClient.invalidateQueries({ queryKey: ['lots'] }),
    queryClient.invalidateQueries({ queryKey: ['movements'] }),
    queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    queryClient.invalidateQueries({ queryKey: ['production-costs'] }),
  ]);
}
