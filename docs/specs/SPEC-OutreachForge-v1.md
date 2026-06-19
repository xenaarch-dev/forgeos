# SPEC — OutreachForge Agent (v1)

**Status:** Ready to build — 3 of 4 questions resolved  
**Date:** 2026-06-19 (Day 161)  
**Author:** Padmaja Kotoky  
**Pattern:** ForgeAgent base class (same as migrated agents)

## Problem

ContractForge has zero paying customers through Day 161. The blocker 
is not product or payment — both are verified end to end. The blocker 
is outreach: no first-touch messages have been sent. Lead sourcing 
stays a human task. This agent handles everything after a lead exists.

## Scope

**In scope (v1):**
- Accept a supplied lead list (name, handle/email, fit context)
- Draft a personalized first-touch message per lead using ContractForge 
  positioning and existing voice samples as reference
- Gate every draft on human approval — nothing sends without explicit 
  confirmation, no exceptions
- Track per-lead status in Supabase: drafted → approved → sent → 
  replied → converted
- Draft follow-up after configurable no-reply window, also approval-gated

**Out of scope (v1):**
- Lead sourcing or discovery
- ForgeOS-specific marketing (different problem, separate future spec)
- Auto-sending under any condition, ever

## Architecture

- Class: OutreachForgeAgent(ForgeAgent) in agents/outreach.py
- New Supabase table: outreach_leads
  - id, name, handle, platform, fit_context, status, 
    draft_message, approved_at, sent_at, reply_received, 
    follow_up_draft, created_at, updated_at
- Voice reference: X bio + ContractForge landing copy + 
  existing drafted DMs (Soham, Morgan) as prompt context

## Open Questions

1. **Lead intake** — RESOLVED: Padmaja edits Supabase table or flat 
   file directly. No new UI in v1.

2. **Approval/notification channel — UNRESOLVED. Do not build this 
   piece until decided.** Telegram was the original design but is 
   temporarily blocked in India (June 16–22, 2026, NEET exam-fraud 
   order under Section 69A IT Act). Lifts June 22, message-editing 
   restriction until June 30. Options: wait and reactivate Telegram; 
   WhatsApp Business Cloud API (heavier — Meta verification gate); 
   Claude Cowork mobile pairing (zero build cost but needs desktop 
   awake). Everything else in this spec builds without this piece.

3. **Voice/style source** — RESOLVED: existing materials as reference, 
   not a blank prompt.

4. **Build pattern** — RESOLVED: ForgeAgent from day one.

## What this spec does not decide

Approval channel implementation (Open Question 2). Auto-sending 
under any condition. ForgeOS marketing agent (separate spec).
