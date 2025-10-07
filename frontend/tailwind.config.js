/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "media",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        graphite: "#0e0e10",
        teal: {
          400: "#00C6D1",
          500: "#00A7B8"
        },
        accent: "#00C6D1"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"]
      },
      boxShadow: {
        glow: "0 0 12px rgba(0, 198, 209, 0.4)"
      }
    }
  },
  plugins: []
};