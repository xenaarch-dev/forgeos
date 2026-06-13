/**
 * ALL simulated agent output lives here — ContractForge-authentic,
 * pulled from the real shipped product. No lorem, no placeholders.
 *
 * NOTE: "branch: master @ a3f29e1" in Kira's log is verbatim history
 * from the actual ContractForge deploy — do not "correct" it.
 */

/* ---------------------------------------------------------------- */
/* S04 — Maya / PMAgent: PRD typing itself field by field            */
/* ---------------------------------------------------------------- */
export type PRDField = { label: string; value: string }

export const mayaPRD: PRDField[] = [
  { label: 'PRODUCT', value: 'ContractForge' },
  {
    label: 'PROBLEM',
    value:
      'Indian freelancers lose 4+ hrs/week to contracts.\nNo GST support. No ₹ pricing. No enforceable clauses.',
  },
  {
    label: 'USER',
    value:
      'Freelancer, 22–35, ₹50K–5L per project,\nburned by non-payment at least once.',
  },
  {
    label: 'SUCCESS METRIC',
    value: 'Contract generated + exported in under 60 seconds.',
  },
  { label: 'PRICING', value: '₹2,499/month · ₹1,499 per contract' },
  {
    label: 'GATE',
    value: '5 real user conversations before scaffold. PASSED ✓',
  },
]

/* ---------------------------------------------------------------- */
/* S05 — Aria / ArchitectAgent: architecture diagram                 */
/* ---------------------------------------------------------------- */
export const ariaStack = {
  column: ['Next.js 14', 'FastAPI · Python 3.12', 'Supabase (Postgres + RLS)'],
  rails: ['Lemon Squeezy → webhooks', 'Resend → email', 'Doppler → secrets'],
  annotation: 'deploy: Vercel + Render',
}

/* ---------------------------------------------------------------- */
/* Terminal lines — Rex (scaffold) and Kira (deploy)                 */
/* ---------------------------------------------------------------- */
export type TermLine = {
  text: string
  delayMs: number
  tone: 'cmd' | 'ok' | 'info'
  link?: { text: string; href: string }
}

export const rexScaffold: TermLine[] = [
  {
    text: '$ forgeos build "AI contract generator for Indian freelancers"',
    delayMs: 220,
    tone: 'cmd',
  },
  { text: '  ✓ creating app/(marketing) app/(app) app/api', delayMs: 380, tone: 'ok' },
  {
    text: '  ✓ installing tailwindcss framer-motion @supabase/ssr',
    delayMs: 260,
    tone: 'ok',
  },
  { text: '  ✓ configuring supabase client + RLS policies', delayMs: 320, tone: 'ok' },
  {
    text: '  ✓ wiring lemonsqueezy webhook route /api/ls/webhook',
    delayMs: 240,
    tone: 'ok',
  },
  {
    text: '  ✓ pdf engine: reportlab + DejaVuSans (₹ renders correctly)',
    delayMs: 400,
    tone: 'ok',
  },
  {
    text: '  ✓ scaffold complete — 47 files, 0 placeholders',
    delayMs: 360,
    tone: 'ok',
  },
]

export const kiraDeploy: TermLine[] = [
  { text: '$ kira deploy --prod', delayMs: 400, tone: 'cmd' },
  { text: '  branch: master @ a3f29e1', delayMs: 520, tone: 'info' },
  { text: '  build: next build ✓ 38.2s', delayMs: 700, tone: 'info' },
  { text: '  edge: vercel — bom1 (Mumbai) primary', delayMs: 560, tone: 'info' },
  { text: '  api: render — healthz 200 ✓', delayMs: 640, tone: 'info' },
  { text: '  ssl: active · uptime-robot: armed', delayMs: 520, tone: 'info' },
  {
    text: '  ✓ live → contractforge.co.in   47s total',
    delayMs: 760,
    tone: 'ok',
    link: { text: 'contractforge.co.in', href: 'https://contractforge.co.in' },
  },
]

