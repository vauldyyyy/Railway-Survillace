/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0B1220',
        'bg-secondary': '#111B2E',
        'bg-card': '#0F1A2E',
        'bg-hover': '#162240',
        'cyber': '#00E0FF',
        'cyber-dim': '#007A8A',
        'danger': '#FF3B3B',
        'danger-dim': '#8B2020',
        'warning': '#FFA500',
        'warning-dim': '#8B5A00',
        'success': '#00FF88',
        'success-dim': '#008844',
        'text-primary': '#E8EDF5',
        'text-secondary': '#8892A5',
        'text-muted': '#4A5568',
        'border-subtle': '#1E2D4A',
        'border-glow': '#00E0FF33',
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-cyan': '0 0 20px rgba(0, 224, 255, 0.15), 0 0 40px rgba(0, 224, 255, 0.05)',
        'glow-red': '0 0 20px rgba(255, 59, 59, 0.2), 0 0 40px rgba(255, 59, 59, 0.1)',
        'glow-orange': '0 0 20px rgba(255, 165, 0, 0.15)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.3)',
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'scan-line': 'scanLine 3s linear infinite',
        'flash-critical': 'flashCritical 1s ease-in-out infinite',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'slide-in-up': 'slideInUp 0.3s ease-out',
        'fade-in': 'fadeIn 0.5s ease-out',
        'shimmer': 'shimmer 2s linear infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.5 },
        },
        scanLine: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        flashCritical: {
          '0%, 100%': { borderColor: 'rgba(255, 59, 59, 0.3)' },
          '50%': { borderColor: 'rgba(255, 59, 59, 0.8)', boxShadow: '0 0 30px rgba(255, 59, 59, 0.3)' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: 0 },
          '100%': { transform: 'translateX(0)', opacity: 1 },
        },
        slideInUp: {
          '0%': { transform: 'translateY(20px)', opacity: 0 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [],
}
