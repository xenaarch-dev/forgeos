# ForgeOS Agent Patterns

---

## Model Routing Rules (ModelRouter v2 — 2026-07-01)

These rules are hand-authored, not ForgeBrain-generated.

### Tiered routing (cost-first, not quality-first)

Pre-revenue budget is the binding constraint. The tier structure reflects that:
most pipeline turns are bulk scaffolding where GLM-5.2 is good enough and 6×
cheaper than frontier models. Fable-5 is reserved for the two gates where
errors are most expensive: architecture planning and CSO security review.

| Tier | Model | Env flag | Task types | Cost/MTok |
|------|-------|----------|------------|-----------|
| 1 (default) | GLM-5.2 via OpenRouter | `GLM_API_KEY` (required) | scaffold, worker, review, code | ~$1.20/$4.10 |
| 2 (fallback) | claude-sonnet-4-6 | `ANTHROPIC_API_KEY` | legal, all when GLM unavailable | ~$3/$15 |
| 3 (frontier) | claude-fable-5 | `FORGEOS_FRONTIER_TIER=true` | architecture, security only | ~$10/$50 |
| Offline | qwen2.5-coder:7b (Ollama) | `FORGEOS_OFFLINE_MODE=true` | all (no API key) | free |

### Rules
- **Tier 1 is the default.** If `GLM_API_KEY` is not set, the router logs a
  warning to stderr and falls through to Tier 2. It never silently swallows the
  missing-key case.
- **Tier 3 is opt-in per run**, not global. Use `FORGEOS_FRONTIER_TIER=true`
  on the command line for a specific build; don't set it in `~/.bashrc` until
  there is revenue to absorb it reliably.
- **Offline mode removes Tier 1 and 2.** `FORGEOS_OFFLINE_MODE=true` sends
  everything to Ollama. Capability ceiling is lower; use only when air-gapped
  or for local iteration without API cost.
- **qwen2.5-coder:7b is no longer the default.** It is only used when
  `FORGEOS_OFFLINE_MODE=true` or for `gbrain_index` (index rebuilds only).
- **ArchitectAgent planning calls** use `task_type="architecture"` → Tier 1 by
  default, Tier 3 when frontier flag is set.
- **CSOGate** uses `task_type="security"` → same frontier routing as architect.
- **Legal** always uses claude-sonnet-4-6 (Tier 2) — precision over cost for
  contract and compliance output.

### GLM-5.2 model slug
OpenRouter lists Zhipu models as `zhipuai/glm-z1-32b` or similar. Verify the
exact slug at openrouter.ai/models when you add the key for the first time. Set
`GLM_MODEL=<verified-slug>` in `~/.bashrc` if the default slug is wrong.

---

> Auto-generated ForgeBrain patterns below — edit `forge_brain.py` or the
> Obsidian vault, not that section directly.

## Learned Rules

### Continuous Integration/Continuous Deployment (CI/CD)

Automate the build, test, and deployment process to ensure code quality and reduce human error.

**When**: When developing applications that require frequent updates and need to be deployed in a timely manner.


### Default ForgeOS SaaS stack

Use Next.js for the frontend, FastAPI for the backend, Supabase Postgres for storage, Upstash Redis for cache, Sentry + Uptime Robot for monitoring.

**When**: Greenfield SaaS where you need auth, payments, and email.


### Documentation-First Architecture

Create placeholder architecture and security documentation files early in the project lifecycle, even if initially empty. This establishes the framework for capturing decisions as they are made.

**When**: At project initialization when the technical approach is undefined but you want to establish good documentation practices. Helps ensure architectural decisions are recorded as the project evolves.


### Error Handling

Implement robust error handling to manage exceptions gracefully.

**When**: When developing any application, especially in the backend and frontend.


### FastAPI Backend for Business Logic

Use FastAPI to create a fast, efficient backend that handles business logic and API requests.

**When**: When developing a SaaS application with complex business rules and APIs.


### FastAPI for Backend

Use FastAPI for building high-performance, easy-to-use asynchronous APIs.

**When**: When developing a backend service that requires handling business logic and providing APIs.


### FastAPI Security

