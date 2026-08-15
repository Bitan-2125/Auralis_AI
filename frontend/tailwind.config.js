/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#F5F7FA",
        panel: "#FFFFFF",
        panel2: "#EEF1F6",
        line: "#D8DEE9",
        accent: "#5B6BFF",
        signal: "#F5A623",
        text: "#1A1D27",
        muted: "#6B7280",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
