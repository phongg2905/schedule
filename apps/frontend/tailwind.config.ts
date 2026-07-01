import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f7f7f2",
          100: "#ececd9",
          200: "#dad8bb",
          300: "#c1bc93",
          400: "#a39a68",
          500: "#7f7446",
          600: "#645b38",
          700: "#4b442b",
          800: "#312d1d",
          900: "#1d1b12",
        },
      },
      boxShadow: {
        soft: "0 18px 60px rgba(15, 23, 42, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
