import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './auth';
import { ToastProvider } from './components/Toast';
import App from './App';
import './styles.css';

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 20_000, retry: (count, error) => count < 1 && !(error instanceof Error && 'status' in error && (error as { status?: number }).status === 403), refetchOnWindowFocus: false }, mutations: { retry: false } } });

createRoot(document.getElementById('root')!).render(
  <StrictMode><QueryClientProvider client={queryClient}><AuthProvider><ToastProvider><App /></ToastProvider></AuthProvider></QueryClientProvider></StrictMode>,
);
