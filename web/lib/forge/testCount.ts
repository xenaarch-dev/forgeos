// Real Python backend test count (STATE.md Day 174: "309 passed, 3 skipped
// in 8.12s", 312 total). Hardcoded as a stopgap — there's no live-read path
// yet: pytest runs against the repo root in a separate process from this
// Next.js app, and Vercel's build container has no Python/pytest available,
// so computing this at `next build` time the way getDayNumber()/
// getYcDaysRemaining() compute live isn't possible without new plumbing
// (e.g. CI writes the count to a Supabase row or a checked-in report this
// app reads). Needs that same "compute live" treatment once that exists —
// tracked in STATE.md as a known follow-up. Update this constant by hand
// whenever the real suite count changes in the meantime.
export const TEST_COUNT_PASSING = 309
export const TEST_COUNT_TOTAL = 312
