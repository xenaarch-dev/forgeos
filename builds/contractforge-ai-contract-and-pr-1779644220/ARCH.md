# ContractForge Architecture

## Stack Justification
- **Frontend**: Next.js 14 (App Router) + Tailwind + Shadcn/ui - Provides a modern, performant, and scalable frontend with a rich UI/UX.
- **Backend**: FastAPI - Offers high performance and easy-to-use asynchronous APIs for handling business logic.
- **Database**: Supabase (Postgres) - A powerful database service that integrates well with the other tools in the stack.
- **Cache**: Upstash Redis - Provides fast read/write access to cache data, improving application performance.
- **Queue**: Upstash Kafka - Enables real-time messaging and processing of asynchronous tasks.
- **Auth**: Supabase Auth - Handles user authentication and authorization securely.
- **Payments**: Lemon Squeezy - A simple and secure payment gateway for recurring billing.
- **Email**: Resend - Reliable email delivery with transactional capabilities.
- **Monitoring**: Sentry + Uptime Robot - Ensures the application is always up and running, with detailed error tracking.
- **CI/CD**: GitHub Actions - Automates testing and deployment processes.
- **Deployment**: Railway (backend) + Vercel (frontend) - Provides a seamless and scalable deployment experience.

## System Diagram