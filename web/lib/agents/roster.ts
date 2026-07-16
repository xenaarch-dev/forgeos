// web/lib/agents/roster.ts
export type AgentStatus = 'running' | 'live' | 'active' | 'queued'

export type AgentDefinition = {
  slug: string
  name: string
  defaultStatus: AgentStatus
}

// Ice-blue (#A4D8FF) locked design system — single accent, no per-agent hues.
export const AGENT_ROSTER: AgentDefinition[] = [
  { slug: 'outreach', name: 'OutreachForge', defaultStatus: 'running' },
  { slug: 'contract', name: 'ContractForge', defaultStatus: 'live' },
  { slug: 'client', name: 'ClientForge', defaultStatus: 'running' },
  { slug: 'spec', name: 'SpecForge', defaultStatus: 'running' },
  { slug: 'meeting', name: 'MeetingForge', defaultStatus: 'queued' },
  { slug: 'reputation', name: 'ReputationForge', defaultStatus: 'queued' },
  { slug: 'gbrain', name: 'GBrain', defaultStatus: 'active' },
]

export function statusDotColor(status: AgentStatus): string {
  if (status === 'running' || status === 'live') return '#A4D8FF'
  if (status === 'active') return 'rgba(164,216,255,0.60)'
  return 'rgba(236,235,230,0.25)'
}

export function statusLabel(status: AgentStatus): string {
  if (status === 'live') return 'LIVE ✓'
  return status.toUpperCase()
}
