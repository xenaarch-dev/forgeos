// web/lib/agents/roster.ts
export type AgentStatus = 'running' | 'idle' | 'queued'

export type AgentDefinition = {
  slug: string
  name: string
  accent: string
  defaultStatus: AgentStatus
}

// Cosmic Garden accents only (teal/gold/violet/azure family) — never the
// ice-blue (#A4D8FF) values from ForgeOS_War_Room_dc.html's source markup.
export const AGENT_ROSTER: AgentDefinition[] = [
  { slug: 'outreach',   name: 'OutreachForge',   accent: '#00E5CC', defaultStatus: 'running' },
  { slug: 'contract',   name: 'ContractForge',   accent: '#3B82F6', defaultStatus: 'running' },
  { slug: 'core',       name: 'ForgeOS Core',    accent: '#7C3AED', defaultStatus: 'running' },
  { slug: 'spec',       name: 'SpecForge',       accent: '#00C2AB', defaultStatus: 'idle' },
  { slug: 'reputation', name: 'ReputationForge', accent: '#5B8DEF', defaultStatus: 'queued' },
  { slug: 'nightly',    name: 'NightlyAgent',    accent: '#9061E0', defaultStatus: 'queued' },
  { slug: 'client',     name: 'ClientForge',     accent: '#E8961F', defaultStatus: 'idle' },
]

export function statusDotColor(status: AgentStatus, accent: string): string {
  if (status === 'running') return accent
  if (status === 'queued') return 'rgba(240,237,232,0.35)'
  return 'rgba(240,237,232,0.15)'
}
