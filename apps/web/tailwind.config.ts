import tailwindcssAnimate from 'tailwindcss-animate';
import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        text: 'hsl(var(--text))',
        'text-2': 'hsl(var(--text2))',
        muted: 'hsl(var(--muted))',
        disabled: 'hsl(var(--disabled))',
        surface: 'hsl(var(--surface))',
        'surface-2': 'hsl(var(--surface2))',
        accent: '#7C5CFF',
        'accent-strong': '#9D85FF',
        'accent-soft': '#B4BEFF',
        obsidian: '#03050A',
        'obsidian-deep': '#010103',
        'primary-gold': '#D4AF37',
        'primary-gold-strong': '#FFD700',
        'secondary-bronze': '#CD7F32',
        'secondary-bronze-dark': '#B87333',
        'metallic-silver': '#C0C0C0',
        'metallic-slate': '#94A3B8',
        'accent-ice': '#1F2A37',
        'glow-blue': 'rgba(124, 92, 255, 0.4)',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 4px)',
        sm: 'calc(var(--radius) - 8px)',
      },
      boxShadow: {
        'obsidian-panel': '0 30px 90px rgba(0, 0, 0, 0.8)',
        'metallic-glow': '0 12px 35px rgba(212, 175, 55, 0.4)',
        'inner-metallic': 'inset 0 1px 0 rgba(255,255,255,0.35)',
      },
      fontFamily: {
        display: ['var(--font-display)', 'Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        body: ['var(--font-body)', 'Inter', 'Space Grotesk', 'system-ui', 'sans-serif'],
        headline: ['var(--font-display)', 'Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      },
      animation: {
        'glitch': 'glitch 4s steps(10) infinite',
      },
      keyframes: {
        glitch: {
          '0%, 20%, 40%, 60%, 80%, 100%': { transform: 'translate(0)' },
          '10%': { transform: 'translate(-2px, -2px)' },
          '30%': { transform: 'translate(2px, 2px)' },
          '50%': { transform: 'translate(-1px, 1px)' },
          '70%': { transform: 'translate(1px, -1px)' },
          '90%': { transform: 'translate(-1px, -1px)' },
        },
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
