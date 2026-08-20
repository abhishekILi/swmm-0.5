/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}", "./src/**/*.html", "./src/**/*.ts"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Roboto', 'Helvetica', 'sans-serif'],
      },
      colors: {
        'accent-blue': '#1D96E9',
        'accent-light': '#61C2FF',
        'accent-glow': '#2EB6FA',
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
