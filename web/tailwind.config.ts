import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0C0E10',
        accent: '#A4D8FF',
        gunmetal: '#35393C',
        'warm-white': '#ECEBE6',
        error: '#E24C4B',
      },
      fontFamily: {
        display: ['"Playfair Display"', 'serif'],
        mono: ['"DM Mono"', 'monospace'],
        body: ['"DM Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
export default config;
