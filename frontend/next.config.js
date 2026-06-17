/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Required for `docker run node server.js` (Dockerfile.production Stage 3)
  output: 'standalone',

  // API proxying is handled by src/app/api/v1/[...path]/route.ts at request time.
  // That route reads BACKEND_URL from process.env on every request, so no build
  // arg or rewrite baking is needed — the correct backend URL is always used.

  images: {
    domains: ['localhost', 'api.huronconsultinggroup.com'],
  },
};

// Wrap with Sentry only when the package is installed and a DSN is configured.
// The app boots normally without it — no package = no wrapping.
let exportedConfig = nextConfig;
try {
  const { withSentryConfig } = require('@sentry/nextjs');
  if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
    exportedConfig = withSentryConfig(nextConfig, {
      // Sentry organisation and project (from .env.local)
      org:     process.env.SENTRY_ORG,
      project: process.env.SENTRY_PROJECT,

      // Upload source maps so Sentry shows original TypeScript line numbers.
      // Requires SENTRY_AUTH_TOKEN in .env.local.
      silent: true,
      widenClientFileUpload: true,

      // Hide Sentry internal frames in stack traces.
      hideSourceMaps: true,

      // Tree-shake Sentry logger statements from production bundles.
      disableLogger: true,
    });
  }
} catch {
  // @sentry/nextjs not installed yet — run: npm install @sentry/nextjs
}

module.exports = exportedConfig;
