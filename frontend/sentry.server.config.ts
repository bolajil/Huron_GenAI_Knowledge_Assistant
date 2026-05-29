// Sentry — Node.js server runtime (Next.js API routes, SSR pages)
import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NODE_ENV,
    tracesSampleRate: 0.1,

    beforeSend(event) {
      if (event.request?.headers) {
        delete (event.request.headers as Record<string, unknown>)["authorization"];
        delete (event.request.headers as Record<string, unknown>)["cookie"];
      }
      return event;
    },
  });
}
