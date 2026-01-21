// apps/web/next.config.mjs
import { fileURLToPath } from 'url';
import path, { dirname } from 'path';
// import { withSentryConfig } from '@sentry/nextjs'; // Temporarily disabled
import withBundleAnalyzer from '@next/bundle-analyzer';

// Needed for __dirname in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    // Add any monorepo packages here that need transpiling
    // Example: '@agent-market/sdk', '@agent-market/ui', etc.
  ],

  // There is NO experimental.turbopack option — it has never existed
  // Just delete it completely

  // Extend build timeout for static generation
  staticPageGenerationTimeout: 120,

  // Enable compression (handled by hosting, but good to document)
  compress: true,

  // Optimize images
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    minimumCacheTTL: 60,
    dangerouslyAllowSVG: true,
    contentDispositionType: 'attachment',
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },

  // Bundle splitting and optimization
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['lucide-react', '@tanstack/react-query'],
  },

  // Redirects: HTTP→HTTPS and www/non-www
  async redirects() {
    return [
      // Redirect www to non-www (or vice versa - choose one canonical)
      {
        source: '/:path*',
        has: [
          {
            type: 'host',
            value: 'www.swarmsync.ai',
          },
        ],
        destination: 'https://swarmsync.ai/:path*',
        permanent: true,
      },
    ];
  },

  // Headers for caching and security
  async headers() {
    return [
      {
        source: '/:path*\\.(jpg|jpeg|gif|png|svg|ico|webp|avif)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/:path*\\.(js|css|woff|woff2|ttf|eot)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://js.stripe.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "img-src 'self' data: https:",
              "font-src 'self' https://fonts.gstatic.com",
              "connect-src 'self' https://swarmsync-api.up.railway.app https://vitals.vercel-insights.com https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com",
              "frame-src 'self' https://js.stripe.com",
            ].join('; '),
          },
        ],
      },
    ];
  },

  // Disable source maps for production for security
  productionBrowserSourceMaps: false,

  webpack: (config, { isServer, dev }) => {
    // Split vendor chunks for better caching
    if (!isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            default: false,
            vendors: false,
            // Vendor chunk for node_modules
            vendor: {
              name: 'vendor',
              chunks: 'all',
              test: /node_modules/,
              priority: 20,
            },
            // Separate chunk for common components
            common: {
              name: 'common',
              minChunks: 2,
              chunks: 'all',
              priority: 10,
              reuseExistingChunk: true,
            },
            // Separate chunk for UI components
            ui: {
              name: 'ui',
              test: /[\\/]src[\\/]components[\\/]ui[\\/]/,
              chunks: 'all',
              priority: 15,
            },
          },
        },
      };
    }
    // Properly resolve @ alias to ./src (works with both Webpack & Turbopack)
    config.resolve.alias = config.resolve.alias || {};
    config.resolve.alias['@'] = path.resolve(__dirname, './src');
    config.resolve.alias['@pricing'] = path.resolve(__dirname, '../../lib/pricing');

    return config;
  },
};

// Temporarily disabled Sentry due to missing dependencies
// const sentryNextConfig = withSentryConfig(
//   nextConfig,
//   {
//     // For all available options, see:
//     // https://github.com/getsentry/sentry-webpack-plugin#options

//     // Suppresses source map uploading logs during bundling
//     silent: true,
//     org: "agent-market",
//     project: "web-app",
//   },
//   {
//     // For all available options, see:
//     // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

//     // Upload a larger set of source maps for prettier stack traces (increases build time)
//     widenClientFileUpload: true,

//     // Transpiles SDK to be compatible with IE11 (increases bundle size)
//     transpileClientSDK: true,

//     // Routes browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers (increases server load)
//     tunnelRoute: "/monitoring",

//     // Hides source maps from the browser
//     hideSourceMaps: true,

//     // Automatically tree-shake Sentry logger statements to reduce bundle size
//     disableLogger: true,

//     // Enables automatic instrumentation of Vercel Cron Monitors.
//     // See the following for more information:
//     // https://docs.sentry.io/product/crons/
//     // https://vercel.com/docs/cron-jobs
//     automaticVercelMonitors: true,
//   }
// );

export default withBundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
})(nextConfig);
