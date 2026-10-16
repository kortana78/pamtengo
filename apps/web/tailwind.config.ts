import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 50: "#eef7f2", 600: "#0e7c4a", 700: "#0b633c" },
      },
    },
  },
  plugins: [],
};

export default config;
