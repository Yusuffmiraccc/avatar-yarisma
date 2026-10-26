import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', css: true, restoreMocks: true, include: ['src/test/**/*.test.{ts,tsx}'] },
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
});

