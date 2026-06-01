// @ts-nocheck
// Sentry — browser (client) runtime. Uses dynamic require so the build does not
// fail when @sentry/nextjs is not installed. Add NEXT_PUBLIC_SENTRY_DSN to enable.
const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  try {
    const Sentry = require("@sentry/nextjs");
    Sentry.init({
      dsn: SENTRY_DSN,
      environment: process.env.NODE_ENV,
      tracesSampleRate: 0.1,
      replaysOnErrorSampleRate: 1.0,
      replaysSessionSampleRate: 0.05,
      integrations: [
        Sentry.replayIntegration({
          blockAllMedia: false,
          maskAllText: false,
          block: ["[data-sentry-block]"],
          mask: ["[data-sentry-mask]", "textarea", "input[type=text]"],
        }),
      ],
      beforeSend(event) {
        if (event.request?.data) {
          const body = event.request.data;
          for (const key of ["query", "content", "password", "token", "messages"]) {
            if (key in body) body[key] = "[Filtered]";
          }
        }
        return event;
      },
    });
  } catch {
    // @sentry/nextjs not installed — error tracking disabled
  }
}
