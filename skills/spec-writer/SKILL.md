---
name: spec-writer
description: Turn an idea or a clean-room analysis into a buildable product spec with user stories, acceptance criteria, data model and a stack recommendation. Use before any code is written.
---

# Spec writer

A spec is good when a stranger could build the product from it without asking
a question.

## Sections
1. **One line.** Who it is for and the outcome they get.
2. **First user.** The narrowest group who needs it most, and why now.
3. **User stories.** "As a <user>, I can <action> so that <outcome>", each with
   2-4 testable acceptance criteria (Given / When / Then).
4. **Scope.** Must-have for v1, explicitly out of scope, later.
5. **Data model.** Entities, fields with types, relationships, which rows each
   user may read and write (this becomes RLS).
6. **Stack.** Recommend one stack and say why for this use case. ForgeOS
   default: Next.js 14 + FastAPI + Supabase, deployed on Vercel + Render.
   Change it only with a reason (real-time, mobile-first, heavy ML, games).
7. **Risks.** Top 3 technical or product risks and how v1 tests them.

## Rules
- Every acceptance criterion must be checkable by a test.
- No feature without a user story behind it.
- Prices in INR first when the user is in India; include GST where relevant.
