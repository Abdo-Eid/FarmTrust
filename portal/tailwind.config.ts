import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        teal: {
          50:  '#e8fdf6',
          100: '#d1faf1',
          500: '#1dd1a1',
          600: '#1abc9c',
          700: '#16a085',
          800: '#0f3d37',
          900: '#0d2b27',
          950: '#082420',
        },
        gold:        '#D4A373',
        sand:        '#F3F1EB',
        surface:     '#FFFFFF',
        'dark-alt':  '#2C3A35',
        'table-header': '#E8E6DF',
        status: {
          active:       '#22c55e',
          intermittent: '#f59e0b',
          inactive:     '#ef4444',
          encroachment: '#dc2626',
          processing:   '#6366f1',
          queued:       '#94a3b8',
        },
        confidence: {
          high:   '#22c55e',
          medium: '#f59e0b',
          low:    '#ef4444',
        },
        risk: {
          low:    '#22c55e',
          medium: '#f59e0b',
          high:   '#ef4444',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Consolas', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '2px',
        sm:      '2px',
        md:      '4px',
        lg:      '4px',
        xl:      '4px',
        '2xl':   '4px',
        full:    '9999px',
      },
      boxShadow: {
        panel:    '0 1px 3px 0 rgba(0,0,0,0.08)',
        'panel-md': '0 2px 8px 0 rgba(0,0,0,0.10)',
      },
      backgroundImage: {
        'teal-gradient': 'linear-gradient(90deg, #1abc9c 0%, #16a085 100%)',
        'tech-grid': "url(\"data:image/svg+xml,%3Csvg width='40' height='40' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M 40 0 L 0 0 0 40' fill='none' stroke='rgba(255,255,255,0.06)' stroke-width='1'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
}

export default config
