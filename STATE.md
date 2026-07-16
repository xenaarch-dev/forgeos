# ForgeOS — Session State

**Date:** 2026-07-16
**Day:** 188
**Day-N rule:** Computed fresh each session from `date +%Y-%m-%d` using `floor((today − 2026-01-10) / 86_400_000) + 1` — NEVER incremented from the previous session's value, regardless of how many sessions occur per calendar day.
**Branch:** main (not master — same repo, xenaarch-dev/forgeos, default branch is main)
**Remote:** https://github.com/xenaarch-dev/forgeos.git
**Session focus:** Day 188 — full ice-blue design-system rollout across `web/`: landing page rebuild, auth screens, app shell (MissionBar/Topbar/Sidebar/MetricsBar), War Room dashboard, and six new `/app/*` pages (Products, Product Detail, Pipeline, Agents, Artifacts, Command, Billing, Settings), built in 11 phases per Fable-5-approved spec — NOT YET PUSHED, see Open Items

---

## Day 188 — Completed (2026-07-16)

### Ice-blue design system rollout — 11 phases, 11 local commits (not yet pushed)

Full front-end rebuild of `web/` per the Fable 5 "ForgeOS-Landing_dc.html / ForgeOS-App_dc.html" spec (the
actual HTML prototypes were never supplied — repo and `web/public/uploads/` were both empty — so this was
built directly from the detailed text spec, confirmed with Padmaja before starting).

**Phase 0 (`e1236dd`):** Replaced `globals.css`'s "Cosmic Garden" tokens (void-black/teal/gold/violet,
Cormorant italic, Space Mono) with the locked ice-blue system (`--bg:#0C0E10`, `--accent:#A4D8FF`, Playfair
Display 700/900 **normal** style only, DM Mono, DM Sans). New `tailwind.config.ts` color/font extensions.
Built the global component set: `MissionBar`, `ForgeCursor`, `BootSequence`, `Scanline`, and three canvas
effects (`SignalBloom`, `FilamentForge`, `GlyphTide`).

**Phase 1 (`2055ed8`):** Replaced `components/v3/LandingV3.tsx` (1176 lines, old palette) with a
`components/landing/` section set (Hero, FactoryFloor, HowItWorks, Proof, Mission, CTA, Footer) wired to
the existing `useMetrics()` hook for live day-number/YC-countdown/MRR/leads. Deleted `components/fx/`
(7 files, confirmed zero imports anywhere — orphaned since the Day-176 S01-S13 portal deletion).

**Phase 2 (`fc94131`):** Reskinned login/signup/onboarding to the two-panel `AuthShell` layout. Kept the
existing magic-link-only Supabase auth (no fabricated password field — that flow doesn't exist in this
codebase). Onboarding became a 3-step wizard over the real `fullName`/`companyName`/`idea` fields the
`completeOnboarding` server action already expects (not the spec's illustrative "AI Contract Generator"
chips, which don't map to any persisted field).

**Phase 3 (`cb7890d`):** Rebuilt `app/app/layout.tsx` as the spec'd flex-col shell — MissionBar (fixed,
26px) → Topbar (48px) → {Sidebar, main} → MetricsBar as a genuine flex child, never `position:fixed`.
Sidebar collapses to 48px icon-only on the pipeline route. MetricsBar moved out of the dashboard page into
the shared shell so it now persists across every `/app/*` screen. This commit also landed the Phase 1
`components/fx`/`components/v3` deletions, which had been removed from disk but never actually staged.

**Phase 4 (`5696f79`):** Redesigned AgentRoster/ActivityStream/ArtifactPreview. `lib/agents/roster.ts` lost
its per-agent accent-hue model in favor of the uniform `#A4D8FF` status-dot system — see Open Items, this
reverses a July-7 decision that was tested against.

**Phases 5-10 (`8cc73bb`, `1a34ea5`, `2a45236`, `3decdfc`, `584c80f`, `af6aa65`):** Six new `/app/*` routes
built from scratch — Products, Product Detail, Pipeline (18-stage GStack visualization with stage-detail
modal), Agents (status-filtered grid), Artifacts (filterable table + slide-in preview panel), Command
(chat-style interface, client-side only — no backend chat route exists), Billing, Settings (6-section
sub-nav incl. Danger Zone confirmation modal).

Verified after every phase: `pnpm build` clean, `npx tsc --noEmit` clean, `pnpm test` (20/20 passing,
3 test files). `pnpm lint` could not run — `web/` has never had an ESLint config despite the `lint` script
in `package.json` (pre-existing gap, not touched this session).

### A deliberate reversal, confirmed with Padmaja mid-session

`lib/agents/roster.ts` carried a comment and a passing unit test (`roster.test.ts`) explicitly asserting
ice-blue (`#A4D8FF`) must **never** appear in the agent roster — a decision from the `2026-07-07`
app-foundations plan, made because the mockup that inspired it used ice-blue only for the landing page,
deliberately kept separate from the App/War Room's Cosmic Garden system. This session's brief called for
ice-blue everywhere, directly contradicting that. Stopped and confirmed before proceeding rather than
silently overwriting tested intent — Padmaja confirmed ice-blue is the correct final decision and the old
comment/test were stale. `roster.test.ts` was rewritten to test the new intended behavior, not deleted.

### Open items (carried forward — don't lose track)

1. **Not pushed to origin yet.** All 11 phases are committed locally on `main` (`e1236dd` through `af6aa65`)
   but deliberately not pushed this session — a full design-system replacement pushed straight to `main`
   would auto-deploy to Vercel production immediately, and Padmaja hadn't seen a rendered screenshot yet
   (see item 3). Push after review.
2. **Sculpture art still missing.** `web/public/art/hero-sculpture.jpg` and `mission-sculpture.jpg` don't
   exist — every `<img>` has an `onError` hide handler so this degrades gracefully to canvas-only
   backgrounds, but the Hero and Mission sections are visually incomplete without them.
3. **Could not get a pixel screenshot this session.** The Browser pane's `computer` screenshot/zoom actions
   timed out consistently (30s) on every attempt, on every route — get_page_text, read_console_messages,
   read_network_requests, and read_page all worked fine and showed a healthy page (correct content, zero
   console errors, all network requests 200 or expected 404s for missing art). Root cause not diagnosed —
   worth a manual look before trusting this blind.
4. **Local dev server can't authenticate.** No `.env.local` exists in `web/` (never has, this session
   didn't create one) — Supabase env vars are unset, so `middleware.ts` throws on any route it protects
   (`/login`, `/app/*`). Landing (`/`, not middleware-gated) verified working; the auth-gated pages were
   verified by `pnpm build`'s static generation + type-check only, not by an actual browser session.
5. **`web/.next` repeatedly hit `EINVAL: readlink` on Windows/OneDrive.** Happened 3 times this session
   mid-build, always fixed by `rm -rf .next` and rebuilding. Looks like OneDrive's sync client racing
   Next.js's build-output symlinks. Consider adding `web/.next` to OneDrive's "always keep on this device"
   exclusion list, or moving the repo off the OneDrive-synced path, if this keeps recurring.
6. **`pnpm lint` has never worked in `web/`** — no ESLint config exists despite the script being present.
   Not this session's regression; flagging since the Verification Checklist in the brief calls for it.
7. **Agents-page filter tabs don't include `PLANNED`,** unlike the spec's `ALL | RUNNING | LIVE | QUEUED |
   PLANNED`. The actual agent-status set in this codebase is `running/live/active/queued` (no `planned`),
   so `ACTIVE` (GBrain) is only reachable via `ALL`. Minor, but worth knowing if a `PLANNED` state gets
   added later.

---

## Day 176 — Completed (2026-07-04, closed past midnight into Day 177)

### Real metrics wired into LandingV3 + dead portal code removed — `576abbc`

A QA sweep found `LandingV3.tsx` was hardcoding MRR/leads/agent_status inline even though a
working `useMetrics()` hook and Supabase-backed `/api/metrics` route already existed from Day
175 — the values happened to match reality (₹0 MRR, queued outreach) but weren't actually reading
from the API. Fixed: `LandingV3` now calls `useMetrics()` and patches 11 DOM nodes (nav badge,
HUD-L/HUD-R panels, Factory Floor rows, dashboard MRR/pipeline stats, dashboard agent cards) from
the live response instead of literal strings. Marquee ticker text left un-wired deliberately (see
Open Items).

Also deleted `web/components/portal/` (S01-S13 + PortalScene, HudPanel, LoopCanvas, Nav,
ProgressRail, AgentChapter) — confirmed fully orphaned since the Day 175 LandingV3 port (zero
imports from outside the directory, verified by grep before deleting). `next build` passed clean
afterward.

### Live verification

Confirmed via direct checks, not assumption:
- Local repo up to date with `origin/main`, no drift.
- Live `forgeos-eight.vercel.app` confirmed serving commit `576abbc`: GitHub's deployment record
  (`gh api .../deployments`) shows sha `576abbc` as the latest Production deployment, and the live
  HTML contains the new wiring-only DOM ids (`badge-cf-status`, `hud-mrr`, `dash-pipeline`) while
  containing zero of the old portal's markers (`PortalScene`, `S01_Hero`, `AgentChapter`) —
  genuinely gone from the live bundle, not just deleted locally.
