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
      },
    },
  },
  plugins: [],
};

export default config;
