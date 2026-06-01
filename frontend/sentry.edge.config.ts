// @ts-nocheck
// Sentry — Edge Runtime (Next.js middleware). Uses dynamic require so the build
// does not fail when @sentry/nextjs is not installed.
const SENTRY_DSN_EDGE = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN_EDGE) {
  try {
    const Sentry = require("@sentry/nextjs");
    Sentry.init({
      dsn: SENTRY_DSN_EDGE,
      environment: process.env.NODE_ENV,
      tracesSampleRate: 0.1,
    });
  } catch {
    // @sentry/nextjs not installed — error tracking disabled
  }
}
