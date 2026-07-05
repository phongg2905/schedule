import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Background system - warm, soft
        bg: {
          base: "#FBF9F7",
          soft: "#F5F2EF",
          muted: "#EDE9E3",
          warm: "#FFFCF8",
        },
        // Primary - soft coral/peach
        coral: {
          50: "#FFF5F0",
          100: "#FFE8DF",
          200: "#FFD0BD",
          300: "#FFB49A",
          400: "#FF9578",
          500: "#FF7A5C",
          600: "#E86446",
          700: "#CC4E34",
          800: "#A83822",
          900: "#842618",
        },
        // Secondary - light blue
        sky: {
          50: "#F2F7FF",
          100: "#E0EDFF",
          200: "#BCD9FF",
          300: "#8FBDFF",
          400: "#6BA2FF",
          500: "#4A88E6",
          600: "#3670CC",
          700: "#2659AD",
          800: "#1A448A",
          900: "#11316B",
        },
        // Mint accent
        mint: {
          50: "#F0FCF5",
          100: "#DAF7E6",
          200: "#B3EDCB",
          300: "#7DE0A8",
          400: "#4FD089",
          500: "#34B870",
          600: "#269959",
          700: "#1C7A46",
          800: "#145E36",
          900: "#0E4728",
        },
        // Lavender accent
        lavender: {
          50: "#F5F3FF",
          100: "#EDE8FF",
          200: "#D8CEFF",
          300: "#BCA9FF",
          400: "#9D82FF",
          500: "#7E5CE6",
          600: "#6542CC",
          700: "#4E2DAD",
          800: "#3A1D8A",
          900: "#29106B",
        },
        // Neutral palette - warm toned
        neutral: {
          50: "#FCFBFA",
          100: "#F5F2EF",
          200: "#E8E3DC",
          300: "#D4CDC3",
          400: "#B0A79B",
          500: "#8C8377",
          600: "#6B6359",
          700: "#524B43",
          800: "#3A3530",
          900: "#24211E",
        },
        // Semantic colors - desaturated, warm
        accent: "#FF7A5C",
        accentBlue: "#6BA2FF",
        success: "#4FD089",
        warning: "#F0B84A",
        danger: "#E86446",
      },
      borderRadius: {
        soft: "12px",
        card: "24px",
        cardLg: "32px",
        pill: "9999px",
      },
      boxShadow: {
        // Card shadows - physical, layered
        card: "0 2px 8px rgba(36, 33, 30, 0.04), 0 8px 32px rgba(36, 33, 30, 0.06)",
        "card-hover": "0 4px 16px rgba(36, 33, 30, 0.06), 0 16px 48px rgba(36, 33, 30, 0.08)",
        "card-glass": "0 2px 8px rgba(36, 33, 30, 0.04), 0 8px 32px rgba(36, 33, 30, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.8)",
        // Navigation shadow
        nav: "0 4px 24px rgba(36, 33, 30, 0.06), 0 1px 2px rgba(36, 33, 30, 0.04)",
        // Button shadows
        "button-primary": "0 4px 14px rgba(255, 122, 92, 0.25), 0 2px 4px rgba(255, 122, 92, 0.1)",
        "button-primary-hover": "0 8px 24px rgba(255, 122, 92, 0.3), 0 4px 8px rgba(255, 122, 92, 0.15)",
        "button-ghost": "inset 0 1px 0 rgba(255, 255, 255, 0.6)",
        // Lift / hover shadows
        lift: "0 8px 32px rgba(36, 33, 30, 0.08), 0 16px 48px rgba(36, 33, 30, 0.06)",
        "lift-lg": "0 12px 48px rgba(36, 33, 30, 0.1), 0 24px 64px rgba(36, 33, 30, 0.08)",
        // Inner glow
        "inner-glow": "inset 0 1px 0 rgba(255, 255, 255, 0.6), inset 0 -1px 0 rgba(36, 33, 30, 0.04)",
      },
      fontFamily: {
        display: ["'SF Pro Display'", "'Inter'", "'Manrope'", "system-ui", "sans-serif"],
        body: ["'Inter'", "'SF Pro Text'", "'Manrope'", "system-ui", "sans-serif"],
      },
      fontSize: {
        // Heading sizes
        "display-2xl": ["4.5rem", { lineHeight: "1.1", letterSpacing: "-0.03em", fontWeight: "700" }],
        "display-xl": ["3.75rem", { lineHeight: "1.1", letterSpacing: "-0.025em", fontWeight: "700" }],
        "display-lg": ["3rem", { lineHeight: "1.15", letterSpacing: "-0.02em", fontWeight: "600" }],
        "display-md": ["2.25rem", { lineHeight: "1.2", letterSpacing: "-0.015em", fontWeight: "600" }],
        "display-sm": ["1.875rem", { lineHeight: "1.25", letterSpacing: "-0.01em", fontWeight: "600" }],
        "display-xs": ["1.5rem", { lineHeight: "1.3", letterSpacing: "-0.005em", fontWeight: "600" }],
      },
      animation: {
        // Entrance animations
        "fade-in": "fadeIn 0.6s ease-out forwards",
        "fade-in-up": "fadeInUp 0.6s ease-out forwards",
        "fade-in-down": "fadeInDown 0.4s ease-out forwards",
        "slide-up": "slideUp 0.5s ease-out forwards",
        "slide-down": "slideDown 0.3s ease-out forwards",
        "scale-in": "scaleIn 0.3s ease-out forwards",
        // Micro-interactions
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
        "float": "float 6s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
        // Skeleton
        "skeleton-pulse": "skeletonPulse 2s ease-in-out infinite",
        // Status
        "progress-fill": "progressFill 1s ease-out forwards",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeInDown: {
          "0%": { opacity: "0", transform: "translateY(-8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          "0%": { transform: "translateY(100%)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        slideDown: {
          "0%": { transform: "translateY(-10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        scaleIn: {
          "0%": { transform: "scale(0.95)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        skeletonPulse: {
          "0%": { opacity: "0.6" },
          "50%": { opacity: "1" },
          "100%": { opacity: "0.6" },
        },
        progressFill: {
          "0%": { width: "0%" },
        },
      },
      backgroundImage: {
        // Gradient utilities
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "gradient-warm": "linear-gradient(180deg, #FFFCF8 0%, #FBF9F7 50%, #F5F2EF 100%)",
        "gradient-coral": "linear-gradient(135deg, #FF7A5C 0%, #FF9578 100%)",
        "gradient-sky": "linear-gradient(135deg, #6BA2FF 0%, #8FBDFF 100%)",
        "gradient-mint": "linear-gradient(135deg, #4FD089 0%, #7DE0A8 100%)",
        "gradient-lavender": "linear-gradient(135deg, #9D82FF 0%, #BCA9FF 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
