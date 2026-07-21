/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable typed routes for type-safe navigation
  experimental: {
    typedRoutes: true,
  },

  // Production optimizations
  compress: true,
  reactStrictMode: true,
  poweredByHeader: false,

  // Image optimization for proper caching and formats
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [480, 640, 768, 1024, 1280, 1536],
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30 days
  },

  // Bundle analysis — run with ANALYZE=true to inspect
  // Usage: ANALYZE=true npm run build (install webpack-bundle-analyzer first)
  ...(process.env.ANALYZE === "true"
    ? (() => {
        try {
          const { BundleAnalyzerPlugin } = require("webpack-bundle-analyzer");
          return {
            webpack: (config, { isServer }) => {
              if (!isServer) {
                config.plugins.push(
                  new BundleAnalyzerPlugin({
                    analyzerMode: "static",
                    reportFilename: "bundle-report.html",
                    openAnalyzer: false,
                  })
                );
              }
              return config;
            },
          };
        } catch {
          console.warn(
            "[next.config] ANALYZE=true but webpack-bundle-analyzer is not installed. " +
              "Run: npm install -D webpack-bundle-analyzer"
          );
          return {};
        }
      })()
    : {}),
};

export default nextConfig;
