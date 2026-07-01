/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4fb",
          100: "#d7e5f5",
          200: "#aecbeb",
          300: "#7fabdc",
          400: "#4c85c9",
          500: "#2c65ac",
          600: "#1f4d8a",
          700: "#193d6d",
          800: "#122c50",
          900: "#0b1c33",
        },
        amber: {
          400: "#fbbf24",
          500: "#f59e0b",
          600: "#d97706",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 10px 30px -12px rgba(11, 28, 51, 0.25)",
      },
    },
  },
  plugins: [],
};