Implement security measures in FastAPI using Supabase JWT validation and Row Level Security (RLS).

**When**: When building a secure backend service that requires user authentication and authorization.


### GitHub Actions for CI/CD

Use GitHub Actions to automate testing and deployment processes.

**When**: When building a project that requires continuous integration and delivery.


### Incremental Cost Tracking

Initialize cost tracking at zero and maintain detailed metrics (tokens, USD costs, failures) from project inception, even when no resources are initially consumed.

**When**: For projects where resource consumption and cost management are important concerns, or when building systems that need to track and optimize resource usage over time.


### Lemon Squeezy for Payments

Use Lemon Squeezy as a simple and secure payment gateway that integrates well with the backend.

**When**: When developing a SaaS application with subscription or one-time payments.


### Minimal Viable Stack

Start with an empty technology stack and add components only when specific requirements emerge. Avoid premature technology selection and maintain flexibility for future decisions.

**When**: When building proof-of-concept applications, early-stage projects, or when requirements are not yet fully defined. Particularly useful for small applications where over-engineering is a risk.


### Modular Design

Design your application as a collection of loosely coupled modules or components.

**When**: When building large applications to improve maintainability and scalability.


### Next.js 14 App Router

Use Next.js 14's App Router for a modern, performant, and scalable frontend with a rich UI/UX.

**When**: When building a new web application requiring a modern frontend framework.


### Next.js App Router

Use Next.js 14's App Router for a modern, performant, and scalable frontend with a rich UI/UX.

**When**: When building a React-based web application requiring a robust routing system.


### Next.js App Router with Tailwind and Shadcn/ui

Use Next.js 14's App Router for a modern, performant frontend with Tailwind CSS for styling and Shadcn/ui for UI components.

**When**: When building a new SaaS project requiring a user-friendly interface with advanced UI components.


### RLS by default

Enable RLS on every Supabase table; deny by default; allow only owner.

**When**: Any multi-tenant Supabase application.


### Sentry for Monitoring

Use Sentry to track errors and ensure the application is always up and running.

**When**: When needing detailed error tracking and monitoring for a production application.


### Supabase Auth for Authentication

Use Supabase Auth to handle user authentication and authorization securely.

**When**: When building a web application that requires user authentication and authorization.


### Supabase Auth for User Authentication

Use Supabase Auth to handle user authentication, registration, and session management securely.

**When**: When building a SaaS application with user accounts and authentication requirements.


### Supabase for Database

Use Supabase (Postgres) as the database service, leveraging its powerful features and integration with other tools in the stack.

**When**: When building a web application that requires a robust database solution.


### Supabase for Real-time Database

Use Supabase (Postgres) as a powerful, open-source database that integrates well with the frontend and provides real-time capabilities.

**When**: When building a SaaS application requiring real-time data synchronization across users.


### Supabase with RLS

Use Supabase as the database and apply Row Level Security (RLS) policies to restrict access.

**When**: When building a multi-tenant SaaS application requiring fine-grained data access control.


### Upstash Kafka for Queue

Use Upstash Kafka for real-time messaging and processing of asynchronous tasks.

**When**: When building a system that requires handling asynchronous tasks in real-time.


### Upstash Redis for Cache

Use Upstash Redis for fast read/write access to cache data, improving application performance.

**When**: When needing a caching solution that provides high performance and scalability.


### Upstash Redis for Caching

Use Upstash Redis to provide fast read/write access to cache data.

**When**: When needing a high-performance caching solution for an application.


### Upstash Redis for Caching and Queuing

Use Upstash Redis for fast data caching to improve performance and reduce latency, and as a queue for asynchronous background tasks.

**When**: When needing high-performance caching and background task processing in your SaaS application.


### Webhook signature verification

Verify HMAC signature on every inbound webhook before processing. Use a constant-time comparison.

**When**: Inbound payment, billing, or third-party events.


### Zero-Configuration Startup

Initialize projects with minimal configuration and empty stack definitions, allowing the development process to drive technology choices rather than making assumptions upfront.

**When**: When starting new projects where the optimal technology stack is unknown, or when building applications where simplicity and flexibility are more important than following established patterns.

