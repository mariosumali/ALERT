/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['SF Mono', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        bg:       'hsl(var(--bg))',
        surface1: 'hsl(var(--surface-1))',
        surface2: 'hsl(var(--surface-2))',
        surface3: 'hsl(var(--surface-3))',
        border:   'hsl(var(--border))',
        txt:      'hsl(var(--text))',
        muted:    'hsl(var(--muted))',
        'muted-2':'hsl(var(--muted-2))',
        primary:  'hsl(var(--primary))',
        'primary-2': 'hsl(var(--primary-2))',
        success:  'hsl(var(--success))',
        warning:  'hsl(var(--warning))',
        danger:   'hsl(var(--danger))',
      },
      borderRadius: {
        lg: 'var(--radius)',
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'slide-up': 'slideUp 0.25s ease-out',
        'fade-in': 'fadeIn 0.15s ease-out',
      },
      keyframes: {
        slideUp: {
          '0%': { transform: 'translateY(6px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
