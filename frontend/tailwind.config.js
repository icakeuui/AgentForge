/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        'bg-soft': 'var(--color-bg-soft)',
        surface: 'var(--color-surface)',
        border: 'var(--color-border)',
        primary: 'var(--color-primary)',
        'primary-hover': 'var(--color-primary-hover)',
        success: 'var(--color-success)',
        'success-soft': 'var(--color-success-soft)',
        error: 'var(--color-error)',
        'error-soft': 'var(--color-error-soft)',
        warning: 'var(--color-warning)',
        'warning-soft': 'var(--color-warning-soft)',
        info: 'var(--color-info)',
        'info-soft': 'var(--color-info-soft)',
        'text-main': 'var(--color-text-main)',
        'text-sub': 'var(--color-text-sub)',
        'text-muted': 'var(--color-text-muted)',
      },
      borderRadius: {
        'token-md': 'var(--radius-md)',
        'token-lg': 'var(--radius-lg)',
      },
      boxShadow: {
        'token-sm': 'var(--shadow-sm)',
        'token-xl': 'var(--shadow-xl)',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
    },
  },
  plugins: [],
}
