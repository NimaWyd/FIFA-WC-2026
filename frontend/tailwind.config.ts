import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#090b14",
          800: "#0e1020",
          700: "#151829",
          600: "#1e2340",
        },
        pitch: {
          500: "#1a7a3c",
          400: "#22a052",
          300: "#2ec665",
        },
        gold: {
          500: "#f5c842",
          400: "#e8c84a",
          300: "#fde68a",
          dim: "#c9a227",
        },
        fifa: {
          blue: "#1a3fff",
          "blue-dark": "#0d1d8a",
          "blue-light": "#5b8fff",
        },
      },
      animation: {
        float: "float 4s ease-in-out infinite",
        "fade-in": "fade-in 0.6s ease-out both",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-18px)" },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