- Links, mobile breakpoints (375/414/768px via DOM `getBoundingClientRect()`, not the unreliable
  `resize_window`), and metrics cache bypass (`force-dynamic`) all re-confirmed still correct —
  no regressions from Day 175's fixes.
- `day_number` live-ticking confirmed again: `/api/metrics` returned `176` this session, matching
  the Jan 10 2026 baseline computed fresh, not carried over from a stale value.
- Full test suite: **309 passing, 3 skipped, 312 total** — unchanged, re-run (not assumed) both
  before and after today's changes.

### README.md full rewrite

Previous README was last touched Day 162 (14 days stale) and described the retired V1 pipeline
("18 stages, 10 gates, 7 agents") and a "Night Forge" design-token set that no longer exists
anywhere in the codebase (verified via repo-wide grep — the tokens belonged to the now-deleted
S01-S13 portal). Rewritten against actual current code, not memory:
- ModelRouter section now matches `config/models.yaml` / `llm/router.py` exactly: GLM-5.2
  (`openrouter/z-ai/glm-5.2`) Tier-1 default, Sonnet fallback (with the real warning-log message
  quoted), Fable-5 gated behind `FORGEOS_FRONTIER_TIER=true`.
- New "Live homepage" section documenting LandingV3 + `/api/metrics`, single-page routing, and
  the portal deletion.
- "The system" table replaced with the actual 20-stage / 11-gate `HermesOrchestrator` V2 pipeline
  (verified stage-by-stage against `agents/hermes.py`), with the V1 `--legacy` flag noted
  separately.
- Test count corrected to 309/3/312 (was stale at "244/244").
- **Correction to the brief this session started from:** the assumption going in was "Redis+RQ
  superseded by a GitHub Actions scheduler." Verified this is not what the code shows —
  `job_queue.py`/`worker_daemon.py` (Redis+RQ) are unimported dead code, but what actually
  replaced them is the flat-file `daemon/queue.py` + `daemon/drainer.py` running under **Windows
  Task Scheduler**, not GitHub Actions. Similarly, Telegram is not fully superseded by Discord:
  `daemon/drainer.py` still actively polls Telegram for build-idea intake (this is live,
  functioning code) — Day 163's Telegram→Discord swap was specific to the OutreachForge
  lead-approval channel, a separate subsystem. README now describes both mechanisms as they
  actually are, not as briefed.
