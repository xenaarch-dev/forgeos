```markdown
# forgeos Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches the core development patterns, coding conventions, and workflows used in the `forgeos` TypeScript codebase. The repository focuses on modular, test-driven development with clear documentation and migration strategies. It uses conventional commits, a consistent file and import style, and emphasizes pairing features and fixes with tests and documentation updates.

## Coding Conventions

- **File Naming:** Use `camelCase` for file names.
  - Example: `userProfile.ts`, `dataFetcher.test.ts`
- **Import Style:** Use import aliases for clarity and maintainability.
  ```typescript
  import { fetchData as getData } from '@/lib/dataFetcher';
  ```
- **Export Style:** Both named and default exports are used, depending on context.
  ```typescript
  // Named export
  export function calculateSum(a: number, b: number): number {
    return a + b;
  }

  // Default export
  export default function main() {
    // ...
  }
  ```
- **Commit Messages:** Follow [Conventional Commits](https://www.conventionalcommits.org/) with prefixes like `feat`, `fix`, `docs`, `test`.
  - Example: `feat: add user authentication middleware`

## Workflows

### Database Schema Change with Migration and Plan Sync
**Trigger:** When adding or modifying a database table or policy and keeping the implementation plan up-to-date  
**Command:** `/new-table`

1. Edit or create a migration SQL file in `supabase/migrations/`.
   - Example: `supabase/migrations/20240610_add_users_table.sql`
2. Update the implementation plan markdown in `docs/superpowers/plans/`.
   - Example: `docs/superpowers/plans/user-management.md`
3. Optionally, document live schema or reference-only changes as separate migration files.

### Feature Implementation with Test Pairing
**Trigger:** When adding a new feature or fixing a bug in the web app and ensuring it is covered by tests  
**Command:** `/new-feature-with-tests`

1. Implement or update feature logic in `web/lib/` or `web/app/`.
   - Example: `web/lib/userSession.ts`
2. Add or update corresponding test files in `web/lib/**/*.test.ts`.
   - Example: `web/lib/userSession.test.ts`
3. Update `package.json`, lockfile, or config if new test dependencies are introduced.
   - Example: `web/package.json`, `web/pnpm-lock.yaml`

### Feature Implementation with Associated Hook and Component Updates
**Trigger:** When building or enhancing a dashboard or data-driven UI that requires both UI components and data-fetching logic  
**Command:** `/new-dashboard-feature`

1. Implement or update React components in `web/components/`.
   - Example: `web/components/UserTable.tsx`
2. Implement or update custom hooks in `web/hooks/`.
   - Example: `web/hooks/useUserData.ts`
3. Wire up components and hooks in `web/app/` pages.
   - Example: `web/app/dashboard.tsx`

### Bugfix Followed by Plan or Doc Sync
**Trigger:** When fixing a bug and ensuring the documentation or plan is up-to-date with the change  
**Command:** `/bugfix-doc-sync`

1. Fix the bug in the relevant code file(s).
   - Example: `web/lib/auth.ts`
2. Update the relevant implementation plan markdown in `docs/superpowers/plans/`.
   - Example: `docs/superpowers/plans/authentication.md`

## Testing Patterns

- **Framework:** [Vitest](https://vitest.dev/)
- **Test File Pattern:** Use `*.test.ts` for test files, placed alongside or near the code under test.
  - Example: `web/lib/dataFetcher.test.ts`
- **Test Example:**
  ```typescript
  import { describe, it, expect } from 'vitest';
  import { calculateSum } from './calculateSum';

  describe('calculateSum', () => {
    it('adds two numbers', () => {
      expect(calculateSum(2, 3)).toBe(5);
    });
  });
  ```

## Commands

| Command                  | Purpose                                                        |
|--------------------------|----------------------------------------------------------------|
| /new-table               | Start a database schema change with migration and plan sync     |
| /new-feature-with-tests  | Implement a new feature or fix with paired tests               |
| /new-dashboard-feature   | Add or update a dashboard/data-driven UI with hooks/components  |
| /bugfix-doc-sync         | Fix a bug and update the implementation plan or documentation  |
```