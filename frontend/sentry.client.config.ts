// Sentry — browser (client) runtime
// This file is auto-loaded by @sentry/nextjs for every page rendered in the browser.
import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NODE_ENV,

    // Capture 10% of page-load traces for performance monitoring.
    // Raise to 1.0 temporarily when diagnosing latency issues.
    tracesSampleRate: 0.1,

    // Show the Sentry feedback dialog when a crash occurs.
    // Remove if you do not want users prompted to describe what happened.
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: 0.05,

    integrations: [
      Sentry.replayIntegration({
        // Block query text fields and conversation content from replay recordings.
        blockAllMedia: false,
        maskAllText: false,
        block: ["[data-sentry-block]"],
        mask: ["[data-sentry-mask]", "textarea", "input[type=text]"],
      }),
    ],

    // Strip sensitive request data before it reaches Sentry servers.
    beforeSend(event) {
      if (event.request?.data) {
        const body = event.request.data as Record<string, unknown>;
        for (const key of ["query", "content", "password", "token", "messages"]) {
          if (key in body) body[key] = "[Filtered]";
        }
      }
      return event;
    },
  });
}
