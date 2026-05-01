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
          900: "#0a0e1a",
          800: "#0d1428",
          700: "#111d3c",
          600: "#162550",
        },
        pitch: {
          500: "#1a7a3c",
          400: "#22a052",
          300: "#2ec665",
        },
        gold: {
          500: "#d4af37",
          400: "#e8c84a",
          300: "#f5e06e",
        },
      },
    },
  },
  plugins: [],
};
export default config;
