# ForgeOS Project Context

## What It Is
Fully autonomous, multi-agent product factory. One English sentence in → built, tested, secured, deployed software product out.

## Status (2026-05-15)
- Pipeline: architect → scaffold → coder → security → deploy (all 5 agents working)
- Code generation: ~557 seconds per build, real code (not stubs)
- LLM: qwen2.5-coder:7b (Ollama, local, RTX 4050) → haiku-4-5 fallback
- UI: forgeos-ui built (Next.js 14 + R3F + shadcn/ui + Framer Motion)
- API: api.py (FastAPI, 329 lines) — NOT YET STARTED in this session
- GitHub: https://github.com/padmajakotoky73-hash/forgeos

## Critical Blockers This Session
1. .env is EMPTY — no API keys → deploy skips everything
2. localhost:3000 never started
3. No live URL ever produced
4. OneDrive ↔ WSL2 sync not automated

## Path Discrepancy (IMPORTANT)
- Claude Desktop writes to OneDrive: `/mnt/c/Users/PADMAJA/OneDrive/Documents/Claude/Projects/Claude + Obsidian as second Brain/forgeos/`
- ForgeOS runs from WSL2: `~/forge/forgeos/`
- Sync: `cp -r <OneDrive>/. ~/forge/forgeos/` at session start
- These drift every session and have caused bugs (e.g., api.py existed on OneDrive but not WSL2)

## Milestone
First live Railway URL + Vercel URL = session goal achieved.

## Revenue Targets
- $10K MRR
- YC application
- Build in public as xenarch

## Rules (Never Break)
- Payments: Lemon Squeezy (not Stripe) — India VAT compliance
- Prod secrets: Doppler (not .env)
- Deploy: Railway (backend) + Vercel (frontend)
- AI: qwen2.5-coder:7b first, haiku-4-5 fallback only
- Never recommend Aider
