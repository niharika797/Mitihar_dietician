/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        // Verdant brand palette (matches web dashboard)
        brand: {
          50:  "#F0FDF4",
          100: "#DCFCE7",
          200: "#BBF7D0",
          300: "#86EFAC",
          400: "#34B164",
          500: "#23924F",
          600: "#1E7C45",
          700: "#15803D",
        },
        // Semantic
        error:   "#DC2626",
        warning: "#F59E0B",
        info:    "#2563EB",
        // Macro colours
        macro: {
          protein:     "#166534",
          proteinBg:   "#DCFCE7",
          carbs:       "#92400E",
          carbsBg:     "#FEF3C7",
          fat:         "#6B21A8",
          fatBg:       "#F3E8FF",
          fiber:       "#1E40AF",
          fiberBg:     "#DBEAFE",
        },
      },
      fontFamily: {
        sans: ["Inter_400Regular"],
        medium: ["Inter_500Medium"],
        semibold: ["Inter_600SemiBold"],
        bold: ["Inter_700Bold"],
      },
    },
  },
  plugins: [],
};
