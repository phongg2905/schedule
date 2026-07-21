import { Inter, Manrope } from "next/font/google";

/**
 * Inter variable font – primary body typeface.
 * - Variable weight: 100–900
 * - Latin + Vietnamese subsets for full locale support
 * - display=swap for a non-blocking FOUT strategy
 * - Preloaded via next/font automatic `<link rel="preload">`
 */
export const inter = Inter({
  subsets: ["latin", "vietnamese"],
  variable: "--font-inter",
  display: "swap",
  fallback: ["system-ui", "-apple-system", "Segoe UI", "sans-serif"],
  preload: true,
  adjustFontFallback: true,
});

/**
 * Manrope variable font – secondary / display typeface.
 * - Variable weight: 200–800
 * - Latin subset (no Vietnamese glyphs in Manrope)
 * - Lighter than Inter, great for headings
 */
export const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
  preload: true,
  adjustFontFallback: false,
});

/**
 * Combined font className to apply on `<body>`.
 */
export const fontClassNames = `${inter.variable} ${manrope.variable}`;
