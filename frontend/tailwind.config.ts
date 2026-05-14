import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202A",
        steel: "#455A64",
        signal: "#0F766E",
        risk: "#B42318",
        surface: "#F7F9FB",
        northbound: {
          black100: "#0A0E15",
          black90: "#212631",
          black80: "#373F4E",
          black70: "#4E576A",
          black60: "#667085",
          white100: "#FFFFFF",
          white90: "#F0F1F5",
          white80: "#E0E4EB",
          white70: "#D1D6E0",
          white60: "#BFC6D4",
        },
      },
    },
  },
  plugins: [],
};

export default config;
