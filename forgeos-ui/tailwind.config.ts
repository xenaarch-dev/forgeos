import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans:    ["var(--font-space)", "system-ui", "sans-serif"],
        display: ["var(--font-space)", "system-ui", "sans-serif"],
        mono:    ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        bg: {
          DEFAULT:  "#07040f",
          surface:  "#0e0820",
          elevated: "#150d2e",
          hover:    "#1c1040",
        },
        border: {
          DEFAULT: "#2a1f4a",
          subtle:  "#1a1235",
          bright:  "#6d28d9",
        },
        text: {
          primary:   "#f5f0ff",
          secondary: "#9d8ec0",
          tertiary:  "#5b4d7a",
        },
        accent: {
          DEFAULT: "#a855f7",
          hover:   "#9333ea",
          dim:     "rgba(168,85,247,0.15)",
          glow:    "rgba(168,85,247,0.3)",
        },
        status: {
          success: "#34d399",
          error:   "#f87171",
          warning: "#fbbf24",
          running: "#a855f7",
          pending: "#3d2f5e",
        },
      },
      animation: {
        "pulse-glow":   "pulseGlow 2s ease-in-out infinite",
        "cursor-blink": "blink 1s step-end infinite",
        "float":        "float 6s ease-in-out infinite",
        "spin-slow":    "spin 8s linear infinite",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "1",   filter: "brightness(1)" },
          "50%":      { opacity: "0.7", filter: "brightness(1.4)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%":      { opacity: "0" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%":      { transform: "translateY(-10px)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
