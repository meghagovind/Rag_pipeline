import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Outfit", "system-ui", "sans-serif"],
      },
      colors: {
        surface: {
          DEFAULT: "#0a0a0f",
          50: "#12121a",
          100: "#1a1a26",
          200: "#22222f",
          300: "#2a2a38",
        },
        accent: {
          DEFAULT: "#6c63ff",
          light: "#8b83ff",
          dark: "#4d45d4",
          glow: "rgba(108, 99, 255, 0.15)",
        },
        success: "#22c55e",
        warning: "#f59e0b",
        danger: "#ef4444",
      },
      backdropBlur: {
        xs: "2px",
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out",
        "slide-up": "slideUp 0.5s ease-out",
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(108, 99, 255, 0.2)" },
          "50%": { boxShadow: "0 0 40px rgba(108, 99, 255, 0.4)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
