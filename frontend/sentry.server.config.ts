// @ts-nocheck
// Sentry — Node.js server runtime. Uses dynamic require so the build does not
// fail when @sentry/nextjs is not installed.
const SENTRY_DSN_SERVER = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN_SERVER) {
  try {
    const Sentry = require("@sentry/nextjs");
    Sentry.init({
      dsn: SENTRY_DSN_SERVER,
      environment: process.env.NODE_ENV,
      tracesSampleRate: 0.1,
      beforeSend(event) {
        if (event.request?.headers) {
          delete event.request.headers["authorization"];
          delete event.request.headers["cookie"];
        }
        return event;
      },
    });
  } catch {
    // @sentry/nextjs not installed — error tracking disabled
  }
}
