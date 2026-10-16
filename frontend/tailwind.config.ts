import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        woka: {
          violet: "#7C3AED",
          "violet-light": "#8B5CF6",
          "violet-dark": "#6D28D9",
          coral: "#F43F5E",
          "coral-light": "#FB7185",
          "coral-dark": "#E11D48",
          bg: "#F8FAFC",
          card: "#FFFFFF",
          border: "#E2E8F0"
        }
      },
      backgroundImage: {
        "gradient-woka": "linear-gradient(135deg, #7C3AED 0%, #F43F5E 100%)",
        "gradient-woka-hover": "linear-gradient(135deg, #6D28D9 0%, #E11D48 100%)",
        "gradient-subtle": "linear-gradient(135deg, rgba(124, 58, 237, 0.05) 0%, rgba(244, 63, 94, 0.05) 100%)"
      },
      boxShadow: {
        "woka-glow": "0 8px 24px -4px rgba(124, 58, 237, 0.20)",
        "woka-card": "0 1px 3px 0 rgb(15 23 42 / 0.05), 0 1px 2px -1px rgb(15 23 42 / 0.05)",
        "woka-hover": "0 10px 25px -5px rgb(15 23 42 / 0.08), 0 8px 10px -6px rgb(15 23 42 / 0.04)"
      }
    },
  },
  plugins: [],
};

export default config;
