---
name: database-schema-change-with-migration-and-plan-sync
description: Workflow command scaffold for database-schema-change-with-migration-and-plan-sync in forgeos.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /database-schema-change-with-migration-and-plan-sync

Use this workflow when working on **database-schema-change-with-migration-and-plan-sync** in `forgeos`.

## Goal

Updates to the database schema, including adding or modifying tables or policies, accompanied by migration files and synchronized documentation in the implementation plan.

## Common Files

- `supabase/migrations/*.sql`
- `docs/superpowers/plans/*.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or create a migration SQL file in supabase/migrations/
- Update the implementation plan markdown in docs/superpowers/plans/
- Optionally, document live schema or reference-only changes as separate migration files

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.