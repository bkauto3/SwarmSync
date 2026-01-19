import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: "#000000",
        ghost: "#F8FAFC",
        chrome: "#94A3B8",
      },
    },
  },
  plugins: [],
};

export default config;
