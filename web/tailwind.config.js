/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: { ink: '#19231f', muted: '#718078', canvas: '#f5f6f2', line: '#e7ebe5', brand: '#216b50', lime: '#d8ed6a', danger: '#b74d43', amber: '#a66319' },
      boxShadow: { panel: '0 14px 38px rgba(20, 37, 29, .055)' },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
};
