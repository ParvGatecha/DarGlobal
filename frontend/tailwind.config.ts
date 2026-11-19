import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        charcoal: {
          950: "#080A0B",
          900: "#0D1012",
          850: "#121619",
          800: "#181D21",
          700: "#242B31",
          600: "#37414A",
          500: "#586570",
        },
        forest: {
          950: "#06130E",
          900: "#0A1D16",
          850: "#0E271E",
          800: "#143328",
          700: "#1B4436",
          600: "#255D4A",
          border: "#1C3E32",
        },
        gold: {
          500: "#C5A059",
          400: "#D4AF37",
          300: "#E5CA8F",
          200: "#F3E1B6",
          100: "#FAF3E3",
          muted: "#8C7343",
          border: "#5C4B29",
        },
      },
      fontFamily: {
        serif: ["Playfair Display", "Georgia", "Cambria", "serif"],
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      boxShadow: {
        gold: "0 4px 20px -2px rgba(197, 160, 89, 0.15)",
        forest: "0 4px 25px -4px rgba(10, 29, 22, 0.4)",
      },
    },
  },
  plugins: [],
};
export default config;
