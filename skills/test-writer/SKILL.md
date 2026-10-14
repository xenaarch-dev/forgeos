---
name: test-writer
description: Write automated tests from a spec's acceptance criteria - unit tests for logic, API tests for endpoints, and Playwright end-to-end tests for the core user flows. Use when a feature is implemented or when QA finds a gap.
---

# Test writer

Tests prove the acceptance criteria, one test per criterion where possible.

## What to write
- **Unit** (pytest / vitest): pure logic, validators, pricing and tax maths.
- **API** (pytest + FastAPI TestClient): every endpoint's happy path, auth
  failure (401/403), validation failure (422) and not-found (404).
- **End-to-end** (Playwright): the 3 core flows from the spec, including
  sign-up and sign-in. Use role and label selectors, not CSS classes.

## Rules
- A test must fail when the feature is broken. Check by reasoning about what
  the assertion would see if the code returned the wrong thing.
- No sleeps; wait for a condition.
- No real network or payments: stub external services at the boundary.
- Name tests after the behaviour: `test_rejects_expired_link`.
- Report what is covered and the criteria still without a test.
