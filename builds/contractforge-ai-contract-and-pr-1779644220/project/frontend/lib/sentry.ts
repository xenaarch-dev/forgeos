import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN_FRONTEND;
if (dsn) {
  Sentry.init({ dsn, tracesSampleRate: 0.1, replaysSessionSampleRate: 0 });
}
