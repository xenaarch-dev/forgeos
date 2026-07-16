export type PipelineStatus = 'COMPLETE' | 'RUNNING' | 'PENDING'

export type PipelineStage = {
  n: string
  name: string
  description: string
  icon: string
  status: PipelineStatus
  gate: boolean
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { n: '01', name: 'IDEA INTAKE', description: 'Prompt parsed. Intent, market, constraints extracted.', icon: '◉', status: 'COMPLETE', gate: false },
  { n: '02', name: 'ICP VALIDATION', description: 'Ideal customer profile scored against India SMB data.', icon: '⌖', status: 'COMPLETE', gate: false },
  { n: '03', name: 'SPEC GENERATION', description: 'Full product spec drafted by SpecForge.', icon: '◈', status: 'COMPLETE', gate: false },
  { n: '04', name: 'ARCHITECTURE', description: 'System design: Next.js, Supabase, edge functions.', icon: '⬡', status: 'COMPLETE', gate: false },
  { n: '05', name: 'DB SCHEMA', description: 'Postgres schema + RLS policies generated.', icon: '▤', status: 'COMPLETE', gate: false },
  { n: '06', name: 'API DESIGN', description: 'REST endpoints, auth flows, rate limits.', icon: '⇄', status: 'COMPLETE', gate: false },
  { n: '07', name: 'FRONTEND SPEC', description: 'Screens, states, component inventory.', icon: '▢', status: 'COMPLETE', gate: false },
  { n: '08', name: 'BRAND IDENTITY', description: 'Name, palette, type system, voice.', icon: '✦', status: 'COMPLETE', gate: false },
  { n: '09', name: 'SECURITY SCAN', description: 'OWASP pass, secrets audit, DPDP checklist.', icon: '◬', status: 'COMPLETE', gate: false },
  { n: '10', name: 'SCAFFOLD', description: 'GATE — founder approves the repo skeleton.', icon: '⌂', status: 'COMPLETE', gate: true },
  { n: '11', name: 'BACKEND BUILD', description: 'APIs, jobs, webhooks implemented.', icon: '⚙', status: 'COMPLETE', gate: false },
  { n: '12', name: 'FRONTEND BUILD', description: 'UI built to spec, dark-first.', icon: '▣', status: 'COMPLETE', gate: false },
  { n: '13', name: 'TESTS', description: 'GATE — 276 tests must go green.', icon: '✓', status: 'COMPLETE', gate: true },
  { n: '14', name: 'QA REVIEW', description: 'Agent-driven exploratory QA pass.', icon: '◎', status: 'COMPLETE', gate: false },
  { n: '15', name: 'LEGAL COMPLIANCE', description: 'GATE — GST, DPDP 2023, T&C review.', icon: '§', status: 'COMPLETE', gate: true },
  { n: '16', name: 'BRAND ASSETS', description: 'OG images, favicons, launch copy.', icon: '❖', status: 'COMPLETE', gate: false },
  { n: '17', name: 'DEPLOY', description: 'Vercel + Supabase prod, DNS, SSL.', icon: '↗', status: 'RUNNING', gate: false },
  { n: '18', name: 'LIVE ✓', description: 'Product serving traffic. Loop closes.', icon: '●', status: 'PENDING', gate: false },
]

export function pipelineProgress(): { complete: number; total: number; pct: number } {
  const complete = PIPELINE_STAGES.filter((s) => s.status === 'COMPLETE').length
  const total = PIPELINE_STAGES.length
  return { complete, total, pct: Math.round((complete / total) * 100) }
}
