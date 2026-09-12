import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#12161c",
        surface: "#0b0e13",
        border: "#232a35",
        accent: "#3fb6a8",
        warn: "#e0a13a",
        danger: "#d9534f",
        crit: "#b91c1c",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