- Confirmed repo is public (`gh repo view`); secrets-history-clean claim included as stated,
  not independently re-scanned this session (GitHub secret-scanning is disabled on this repo, so
  there's no automated check to run without a full manual history scan).

### Open items (carried forward — don't lose track)

1. **Hero background image still missing** — `web/public/uploads/Screenshot 2026-06-25
   161244.png` 404s live. Blocked on Padmaja supplying the file.
2. **WSL2 vs Windows OneDrive clone never formally consolidated** — caused 3 separate incidents
   this week (Day 161 vs 173-174 drift, the `.content` fix landing in the wrong `models` module,
   and this session's own briefed assumption about Redis+RQ/GitHub Actions turning out not to
   match this clone's code). Needs a decision: always `git pull` in WSL2 before builds, or
   designate one clone as canonical.
3. **Marquee ticker text** — decorative duplicate of the now-wired MRR/status values, not itself
   wired to `/api/metrics`. Deliberately deferred — low priority, cosmetic only.
4. **Roman-forge cursor + data-reactive hero art** — direction chosen (Roman/cosmic hybrid,
   already reflected in LandingV3's current design). Next step is a dedicated Claude Design
   exploration session for the cursor-reactive hero art specifically — not yet run.

### Business context (non-code, relevant to future outreach-agent work)

Padmaja's LinkedIn account was fully restricted/banned today. Appeal filed via LinkedIn's General
Restriction Appeal Form. OutreachForge's LinkedIn-based outreach is blocked indefinitely pending
the appeal outcome. Email-based CA firm outreach (LinkedIn-independent) identified as the interim
channel — 3 candidate Mumbai firms found (Anam CA, N D Savla & Associates, K M GATECHA & CO LLP);
contact details not yet pulled.

**Commits today:** `576abbc`, plus this STATE.md/README.md close-out commit.

---

## Day 175 — Completed (2026-07-03, closed past midnight into Day 176)

### Real-data metrics pipeline — `e9cc0d8`

Replaced every fabricated/hardcoded number on the live portal (old S01-S13 tree) with real or honestly-absent data:
- `web/app/api/metrics/route.ts` — new route. `day_number`/`yc_days_remaining` computed live from Jan 10 2026 / Jul 27 2026 baselines, never hardcoded. `mrr_inr: 0` (verified real, zero paying customers). `leads` queried from Supabase `outreach_leads` via REST (service-role key), `null` if unset — never fabricated. `agent_status.outreach: "queued_awaiting_approval"` (honest, not "running"). `recent_activity: []` since no `agent_logs` table exists yet.
- `web/hooks/useMetrics.ts` — client hook, fetches `/api/metrics`.
- Removed the fabricated `BUILD TIME: 04:07:32` line from both the hero HUD and the S02_Problem "human vs machine" comparison — no real measurement backed that number, so it was deleted rather than replaced with another invented figure.

### v3 landing page shipped live — `055f856`

Replaced the entire S01-S13 Next.js portal with the previously-untracked `web/landing-v3.html` (the approved final design), ported as `web/components/v3/LandingV3.tsx` — a client component using `dangerouslySetInnerHTML` for the ~880-line hand-styled markup (verbatim porting of inline styles to JSX objects was judged too error-prone by hand) plus a real `useEffect` for the interactive JS (Signal Bloom canvas, Glyph Tide, cursor/magnetic-button effects, scramble-text). Fixed three factual issues found during the port: dropped a "276/276 tests" badge with no real source (STATE.md's real number is 309/312), dropped two "zero downtime" claims (no UptimeRobot data confirms this), fixed the hero background image to an absolute `/uploads/` path (**still needs the actual file added at `web/public/uploads/Screenshot 2026-06-25 161244.png` — not done**). `layout.tsx` updated to v3 fonts (Playfair Display, DM Sans, DM Mono, Space Grotesk) and metadata. Old S01-S13 component tree left in place but unused — cleanup deferred, not yet decided.

### `models/__init__.py` — `.content` property restored — `708f634`

Confirmed `import models` resolves to the **package** `models/__init__.py`, not the flat `models.py` (packages win over same-named modules in the same directory — verified via `models.__file__`). This morning's GLM slug fix (`e07e754`) added `.content` to `models.py` only, which isn't the file Python actually imports — so the live-imported class never had the fix. Re-added `@property def content(self): return self.text` to `models/__init__.py`'s `LLMResponse`, committed properly this time (previous session's fix was lost to an accidental `git stash drop`). Verified at the code level (`LLMResponse(text='pong').content == 'pong'`, no `AttributeError`) — could not run a live GLM ping from this Windows/Git Bash session since `GLM_API_KEY` only lives in WSL2's `~/.bashrc`. **Still open: live WSL2 verification of the GLM ping deferred, not done this session.**

### Nav responsive fix + canvas false-alarm correction — `f0fd13f`

Nav's inline `padding:0 56px`/`gap:34px` didn't shrink below ~830px viewport (flex children default to `min-width:auto`), clipping the CTA button — fixed with a `≤900px`/`≤680px` breakpoint using `!important` (required since the base styles are inline). Separately investigated a "dead canvas" concern (dangerouslySetInnerHTML script tags don't execute) and found it didn't apply — the port already used a real `useEffect`, never an injected `<script>`. The apparent dead canvas on first live check was a false negative: the browser automation tab used for testing reports `document.hidden: true` permanently (confirmed even after clicking to establish focus), which correctly gates the canvas's `requestAnimationFrame` loop exactly as it should for a real backgrounded tab. Canvas confirmed rendering correctly in local dev, local production build, and live Vercel once tested from a state where it actually painted.

### Pre-launch smoke test — CLOSED — `0b9af07`

Full click-through QA found: `FOLLOW THE BUILD` was a dead same-page anchor, 3 of 4 footer links were literal `href="#"` placeholders, the metrics API was being edge-cached by Vercel despite `must-revalidate` (`x-vercel-cache: HIT`, age growing 8s→26s across two `no-store` fetches), and — beyond what the QA pass explicitly named — the same fixed-px-column overflow bug (root cause of the earlier nav fix) also broke the Seven Agents grid (all 7 rows) and the Agent Dashboard mockup on narrow viewports, with `overflow-x:hidden` making the pushed-off content (status badges, stats, description text) permanently unreachable — confirmed via direct `getBoundingClientRect()` measurement, not screenshot impression.

Fixed, in commit `0b9af07`:
- **Real links**: `FOLLOW THE BUILD` + footer `GITHUB` → `github.com/xenaarch-dev/forgeos` (repo confirmed public via `gh repo view`; full git history scanned for key/secret/webhook/token patterns — only fake test fixtures found, e.g. `sk-or-v1-test` — clean). Footer `X/TWITTER` → `x.com/xenarch`. Footer `DOCS` → removed entirely, no fake placeholder.
- **Mobile grid overflow**: added `≤900px` single-column/stacked breakpoints (reusing the nav fix's `!important` pattern) to the Seven Agents grid, Agent Dashboard mockup (212px sidebar + 4-stat row + 2-col status grid), Command Interface demo (280px sidebar), Build Logs terminal, How It Works section, and the nav badge pill (only overflowed at 375px once secondary nav links were hidden). Verified zero overflow offenders at 375px, 414px, 768px via direct DOM measurement; confirmed desktop (1280px) layout unchanged.
- **Hero eclipse/headline overlap** (minor, deferred-scope item): light touch — `#forge-halo{opacity:0.45}` at `≤680px` so text stays legible over the art.
- **Metrics caching**: added `export const dynamic = 'force-dynamic'` to `route.ts`. Verified live: two consecutive `no-store` fetches both returned `x-vercel-cache: MISS`, `age: 0` (previously `HIT` with growing age). Bonus proof: `day_number` was observed ticking `175 → 176` live across the session as real midnight passed.

**Residual note (human follow-up):** the mobile grid fix was verified via direct DOM measurement (`getBoundingClientRect()`, zero overflow offenders at 375/414/768px) and via confirming the exact CSS rules are present in the live stylesheet — **not** via a literal live narrow-viewport screenshot. The browser automation tool's `resize_window` does not actually change the rendered viewport in this environment (confirmed twice — requested 375×812, actual `clientWidth` stayed at ~1526px). Padmaja should spot-check the live site on a real phone when convenient; the fix is very likely correct (same method validated the nav fix already shipped and confirmed working) but hasn't had eyes-on-a-real-device confirmation.

**Commits today:** `e9cc0d8`, `055f856`, `708f634`, `f0fd13f`, `0b9af07` — all on `origin/main`.

**Did not move today (carried forward unchanged):** LinkedIn outreach (4 leads still drafted/queued, none sent), CA firm outreach (names still needed from Padmaja before drafting), YC application draft Version B (still not committed).

---

## Day 174 — Completed (2026-07-02)

### ModelRouter v2 — Task 1 CLOSED ✓

**Verification scope:** Two checks only — no new features.

**CHECK 1 — GLM-5.2 live:** ❌ `GLM_API_KEY` is not set in either WSL2 (`~/.bashrc`) or Windows shell. `GLMClient.__init__` raises `LLMError: GLM_API_KEY is not set.` immediately. Key must be obtained at openrouter.ai and added: `export GLM_API_KEY='sk-or-v1-...'`.

**CHECK 2 — Fallback warning logged:** Gap found and fixed.

Original gap: when `GLM_API_KEY` IS set but the actual API call raises (network timeout, quota, wrong model slug), `complete()` was catching the exception silently and falling back to Sonnet with no log output. The "key missing" path already warned via `sys.stderr.write()` in `_is_available()`.

**Fix (`llm/router.py`):** Added `import logging` + `_log = logging.getLogger(__name__)`. In `complete()`, both `except LLMError` and `except Exception` blocks now call `_log.warning("[router] GLM call failed — falling back to Sonnet. Error: %s", e)` when `client_name == "glm52"`.

**New test (`tests/test_model_router.py`):** `TestCompleteGLMCallFailure::test_glm_call_failure_logs_warning_and_falls_back_to_sonnet` — sets `GLM_API_KEY` + `ANTHROPIC_API_KEY`, mocks `GLMClient.complete` to raise `LLMError`, mocks `ClaudeClient.complete` to return a fake response, asserts a `WARNING` log fires mentioning "GLM" and "fall", and asserts Sonnet response is returned.

**Tests:** 312 total — 309 passing, 3 skipped (integration/semgrep, need semgrep binary on PATH).

**Task 1 (ModelRouter v2) status: CLOSED.**

### GLM-5.2 Verify-or-Build — Second Day 174 Session

**Scope:** Verify (or build) GLM-5.2 integration from scratch. Prior session reports questioned.

**Ground truth (from raw commands, before touching anything):**
- `git log --all --oneline | grep -iE "glm|modelrouter"` → `6b248a9 feat: ModelRouter v2` and `62b556d fix(router): log warning` both present
- `ls llm/` → `glm.py` present
- `find . -iname "*glm*"` → `./llm/glm.py` (+ cpython cache)
- `forge_sdk/specs/SPEC_RepairLoop.md` → exists
- `GLM_API_KEY` → blank in both Windows and WSL2 shells

**Critical environment finding:** WSL2 clone (`~/forge/forgeos`) is at Day 161 (`1c9caab`). The Windows OneDrive clone has all Day 173-174 commits. Origin/main is at `ef7b3d8` (Day 173 last commit) — Day 174 commit `62b556d` not yet pushed at session start.

**Action: VERIFIED EXISTING.**
- `llm/glm.py` exists: proof → `./llm/glm.py` found, `git show 6b248a9 --name-only | grep glm.py` shows it was committed Day 173.
- `SPEC_RepairLoop.md` exists: `./forge_sdk/specs/SPEC_RepairLoop.md`.

**Known gap:** `LLMResponse` exposes `.text`, not `.content`. The verification command (`r.content`) would raise `AttributeError` if a key were available and a call succeeded. GLM_API_KEY is unset so the error fires at `__init__` before reaching `.content`. To be fixed when activating the key.

**Live test output (exact):**
```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File ".../llm/glm.py", line 35, in __init__
    raise LLMError(...)
models.LLMError: GLM_API_KEY is not set. Add to ~/.bashrc: export GLM_API_KEY='sk-or-v1-...' Get a key at openrouter.ai (free tier available).
```

**Tests:** `309 passed, 3 skipped in 8.12s` (3 skipped = semgrep integration, need binary on PATH).

**Commits pushed (this session):** `62b556d` + STATE.md cleanup → both to origin/main.

### GLM-5.2 Slug Fix — Third Day 174 Session (2026-07-02)

**Trigger:** Screenshot confirmed GLM auth succeeded (HTTP 200 headers) but OpenRouter returned HTTP 400 body: `"zhipuai/glm-z1-32b is not a valid model ID"`. The only problem was the hardcoded model slug.

**Root cause — wrong slug in three files:**

OpenRouter changed the provider namespace from `zhipuai/` to `z-ai/` sometime before July 2026. The old slug appeared in three places:
1. `llm/glm.py` — `default_model = "zhipuai/glm-z1-32b"` (class attribute)
2. `config.py` — `LLMConfig.glm_model` fallback: `_get("GLM_MODEL", "zhipuai/glm-z1-32b")`. **This was the active override** — `GLMClient.__init__` uses `model or LLM.glm_model or self.default_model`, so the non-empty config.py fallback shadowed the class-level `default_model` when `GLM_MODEL` env var was unset. Fixing only `glm.py` would have had no effect.
3. `config/models.yaml` — all 9 stage entries used `openrouter/zhipuai/glm-z1-32b`

**Correct slug:** `z-ai/glm-5.2` — confirmed via `curl https://openrouter.ai/api/v1/models | python3 -m json.tool | grep z-ai` (not guessed; full model list verified).

**Commits (all on origin/main):**
- `e07e754` — fix(llm): correct GLM-5.2 model slug — `llm/glm.py` `default_model`; also added `@property content` to `models.py` `LLMResponse`
- `08d0542` — fix(llm): correct GLM-5.2 model slug — `config.py` `LLMConfig.glm_model` fallback default
- `49fc8e8` — fix(llm): update `config/models.yaml` GLM slug — all 9 stage entries (`openrouter/zhipuai/glm-z1-32b` → `openrouter/z-ai/glm-5.2`)

**Live proof (WSL2, after pulling `49fc8e8`):**
```
pong
```

**Tests:** 309 passed, 3 skipped in 9.29s (Windows) + 309 passed, 3 skipped in 192.58s (WSL2) — both confirmed after slug fix.

**Task 1 (ModelRouter v2 / GLM-5.2) status: CLOSED — live response confirmed.**

---

### KNOWN ISSUE — WSL2 `models/` Package Shadows Git-Tracked `models.py`

WSL2 clone (`~/forge/forgeos`) contains an **untracked** `models/` directory (a Python package from an earlier refactor) alongside the git-tracked `models.py` flat module. Python always prefers a package directory over a flat module, so `import models` in WSL2 resolves to `models/__init__.py`, not the git-tracked `models.py`.

**Impact:** The `@property content` fix added to `models.py` (commit `e07e754`) does NOT reach WSL2 at runtime. The patch was applied directly to WSL2's `models/__init__.py` as a local fix — this will be lost on a fresh WSL2 clone.

**Correct fix (deferred — do not touch in next session):** Either delete `models/` from WSL2 (so Python uses `models.py`) or merge the two files and commit `models/` to git as the canonical location. Pick one structure; do not do both.

**Two-clone drift (decision deferred):** The Windows OneDrive clone (`C:\Users\PADMAJA\OneDrive\...`) is the Claude Code working directory. The WSL2 clone (`~/forge/forgeos`) is the runtime build environment. They are separate git clones of the same origin. This has caused state drift twice (Day 161 vs Day 173-174; Day 174 `.content` patch). Before the next build, establish a protocol: either always `git pull` in WSL2 before running builds, or designate one clone as canonical and stop using the other for reads.

---

## Day 173 — Completed (2026-07-01)

### ModelRouter v2 — `6b248a9`

GLM-5.2 (zhipuai/glm-z1-32b via OpenRouter) becomes the Tier 1 default for all build stages. qwen2.5-coder:7b is retired as primary — lives on only via `FORGEOS_OFFLINE_MODE=true`. claude-fable-5 added as gated Tier 3 for architecture + security task types when `FORGEOS_FRONTIER_TIER=true`.

**New files**: `llm/glm.py` — GLMClient (OpenAI-compatible, targets OpenRouter), `config/models.yaml` rewritten with `[stages]` + `[frontier]` blocks.

**Modified**: `llm/router.py` — `_select_chain()` three-tier + offline logic; `config.py` — `LLMConfig` fields `glm_api_key`, `glm_model`, `glm_base_url`, `frontier_tier`, `offline_mode`; `agents/gstack.py` — `_gate_call()` `task_type` param, CSOGate passes `task_type="security"`; `AGENTS.md` — ModelRouter v2 rules block (31 sections total).

**Tests**: 22 new in `tests/test_model_router.py` — **298/298 green** at commit.

### Semgrep gate + SPEC_RepairLoop — `a43230c`

**SecurityAgent** (`agents/security.py`) gains `_run_semgrep()`: calls `semgrep --config=auto --json --quiet`, prepends binary dir to PATH (fixes pysemgrep resolution on Windows), returns `[]` on any failure. `_find_semgrep_binary()` checks Scripts/ and `%APPDATA%/Python/Python311/Scripts/` as fallback. Results stored in `context.metadata["security"]["semgrep"]` with `blocking=True` when ERROR-severity findings exist.

**CSOGate** (`agents/gstack.py`) checks `semgrep.blocking` BEFORE calling LLM — hard-fails gate with finding count + check_id details if true.

**SECURITY.md** render now has a dedicated "Semgrep Static Analysis (execution-verified)" section at top with ERROR finding table or clean confirmation.

**`forge_sdk/specs/SPEC_RepairLoop.md`** — full spec: pipeline position (between stage 9-10), 4 test runner detection table, 3-attempt loop pseudocode, exhaustion behavior (REPAIR_SUMMARY.md + halt), failure feedback format (tail 3000 chars), LLM tier per attempt (GLM→GLM→Sonnet), cost analysis (~$0.05 worst case), 5 open questions.

**Tests**: 13 new in `tests/test_semgrep_gate.py` — **311/311 green** at commit. `pyproject.toml` — `integration` marker registered.

---

## Day 163 — Completed (2026-06-23)

### outreach_leads migration — live in production Supabase

Migration `supabase/migrations/20260622000000_outreach_leads.sql` run manually via Supabase SQL editor (project: vcjicrqfnwdegggkrlpd). Confirmed: table, trigger (`outreach_leads_updated_at`), and RLS all created successfully. `OutreachForgeAgent.queue_for_approval()` can now write to production.

### MigrationNotRunError + verify_migration() — `0d4bccd`

- `MigrationNotRunError(Exception)` added to `agents/outreach.py`
- `verify_migration()`: `SELECT id FROM outreach_leads LIMIT 1` — prints "Migration confirmed: outreach_leads exists" on success, raises `MigrationNotRunError` with SQL editor remediation link on any failure
- `test_verify_migration_raises_on_missing_table`: mocks `execute()` raising postgrest-style exception, asserts `MigrationNotRunError` propagates
- **273/273 green** (was 272 — +1 new test)

### Discord approval notifications — `7b08c01`

Telegram permanently removed from plan (Section 69A IT Act, still blocked in India as of Day 163). Discord webhook is the approval channel.

**`agents/outreach.py`**:
- `send_approval_notification(lead_id, lead_name, draft_message) -> bool` — async method: POSTs Discord embed to `DISCORD_WEBHOOK_URL`, returns True on HTTP 204, False on any error or missing env var, never raises
- Embed format: content = "🔔 **OutreachForge — Approval Required**", embed title = lead name, description = draft, footer = "Lead ID: {id} | Reply: /approve {id} or /reject {id}", color = 15105570 (orange)
- `queue_for_approval()` updated: extracts `lead_id` from insert result, calls notification via `asyncio.run()` in a best-effort try/except
- Imports added: `asyncio`, `logging`, `httpx`; `_log = logging.getLogger(__name__)` added at module level

**Discord webhook setup instructions** (run manually when ready):
```bash
# Add to WSL2 ~/.bashrc:
echo 'export DISCORD_WEBHOOK_URL="paste_webhook_url_here"' >> ~/.bashrc
source ~/.bashrc

# Create the webhook:
# 1. Open any Discord server (or create one called "ForgeOS Control")
# 2. Any channel → Edit Channel → Integrations → Webhooks → New Webhook
# 3. Name it "OutreachForge" → Copy Webhook URL → paste into command above
```

**Tests** (3 new):
- `test_send_approval_notification_success`: mocks `httpx.AsyncClient`, asserts True on 204
- `test_send_approval_notification_missing_env`: no `DISCORD_WEBHOOK_URL`, asserts False without raising
- `test_queue_for_approval_triggers_discord_notification`: mocks Supabase + `send_approval_notification` (AsyncMock), asserts called with correct lead_id/name/draft

**276/276 green** (was 273 — +3 new tests)

### YC application draft — `yc/application_draft.md` (not committed)

Two versions written. Version B (ContractForge leads, ForgeOS as engine) flagged as stronger. Xena to review and edit before commit.

---

## Day 162 — Completed (2026-06-22)

### README rewritten — `e5b2cee`

`README.md` fully rewritten. 82 insertions, 232 deletions. Night Forge tone — dark, precise, builder-voice, no startup marketing. No badges.

Content: what shipped (ContractForge), the 18-stage pipeline, 7 named agents, Daemon Mode, stack (Python 3.12 / Render+Vercel), 244 tests, Night Forge design tokens, India-first deliberate choices, ForgeADK snippet, quick start.

`.env.example` exists at root — referenced as prose: "Copy `.env.example` to `.env` and add your keys — minimum: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`."

### OutreachForgeAgent v1 — `436c5d2`

Four files shipped in one commit:

**`agents/outreach.py`** — `OutreachForgeAgent(ForgeAgent)`:
- `name="outreach_forge"`, `phase="outreach"`, `budget_usd=0.05`
- `_execute` raises `NotImplementedError` — not a HermesOrchestrator pipeline stage
- Public API: `draft_message(lead)` → `queue_for_approval(lead, draft)` → `mark_approved(lead_id)` → `mark_sent(lead_id)` + `get_pending_approvals()`
- `draft_message`: validates required fields (`name`, `platform`, `fit_context`), calls `ClaudeClient.complete()` with ContractForge positioning prompt, peer-to-peer voice, max 4 sentences
- All Supabase calls through `_supabase_client()` static method (service role key)
- **HARD RULE** enforced in code comment and docstring: nothing sends automatically, ever

**`agents/__init__.py`** — `OutreachForgeAgent` added to `_LAZY` + `__all__` under "Standalone utilities" comment

**`supabase/migrations/20260622000000_outreach_leads.sql`** — new `supabase/migrations/` directory:
- `outreach_leads` table: `id`, `name`, `handle`, `platform` (check: x/email/linkedin), `fit_context`, `status` (check: drafted/approved/sent), `draft_message`, `approved_at`, `sent_at`, `reply_received`, `follow_up_draft`, `created_at`, `updated_at`
- `updated_at` trigger via `update_updated_at()` function
- RLS enabled, service role only — not exposed to end users

**`tests/test_outreach_agent.py`** — 28 unit tests, 6 classes:
- `TestDraftMessage` (7): missing-field validation, missing API key, return value, handle optional
- `TestQueueForApproval` (5): status=drafted enforced, payload fields, no sent_at/approved_at on insert, correct table, Supabase error handling
- `TestGetPendingApprovals` (4): returns list, filters status=drafted, correct table, None→[] guard
- `TestMarkApproved` (5): status=approved, approved_at set, id filter, sent_at absent, Supabase error handling
- `TestMarkSent` (5): status=sent, sent_at set, id filter, approved_at absent, Supabase error handling
- `TestSupabaseClient` (2): SUPABASE_URL missing, SUPABASE_SERVICE_ROLE_KEY missing
- All Supabase calls mocked via `patch("agents.outreach.OutreachForgeAgent._supabase_client", return_value=mock_client)`
- `TestSupabaseClient` mocks `sys.modules["supabase"]` — the Windows env has a broken `supabase` package install (`create_client` not importable), so the mock bypasses the ImportError to reach the env var check
- **28 / 28 passed** (`0.23s`)

### .mcp.json + .gitignore — `cd81f88`

**`.mcp.json`** (new, not committed — gitignored):
```json
{
  "mcpServers": {
    "magic":           { "command": "npx", "args": ["-y", "@21st-dev/magic@latest"],         "env": { "API_KEY": "PLACEHOLDER_REPLACE_AFTER" } },
    "nano-banana-pro": { "command": "npx", "args": ["@rafarafarafa/nano-banana-pro-mcp"],     "env": { "GEMINI_API_KEY": "PLACEHOLDER_REPLACE_AFTER" } }
  }
}
```
Fill in real keys then restart the Claude Code session — tools will appear. `.mcp.json` is added to `.gitignore` (API keys, not for git).

Note: `SPEC-OutreachForge-v1.md` (`docs/specs/SPEC-OutreachForge-v1.md`) was confirmed present on remote at `569e8ac` — created in WSL2 in Day 161. OutreachForge agent was built matching that spec.

---

## Day 161 — Completed (2026-06-19)

### Group C test run — 33/33 passed (`/tmp/groupc_final.txt`)

Full suite: `PYTHONPATH=. python3 -m pytest -k "integration or FromAgent" -v`  
- 244 collected, 211 deselected, **33 selected — all passed** in 1878.38 s (0:31:18)
- Machine confirmed quiet before run: no user python3 processes, Ollama idle, GPU 18%/480 MiB

| File | Tests |
|------|-------|
| `test_architect_output.py` | 10 |
| `test_eval_agent.py` | 1 |
| `test_legal_agent.py` | 6 |
| `test_pm_agent.py` | 3 |
| `test_scaffold_output.py` | 8 |
| `test_security_output.py` | 5 |
| **Group C total** | **33** |

**Suite total: 244/244 green** (was 243 — +1 from `f6669da` models fix).

### ADR-001 updated — `fa35622`

`docs/adr/ADR-001-daemon-mode.md` — Decision section rewritten from "Recommended approach" to "What was shipped":
- Records flat-file JSON queue design (not queue.txt)
- Records Telegram-in-drainer pattern (not a separate bot process)
- Open Questions table: all 5 resolved
- Pushed to main: `fa35622`

### SPEC-OutreachForge-v1.md created — `569e8ac`

`docs/specs/SPEC-OutreachForge-v1.md` (new directory `docs/specs/`)
- Problem: zero paying customers through Day 161 — blocker is outreach, not product or payment
- Scope: accept supplied leads, draft personalised first-touch, human-approval gate, Supabase tracking, follow-up drafts
- Architecture: `OutreachForgeAgent(ForgeAgent)` in `agents/outreach.py`, new `outreach_leads` Supabase table
- Open Question 2 (approval/notification channel) **UNRESOLVED** — Telegram blocked in India June 16–22 (NEET exam-fraud order, Section 69A IT Act). Lifts June 22; message-editing restriction until June 30. Do not build notification piece until decided.
- Everything else in spec is buildable now.
- Pushed to main: `569e8ac`

### Daemon Mode — live

- `ForgeOS_Daemon_Drain` Task Scheduler job confirmed running every 15 minutes
- Manual drainer run verified: Telegram gracefully skipped (no creds), queue empty, exit 0
- Drainer log at `logs/drainer.log`

---

## Day 159 — Completed (2026-06-17)

### ADR-001 Daemon Mode — IMPLEMENTED (`86cc519`)

**Status:** ADR-001 updated to Accepted.

#### 1 — FORGEOS_AUTO_DEPLOY guard (`agents/deploy.py`)
- Guard at top of `DeployAgent._execute` — checks `os.environ.get("FORGEOS_AUTO_DEPLOY", "0")`
- When NOT set (default): skips GitHub/Render/Vercel/Sentry/UptimeRobot entirely, writes a `DEPLOYMENT.md` "deploy skipped" notice, returns `skipped=[...]` result — pipeline continues normally
- When set to `"1"`: proceeds with full deploy logic unchanged
- One env var = one mechanism = one place to control unattended deploy. No separate gate class.
- TELEGRAM status: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` still absent from `~/.bashrc` — **flagged: pending configuration before Telegram trigger works**.

#### 2 — BuildQueue (`daemon/queue.py`)
- Flat-file FIFO: `builds/queue/pending/<timestamp>_<uuid>.json` → `builds/queue/archive/` on completion
- Job IDs use `%Y%m%dT%H%M%S_%f` (microseconds) so alphabetical sort == chronological order even within the same second
- `enqueue(idea, source)` → `pop_next()` → `archive(job, status, error)` lifecycle
- `builds/` is gitignored — queue is runtime state, never committed

#### 3 — Drainer (`daemon/drainer.py`)
- Single-invocation pattern: check Telegram → drain one job → exit
- `_tg_poll(queue)`: calls `getUpdates` with offset tracking (`daemon/state/telegram_offset.txt`); no-ops silently without `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`; any text message from the configured chat is enqueued as a build idea
- `drain_once(queue)`: pops oldest job, runs `HermesOrchestrator(idea=...).run()`, archives as success or failed+error; returns True/False
- `main()`: polls Telegram, logs queue depth, drains one job, `sys.exit(1)` on build failure so Task Scheduler sees a non-zero exit

#### 4 — Ollama TODO (`llm/ollama.py`)
- Comment at `url = f"{self.api_base.rstrip('/')}/api/chat"` marks this as the `localhost:11434` call site for the future direct Claude API swap
- Task logged as `builds/queue/pending/20260617T000000_ollama-api-swap.json` (runtime, not committed)

#### Windows Task Scheduler — NOT registered (by design)
Padmaja reviews and runs the following command herself:

```
schtasks /create /tn "ForgeOS Drainer" /tr "wsl.exe -d Ubuntu-22.04 -e bash -lc \"cd /home/padmaja/forge/forgeos && PYTHONPATH=. python3 -m daemon.drainer >> /home/padmaja/forge/forgeos/logs/drainer.log 2>&1\"" /sc HOURLY /mo 1 /ru SYSTEM /f
```

Or for on-demand / manual trigger only (no schedule):
```
schtasks /create /tn "ForgeOS Drainer" /tr "wsl.exe -d Ubuntu-22.04 -e bash -lc \"cd /home/padmaja/forge/forgeos && PYTHONPATH=. python3 -m daemon.drainer >> /home/padmaja/forge/forgeos/logs/drainer.log 2>&1\"" /sc ONSTART /ru SYSTEM /f
```

To add an idea to the queue and trigger manually:
```bash
# In WSL2:
cd /home/padmaja/forge/forgeos
PYTHONPATH=. python3 -c "from daemon.queue import BuildQueue; BuildQueue().enqueue('Build a habit tracker SaaS')"
PYTHONPATH=. python3 -m daemon.drainer
```

#### Tests
- `tests/test_deploy_guard.py` — 9 tests: guard-off skips all external calls, DEPLOYMENT.md always written, guard-on proceeds to deploy logic
- `tests/test_queue.py` — 24 tests: enqueue/pop/archive lifecycle, FIFO ordering, edge cases (empty, corrupted file, error truncation)
- `tests/test_drainer.py` — 16 tests: drain_once success/fail/empty, Telegram poll with/without creds, chat_id filter, offset advance, network failure
- **Test suite: 243/243** (was 194 — +49 new)

---

## Day 158 — Completed (2026-06-16)

### Daemon Mode ADR — SHIPPED (`303fbaa`)
- `docs/adr/ADR-001-daemon-mode.md` — decision record, status: Proposed (pending Padmaja review)
- **Environment facts captured** (verified by running commands):
  - `claude --version` = 2.1.146 (Windows binary, NOT in WSL2 PATH)
  - No `--schedule` or `--channels` flag in Claude Code CLI — `/schedule` is a cloud Routine *skill*, not a flag
  - `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` absent from `~/.bashrc` — TelegramNotifier silently no-ops on every build today
- **Options evaluated:** Claude Code Routines (deferred — Ollama is local-only, cloud can't reach localhost:11434), bare crontab in WSL2 (non-starter — WSL2 shuts down when terminal closes), systemd timer in WSL2 (inadvisable on a laptop), Windows Task Scheduler → wsl.exe (recommended near-term), Telegram-triggered builds (correct long-term architecture)
- **Gate analysis:** existing gate=True/False split is sound for unattended runs; **DeployAgent (gate=False) is the only exception** — needs `FORGEOS_AUTO_DEPLOY` env guard before any unattended build can safely proceed (creates real GitHub/Railway/Vercel resources)
- **Failure gaps identified:** Telegram not configured (silent failures), no build timeout (hung Ollama blocks indefinitely), no dead-letter log, no per-run spend cap
- **5 open questions** for Padmaja in the ADR before implementation starts
- No code changes in this task — decision record only

### Repo Hygiene — worktree-dark-manifesto deleted
- Branch tip `ce37aa8` confirmed as direct ancestor of main (`git merge-base --is-ancestor` exit 0) — commit was IN main's linear history, not just superseded
- WaterCursor.tsx byte-identical on both branches; zero unmerged content
- Remote `origin/worktree-dark-manifesto`: deleted ✓
- Local branch `worktree-dark-manifesto`: deleted ✓
- Git worktree registry: clean — only `main` + `act-ii-portal` remain ✓
- Physical dirs (`.claude/worktrees/dark-manifesto`, `.git/worktrees/dark-manifesto`): removed manually via Explorer (Windows permission block on `git worktree remove --force`)
- One discarded loose change in the worktree: `settings.local.json` adding `"Bash(vercel --version)"` — uncommitted, no loss

### LaunchAgent + FalClient — SHIPPED (`c79a20a`)
- `agents/launch.py`: ForgeAgent stage 20, `gate=False`, after DeployAgent
  - Single LLM call → three LAUNCH.md sections: PH listing draft, outreach seed table, launch thread (Xena voice)
  - Reads `context.metadata["pm_output"]["icp"]` for richer prospect seeding
  - Writes to `<workdir>/LAUNCH.md` AND `project/LAUNCH.md` (mirrors DeployAgent pattern)
  - Sets `launch_draft_ready=True` + `launch_needs_review=True` in metadata
  - Soft Telegram notify via `TelegramNotifier` (best-effort, never raises)
  - `capabilities=["LAUNCH.md"]`, `requires=[idea, project_id, spec, frontend_url, backend_url, repo_url]`, `budget_usd=0.0`
- `tools/fal_client.py`: provider-agnostic stub (Pika + Higgsfield via Fal.ai)
  - Methods: `build_a_brand()`, `app_screens()`, `product_sizzle()` — `founder_video` intentionally excluded
  - `is_ready()` returns False without `FAL_API_KEY` — all `generate()` calls raise `NotImplementedError`
  - `FAL_VIDEO_PROVIDER` env var selects provider (default: pika)
  - CLI: `python3 tools/fal_client.py generate --type build_a_brand --prompt '...'`
- `agents/__init__.py`: `LaunchAgent` added to `_LAZY` + `__all__`
- `agents/hermes.py`: launch stage wired after deploy in `_build_pipeline()`
- `tests/test_launch_agent.py`: 23 tests (attrs, render_launch_md, run with mocked LLM, FalClient stub)
- Test suite: **194/194** (was 171 — +23 new)
- **FalClient activation checklist** (when ready):
  1. Sign up at fal.ai → generate API key
  2. `export FAL_API_KEY=...` in WSL2 `~/.bashrc`
  3. Optionally `export FAL_VIDEO_PROVIDER=higgsfield` to switch provider
  4. Replace `raise NotImplementedError` body in `FalClient.generate()` with real fal-client queue submit + poll
  5. Verify model slugs in `_MODEL_MAP` against fal.ai/models

### Pika / Higgsfield — Investigation Complete: NOT STARTED
- `.mcp.json`: does not exist anywhere in repo. MCP config is `.claude/settings.json` — 3 servers: `supabase`, `context7`, `playwright`. No Pika, no Higgsfield entry.
- `agents/pika_launch.py`: does not exist. No `pika*.py`, no `higgsfield*.py` in agents dir.
- `orchestrator.py` / `hermes.py`: zero matches for `pika`, `higgsfield`, `LAUNCH_STAGES`, `build_a_brand`, `app_screens`, `product_sizzle`, `founder_video`.
- Whole-repo grep: zero matches for any of those terms across the entire codebase.
- The "May 2026 planning doc" was conversation-only — never committed to repo. Neither integration has any code, config, or reference. Clean-slate choice for both Pika and Higgsfield — no partially-wired code to navigate around.
- **Gated on**: Padmaja confirming account status / cost for whichever video provider she chooses before implementation begins.

---

## Day 157 — Continued (2026-06-15)

### Migrations
- MissionOrchestrator → ForgeAgent (`9b8a777`) — `capabilities=["VALIDATION_CONTRACT.json"]`, `requires=["idea","tasks"]`, `budget_usd=0.0`
- MissionWorkerLoop → ForgeAgent (`9b8a777`) — `capabilities=[]` (files written by MissionWorker helper, not the loop itself; key nuance for agent-organizer routing), `requires=["tasks"]`, `budget_usd=0.0`; filesystem dep on ScaffoldAgent's `project/` dir is documented in-class comment
- MissionValidator → ForgeAgent (`9b8a777`) — `capabilities=[]`, `requires=["idea"]` (`validation_contract` is a metadata key with self-healing fallback), `budget_usd=0.0`
- Shared import: `from .base import BaseAgent` → `from forge_sdk.agent import ForgeAgent` in `agents/mission.py`

### Test Fixes
- voice_agent asyncio harness — replaced `asyncio.get_event_loop().run_until_complete(coro)` with `asyncio.run(coro)` in `TestSilentMode._run`, `TestFallbackOnError._run`, and `test_speak_never_raises` direct call (`9d61e71`)
- Result: 171/171 — fully green (was 166/171)

### VoiceAgent — ElevenLabs swap + revert (`d00e531` → `e46f947`)
- ElevenLabs was wired in `d00e531`; reverted in `e46f947` — blocked by 402 (free-tier library voices require paid plan)
- Active default: edge-tts (`_tts_and_play` via `edge_tts.Communicate`) — free, no API key, smoke-tested: 29.2 KB MP3 written
- ElevenLabs code **preserved** as `_tts_elevenlabs()` — inactive method, documented with activation instructions
- `ELEVENLABS_API_KEY` remains in `.env.example` for when subscription is upgraded
- **voice_id follow-up (future session)**: when ElevenLabs reactivated, `_DEFAULT_VOICE = "en-GB-RyanNeural"` must be replaced with a valid ElevenLabs library voice ID from paid library

### Doppler — not installed on this machine
- Confirmed: Doppler CLI absent from WSL2 and Windows (no binary, no PATH entry, no shell config reference)
- Actual practice: secrets stored in WSL2 `~/.bashrc` (`export ELEVENLABS_API_KEY=...` at line 153)
- Documented convention (CLAUDE.md references Doppler/Render env) vs actual practice (`~/.bashrc`) — divergence, backlog
- Affects: `ELEVENLABS_API_KEY` (now in `~/.bashrc`), `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` (pending, needed for HermesOrchestrator Telegram notifications)
- Fix path when relevant: either install Doppler CLI in WSL2 (`brew install dopplerhq/cli/doppler` or `.deb`) and migrate secrets, or document `~/.bashrc` as the intentional convention

---

## Day 157 — Completed (2026-06-15)

### Migrations
- GameAgent → ForgeAgent (`a638c80`)
- DeployAgent → ForgeAgent (`e9d891d`)
- GStackGate base → ForgeAgent (`63117e0`) — 10 gate subclasses inherit transitively
- Per-gate `requires` for all 10 GStackGate subclasses (`fe2eaab`) — GStackGate migration fully complete

### Repo Hygiene
- `portal-v3` — deleted local + remote (confirmed fast-forward merged to main, Day 155)
- `act-ii-portal` — pushed to `origin/act-ii-portal` (local backup preserved; 2 commits ahead of dark-manifesto; unmerged, decision pending)
- `web/.next/` — verified already gitignored (line 13) and never tracked; no action needed
- `worktree-dark-manifesto`'s only unmerged content (WaterCursor.tsx) superseded by main's Lighthouse-99-optimized version — flagged for deletion next hygiene pass

### Day-N Formula — RESOLVED (closed permanently)
HUD formula confirmed correct: `Math.floor((Date.now() - new Date('2026-01-10').getTime()) / 86_400_000) + 1`
Source: `web/components/portal/S01_Hero.tsx` (epoch set in `0c46cae`).
Gives DAY 157 on 2026-06-15 — matches STATE.md exactly. No discrepancy. Issue closed.

### LaunchAgent SPEC.md (`89c8fae`)
- Drafted `agents/SPEC_LaunchAgent.md` — spec only, no implementation code
- Stage 20, `gate=False`, after DeployAgent
- Produces `LAUNCH.md` with: Product Hunt listing draft, outreach seed list (5-10 ICP entries), launch announcement thread
- `requires`: idea, project_id, spec, frontend_url, backend_url, repo_url
- `capabilities`: ["LAUNCH.md"]
- `budget_usd = 0.0` — late-pipeline, all spend incurred before stage 20
- Human-in-loop: all content requires Padmaja's approval before any posting/submitting
- Non-goals: does NOT post, does NOT submit to PH (gated on ≥10 paying customers), does NOT call OutreachQueue.add() automatically
- 5 open questions pending Padmaja review (non-blocking, not on critical path)

### Distribution Tooling Audit (`agents/distribution/`)
**ProspectAgent** (`prospect_agent.py`):
- CLI: `--handle / --platform / --context` — one prospect per invocation, no batch/file mode
- Runnable with `ANTHROPIC_API_KEY` set (env or `.env` fallback); no Doppler; no broken imports

**OutreachQueue** (`outreach_queue.py`):
- JSONL schema: `{handle, platform, status, draft_dm, prospect_summary, created_at, sent_at}`
- `status` cycles: `pending → sent | skip`; `replied` exists in stats but must be set manually
- `queue.jsonl` currently empty

### GStackGate + 10 Gates — Classification Complete (read-only)

**GStackGate** (`agents/gstack.py:39`) — abstract base, extends `BaseAgent`. Provides `_execute` runner
(calls `_evaluate`, appends to `context.metadata["gates"]`, raises `RuntimeError` on blocking fail)
and `_gate_call` (wraps `llm_complete`). All 11 classes already in `agents/__init__._LAZY`.

| # | Gate class | hermes.py stage | `gate=` | Phase | Current base | What it does | Classification | Recommendation |
|---|-----------|----------------|---------|-------|--------------|--------------|----------------|----------------|
| – | **GStackGate** | (base class) | – | gate | `BaseAgent` | Abstract runner: `_execute` → `_evaluate`, appends to metadata["gates"], raises on blocking fail | Pipeline base | **Migrate GStackGate → ForgeAgent; all 10 gates inherit** |
| 1 | **OfficeHoursGate** | `office_hours` (stage 1) | `True` | planning | GStackGate→BaseAgent | LLM: evaluates idea viability — market demand, monetization, complexity, risk, moat | Pipeline stage | migrate (transitively via GStackGate base) |
| 2 | **CEOReviewGate** | `ceo_review` (stage 2) | `True` | planning | GStackGate→BaseAgent | LLM: reviews SPEC from investor lens — revenue model, ICP, scope, missing features | Pipeline stage | migrate (transitively) |
| 3 | **EngReviewGate** | `eng_review` (stage 4) | `True` | design | GStackGate→BaseAgent | LLM: reviews ARCH from staff-engineer lens — stack, data model, API design, gaps | Pipeline stage | migrate (transitively) |
| 4 | **DesignShotgunGate** | `design_shotgun` (stage 5) | `False` | design | GStackGate→BaseAgent | LLM: rapid-fire design verdicts (auth, db, frontend, payments, deploy); `blocking=False` — advisory only | Pipeline stage | migrate (transitively) |
| 5 | **ReviewGate** | `review` (stage 10) | `True` | review | GStackGate→BaseAgent | LLM: staff code review — completeness, quality, TODOs, security, production readiness | Pipeline stage | migrate (transitively) |
| 6 | **AdversarialGate** | `adversarial` (stage 11) | `True` | review | GStackGate→BaseAgent | LLM: attacker-mode review — SQLi, auth bypass, IDOR, rate limiting, hardcoded secrets, billing logic | Pipeline stage | migrate (transitively) |
| 7 | **ScoreGate** | `score` (stage 12) | `True` | review | GStackGate→BaseAgent | LLM: final quality score on generated codebase; `min_score=7.0` — highest bar of the review tier | Pipeline stage | migrate (transitively) |
| 8 | **CSOGate** | `cso` (stage 14) | `True` | security | GStackGate→BaseAgent | LLM: CSO-level review — JWT, RLS, input validation, secrets, deps, GDPR; reads SECURITY.md artifact | Pipeline stage | migrate (transitively) |
| 9 | **QAGate** | `qa` (stage 15) | `True` | qa | GStackGate→BaseAgent | LLM: validates against MissionValidator's `validation_contract.assertions`; soft-passes if no contract found | Pipeline stage | migrate (transitively) |
| 10 | **ShipGate** | `ship` (stage 17) | `True` | ship | GStackGate→BaseAgent | No LLM call — aggregates `context.metadata["gates"]`; fails if any prior gate failed or avg < 7.0 | Pipeline stage | migrate (transitively) |

**Key structural finding:** The 10 gate subclasses only override `_evaluate`, not `_execute`. Migrating GStackGate base alone (BaseAgent → ForgeAgent) propagates to all 10 subclasses. Each subclass still needs its own `capabilities`/`requires` added (they vary per gate). `capabilities = []` for all (gates write no files — they write to `context.metadata`).

**Flags for implementation:**
- **ShipGate `requires`**: its only input is `context.metadata["gates"]` — a non-standard field, not a top-level `ProjectContext` attribute. Flag this when writing per-subclass `requires`.
- **RuntimeError propagation** (elevated — see Next Session, Step 1): GStackGate's blocking-fail path raises `RuntimeError`. Verify `ForgeAgent.run()` propagates this unchanged BEFORE migrating. After migration, confirm a test covers gate FAILURE (not just pass) — 167/167 alone doesn't prove this path is covered.

---

## Day 155 — Completed (2026-06-13)

- 5 bugs fixed and committed (`a436601` → `f610cee`)
- portal-v3 merged to main, clean fast-forward
- Vercel production updated at forgeos-eight.vercel.app
- Twitter card metadata added (rich X previews now work)
- CTA placeholder text fixed on dark bg
- 7 orbital arcs now varied (rand fix)
- PRDSim cursor visible
- Agent reference corrected (removed "Nova" persona not shown in portal)

| Bug | File | Commit |
|-----|------|--------|
| PRDSim cursor invisible | S04_Maya.tsx | `a436601` |
| zenVerdict refs "Nova" not in portal | simulations.ts | `ae4c4d9` |
| Missing Twitter card metadata | layout.tsx | `786eb7f` |
| CTA placeholder color unset | S13_CTA.tsx | `dcce4c3` |
| `rand(0.9,0.9)` no-op — all loop arcs same | PortalScene.tsx | `8ef444a` |

---

## Current State

| Item | Value |
|------|-------|
| Live URL | forgeos-eight.vercel.app |
| ContractForge | contractforge.co.in |
| main branch | `49fc8e8` — Day 174 slug fix (pushed 2026-07-02) |
| GLM-5.2 | Live — `z-ai/glm-5.2` via OpenRouter, returned "pong" 2026-07-02 |
| Test suite | 309 passing, 3 skipped (integration/semgrep), 0 failing |
| MRR | ₹0 |

---

## Next Session Starts With

**Day 174 — complete.** Task 1 (ModelRouter v2 / GLM-5.2) fully CLOSED — slug fixed across 3 files, live test returned "pong", all commits on origin/main. 309 passing, 3 skipped. Open items for next session:

1. **models/ package conflict (WSL2)** — KNOWN ISSUE above. Decide: delete `models/` from WSL2 clone, or merge into git and commit it. Do not leave it unresolved indefinitely — the `.content` local patch in WSL2's `models/__init__.py` will be lost on any fresh clone. Recommended: delete `models/` in WSL2 (`rm -rf ~/forge/forgeos/models/`) and confirm `import models` then resolves to `models.py`. Run tests in WSL2 after to verify.
2. **Two-clone protocol** — Decide canonical clone. Simplest option: always `git pull origin main` in WSL2 at the start of any build session. Add this to CLAUDE.md "Key commands" section.
3. **RepairLoop implementation** — `agents/repair.py` + `tests/test_repair_loop.py` + hermes.py stage wiring. Read `forge_sdk/specs/SPEC_RepairLoop.md` Open Question 1 first: does ScaffoldAgent always produce test files? Run a test build and inspect `project/` output before writing code.
4. **YC video script** — deadline July 27, 2026. Draft not started.
5. **YC application draft** — `yc/application_draft.md` Version B exists, not committed. Review + commit before July 15.
6. **Revenue**: pick one outreach channel and send; all 4 LinkedIn messages and 3 CA emails are drafted, none sent.
7. **Discord webhook URL** — still needed for OutreachForge approval notifications.
8. **FalClient activation** — deferred until `FAL_API_KEY` exists.
9. **semgrep in WSL2** — still unverified on PATH in WSL2 build environment. `pip install semgrep --break-system-packages` then `semgrep --version`. Until installed, CSOGate's static analysis pass runs silently empty.

---

## Key Invariants to Preserve

1. `ForgeAgent.run()` is the single point of GBrainLogger lifecycle (`start` → `finish`) — never call `logger.start/finish` from `_execute`
2. `agents/__init__.py` must keep `BaseAgent` as the only eager import — all subclasses in `_LAZY`
3. `gbrain-events.jsonl` is append-only during a build — never truncate or rewrite
4. `budget_usd = 0.0` means unlimited — use it for agents that run mid/late pipeline (no useful cap)
5. All ForgeOS `from` imports are absolute (`from models import X`, not `from .models import X`)
6. PMAgent and EvalAgent are NOT in `agents/__init__._LAZY` — they're imported directly in `hermes.py`
7. GStackGate's blocking-fail path raises `RuntimeError` inside `_execute` — but **ForgeAgent.run() catches it** (via `except Exception`) and returns `AgentResult(status=FAILED)`. Hermes halts the pipeline by checking `result.status == "failed" and is_gate` (hermes.py:332), not by receiving the RuntimeError. Both BaseAgent and ForgeAgent handle this identically. Test coverage: `tests/test_gstack.py::test_blocking_gate_failure_produces_failed_result`.

---

## Test Status

| Suite | Passing | Failing | Notes |
|-------|---------|---------|-------|
| `test_agents.py` | 4/4 | 0 | full pass |
| `test_architect_output.py` | 17/17 | 0 | full pass |
| `test_dataset_collector.py` | 19/19 | 0 | full pass |
| `test_deploy_guard.py` | 9/9 | 0 | new Day 159 — auto-deploy guard |
| `test_drainer.py` | 16/16 | 0 | new Day 159 — daemon drainer |
| `test_eval_agent.py` | 19/19 | 0 | full pass |
| `test_gstack.py` | 4/4 | 0 | gate-failure + pass + subclass + base-attr |
| `test_launch_agent.py` | 23/23 | 0 | LaunchAgent attrs, render, run (mocked LLM), FalClient stub |
| `test_legal_agent.py` | 13/13 | 0 | full pass |
| `test_orchestrator.py` | 4/4 | 0 | full pass |
| `test_model_router.py` | 23/23 | 0 | Day 174 +1: GLM call failure warning test (`TestCompleteGLMCallFailure`) |
| `test_outreach_agent.py` | 32/32 | 0 | Day 163: +MigrationNotRunError, +Discord webhook (3 tests) |
| `test_pm_agent.py` | 27/27 | 0 | full pass |
| `test_queue.py` | 24/24 | 0 | new Day 159 — build queue FIFO lifecycle |
| `test_scaffold_output.py` | 12/12 | 0 | full pass |
| `test_security_output.py` | 15/15 | 0 | full pass |
| `test_semgrep_gate.py` | 13/13 | 0 | new Day 173 — semgrep integration + CSOGate blocking |
| `test_tools.py` | 6/6 | 0 | full pass |
| `test_validator_output.py` | 7/7 | 0 | full pass |
| `test_voice_agent.py` | 18/18 | 0 | asyncio.run() replaces get_event_loop() — Python 3.14 compat (`9d61e71`) |
| `test_worker_output.py` | 6/6 | 0 | full pass |
| **TOTAL** | **312 collected — 309 passing, 3 skipped** | **0** | 3 skipped = integration/semgrep (need semgrep on PATH) |

---

## Agent Migration Status

| Agent | Base class | Migrated |
|-------|-----------|---------|
| ArchitectAgent | ForgeAgent | ✓ (2026-06-07) |
| PMAgent | ForgeAgent | ✓ (2026-06-07) |
| ScaffoldAgent | ForgeAgent | ✓ (2026-06-07) |
| DesignAgent | ForgeAgent | ✓ structure only — `_execute` raises NotImplementedError |
| MediaAgent | ForgeAgent | ✓ structure only — `_execute` raises NotImplementedError |
| CoderAgent | ForgeAgent | ✓ (2026-06-08) |
| SecurityAgent | ForgeAgent | ✓ (2026-06-08) |
| EvalAgent | ForgeAgent | ✓ (2026-06-08) |
| DeployAgent | ForgeAgent | ✓ (2026-06-15) |
| GameAgent | ForgeAgent | ✓ (2026-06-15) |
| LaunchAgent | ForgeAgent | ✓ (2026-06-16) — `c79a20a`, stage 20, FalClient stub wired |
| GStackGate + 10 gates | ForgeAgent | ✓ (2026-06-15) — base `63117e0` + per-gate requires `fe2eaab` |
| MissionOrchestrator | ForgeAgent | ✓ (2026-06-15) |
| MissionWorkerLoop | ForgeAgent | ✓ (2026-06-15) — `capabilities=[]`: files written by MissionWorker helper, not the loop |
| MissionValidator | ForgeAgent | ✓ (2026-06-15) |
| OutreachForgeAgent | ForgeAgent | ✓ (2026-06-22) — `436c5d2`, standalone utility, `_execute` raises NotImplementedError |
| VoiceAgent | *none* (plain class) | N/A — standalone TTS utility, no pipeline base needed |

---

## HANDOFF — Day 174 (2026-07-02)

**GLM-5.2 is live. The slug was wrong. Read the slug fix notes before touching the router.**

### GLM-5.2 is confirmed working — model slug is `z-ai/glm-5.2`

As of commits `e07e754` / `08d0542` / `49fc8e8` (all on origin/main), the correct OpenRouter slug
is `z-ai/glm-5.2` (not `zhipuai/glm-z1-32b` — that namespace no longer exists on OpenRouter as of
July 2026). The slug is patched in three places: `llm/glm.py`, `config.py`, `config/models.yaml`.

**Live verification (WSL2, 2026-07-02):** `GLMClient().complete([{"role":"user","content":"ping"}])` returned `"pong"`.

**Before running any build**, confirm:
```bash
echo $GLM_API_KEY   # must print sk-or-v1-... (OpenRouter key — already in WSL2 ~/.bashrc)
```
If blank, builds fall back to `claude-sonnet-4-6` with a `logging.WARNING` in `llm.router` — not silent, but ~6× more expensive. Key is in WSL2 `~/.bashrc`; confirm it is sourced in any new shell before builds.

### Do NOT change these model strings

The correct values as of 2026-07-02:
- `llm/glm.py` `default_model` → `"z-ai/glm-5.2"`
- `config.py` `LLMConfig.glm_model` fallback → `"z-ai/glm-5.2"`
- All 9 stage entries in `config/models.yaml` → `"openrouter/z-ai/glm-5.2"`

If OpenRouter ever invalidates this slug again, re-run:
```bash
curl -s https://openrouter.ai/api/v1/models | python3 -m json.tool | grep -i "z-ai\|glm"
```
and update all three locations.

### WSL2 `models/` package shadow — DO NOT patch workaround again

WSL2 has an untracked `models/` directory that shadows the git-tracked `models.py`. The `.content`
property added to `models.py` (commit `e07e754`) was patched into WSL2's `models/__init__.py`
manually — this is a local-only fix, not in git. A fresh clone will re-break it.

**First thing next session before running tests in WSL2:**
```bash
# In WSL2:
ls ~/forge/forgeos/models/   # if this prints files, the package exists
rm -rf ~/forge/forgeos/models/
python3 -c "import models; print(models.__file__)"   # should print models.py, not models/__init__.py
PYTHONPATH=. python3 -m pytest tests/ -x -q   # confirm all 309 still pass
```

### Semgrep gate — not yet verified on WSL2 PATH

SecurityAgent + CSOGate are both live. `_run_semgrep()` returns `[]` silently if the binary is
missing — the gate passes without scanning. Verify before the next build:
```bash
semgrep --version   # in WSL2; if missing: pip install semgrep --break-system-packages
```

### Fable-5 frontier tier — still off by default

`FORGEOS_FRONTIER_TIER` defaults to `False`. Set to `true` only per-run for architect/security
gates when quality is more important than cost. Costs ~$10/$50 MTok vs $1.20/$4.10 for GLM.

### Open blockers for next session

| Blocker | Status | Action |
|---------|--------|--------|
| `models/` package shadow in WSL2 | Not fixed | `rm -rf ~/forge/forgeos/models/` then run tests |
| semgrep on WSL2 PATH | Not verified | `pip install semgrep --break-system-packages` |
| RepairLoop not implemented | Not started | Read `forge_sdk/specs/SPEC_RepairLoop.md` Open Q1 first |
| YC video script | Not started | Deadline July 27, 2026 |
| YC application draft | Not committed | `yc/application_draft.md` Version B — review + commit before July 15 |

---

## HANDOFF — Day 175/176 (2026-07-03, closed past midnight into 2026-07-04)

**Pre-launch smoke test CLOSED. Live site (forgeos-eight.vercel.app) is now the v3 landing design, on commit `0b9af07`, with real links, mobile-responsive grids, and non-cached metrics.**

### One residual note — human spot-check needed

The mobile grid fix (Seven Agents grid, Agent Dashboard mockup, Command Interface demo, Build Logs, How It Works, nav) was verified via direct DOM measurement (`getBoundingClientRect()`, confirmed zero overflow offenders at 375px/414px/768px) and by confirming the exact CSS breakpoint rules are present in the live stylesheet — **not** via a literal live narrow-viewport screenshot. The browser automation tool available in this environment cannot actually resize its rendered viewport (`resize_window` reports success but `document.documentElement.clientWidth` stays at ~1526px regardless of the width requested — confirmed twice). The fix is very likely correct — same verification method already validated the nav fix, which is confirmed working — but Padmaja should open the live site on a real phone when convenient to eyeball it directly.

### Still needed, not done this session

- **Hero background image** — `web/public/uploads/Screenshot 2026-06-25 161244.png` needs to be added by Padmaja. The hero currently 404s on this image; the eclipse canvas animation covers most of the visual space regardless, so it degrades gracefully, but the photo layer is missing.
- **`models/__init__.py` `.content` fix — live WSL2 GLM ping not re-verified.** Confirmed at the code level in this session (`LLMResponse(text='pong').content == 'pong'`, no `AttributeError`), but `GLM_API_KEY` isn't available in this Windows/Git Bash session to run a real `GLMClient().complete(...)` call. Next session in WSL2: re-run `PYTHONPATH=. python3 -c "from llm.glm import GLMClient; c=GLMClient(); r=c.complete([{'role':'user','content':'ping'}]); print(r.content[:80])"` and confirm a real response, not an `AttributeError`.
- **Old S01-S13 component tree** — left in place in `web/components/portal/`, no longer rendered from `app/page.tsx`. Cleanup (delete vs. keep as reference) not yet decided — flagging so it doesn't get mistaken for dead-but-load-bearing code.

### Did not move today (unchanged, carry forward)

- **LinkedIn outreach** — 4 leads drafted/queued in `outreach_leads`, none sent (human-in-loop by rule).
- **CA firm outreach emails** — still blocked on Padmaja providing actual firm names/contacts to draft against.
- **YC application draft Version B** — still not committed (`yc/application_draft.md`). Deadline context: July 27, 2026 is now 23 days away.

### Everything else from Day 174's HANDOFF (models/ WSL2 shadow, semgrep on PATH, RepairLoop, YC video script) is unchanged — see the Day 174 HANDOFF above, still open.
