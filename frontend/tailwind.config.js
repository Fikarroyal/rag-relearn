/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: { 50: '#FFF4EC', 100: '#FFE6D1', 500: '#F26A1B', 600: '#E0560D', 700: '#B8440A' },
        ink: { DEFAULT: '#23262B', soft: '#4A4F57', mute: '#7B8089' },
        canvas: '#F6F6F4',
        line: '#E5E4E0',
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      borderRadius: { DEFAULT: '8px', lg: '10px' },
    },
  },
  plugins: [],
}
