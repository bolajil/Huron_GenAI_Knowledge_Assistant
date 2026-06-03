/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Required for `docker run node server.js` (Dockerfile.production Stage 3)
  output: 'standalone',

  // TypeScript and ESLint are checked in dedicated CI jobs (tsc --noEmit, next lint).
  // Disabling them here prevents duplicate failures during `next build` in Docker.
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },

  // API rewrites to FastAPI backend — BACKEND_URL overridden in containers
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8004';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },

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
