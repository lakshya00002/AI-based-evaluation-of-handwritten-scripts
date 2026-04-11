/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
      },
      colors: {
        ink: { 950: "#0b1220", 900: "#111827", 700: "#374151" },
        accent: { DEFAULT: "#2563eb", dim: "#1d4ed8" },
      },
    },
  },
  plugins: [],
};