/* ---------------------------------------------------------------- */
/* S07 — Zen / WorkerLoopAgent: the real generation endpoint         */
/* Tokenised for syntax highlighting: k keyword · s string · n num   */
/* · d decorator · f function · p plain · m dim                      */
/* ---------------------------------------------------------------- */
export type CodeTok = { t: string; c: 'k' | 's' | 'n' | 'd' | 'f' | 'p' | 'm' }
export type CodeLine = CodeTok[]

export const zenCode: CodeLine[] = [
  [
    { t: '@router.post', c: 'd' },
    { t: '(', c: 'm' },
    { t: '"/contracts/generate"', c: 's' },
    { t: ')', c: 'm' },
  ],
  [
    { t: 'async def ', c: 'k' },
    { t: 'generate', c: 'f' },
    { t: '(req: ContractRequest, user=Depends(auth)):', c: 'p' },
  ],
  [
    { t: '    clauses = forge_knowledge.', c: 'p' },
    { t: 'clauses', c: 'f' },
    { t: '(', c: 'm' },
  ],
  [
    { t: '        jurisdiction=', c: 'p' },
    { t: '"Mumbai"', c: 's' },
    { t: ',', c: 'm' },
  ],
  [
    { t: '        act=', c: 'p' },
    { t: '"Indian Contract Act, 1872"', c: 's' },
    { t: ',', c: 'm' },
  ],
  [
    { t: '        gst_rate=', c: 'p' },
    { t: '0.18', c: 'n' },
    { t: ',', c: 'm' },
  ],
  [
    { t: '        late_fee_pct=', c: 'p' },
    { t: '18', c: 'n' },
    { t: ',', c: 'm' },
  ],
  [{ t: '    )', c: 'm' }],
  [
    { t: '    draft = ', c: 'p' },
    { t: 'await', c: 'k' },
    { t: ' model.', c: 'p' },
    { t: 'run', c: 'f' },
    { t: '(spec=req, clauses=clauses)', c: 'p' },
  ],
  [
    { t: '    ', c: 'p' },
    { t: 'return', c: 'k' },
    { t: ' ContractResponse(id=save(draft, user.id))', c: 'p' },
  ],
]

export const zenVerdict = {
  status: 'tests: 32/32 passed ✓',
  credit: '// EvalAgent — all 32 scenarios passed',
}

/* ---------------------------------------------------------------- */
/* S08 — Marcus / SecurityAgent: threat matrix                       */
/* ---------------------------------------------------------------- */
export type ThreatRow = { label: string; holdMs: number }

export const marcusMatrix: ThreatRow[] = [
  { label: 'HMAC signature on LS webhooks ..........', holdMs: 420 },
  { label: 'RLS: auth.uid() = user_id ..............', holdMs: 380 },
  { label: '422 on malformed webhook payloads ......', holdMs: 460 },
  { label: 'secrets via Doppler — zero .env in git .', holdMs: 400 },
  // security is a process, not a checkbox — this one scans visibly longer
  { label: 'OWASP A01 broken access control ........', holdMs: 1700 },
  { label: 'rate limiting on /generate .............', holdMs: 440 },
]

/* ---------------------------------------------------------------- */
/* S09 — Lexi / LegalAgent: clauses on paper                         */
/* ---------------------------------------------------------------- */
export const lexiClauses: string[] = [
  '§ Governing Law: Indian Contract Act, 1872',
  '§ Jurisdiction: Courts of Mumbai, Maharashtra',
  '§ Arbitration: seated in Mumbai, per A&C Act 2015',
  '§ GST: 18% as applicable under Indian law',
  '§ Late Payment: interest at 18% per annum',
  '§ Data: compliant with DPDP Act, 2023',
]

export const lexiAnnotation = 'global tools cannot write this.'

/* ---------------------------------------------------------------- */
/* S10 — Kira caption                                                */
/* ---------------------------------------------------------------- */
export const kiraCaption = 'Kira speaks en-IN. ForgeOS is India-first by design.'
