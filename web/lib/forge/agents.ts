export type FactoryAgentStatus = 'RUNNING' | 'LIVE' | 'ACTIVE' | 'QUEUED'

export type FactoryAgent = {
  slug: string
  name: string
  icon: string
  status: FactoryAgentStatus
  description: string
  lastAction: string | null
  totalRuns: number | null
  successRate: string | null
  lastRun: string | null
}

// Per-agent lastAction/totalRuns/successRate/lastRun are null unless there's
// a real logged source — no agent-level activity feed is wired yet (see
// /api/metrics recent_activity for the real, dashboard_events-backed feed).
// QUEUED agents' lastAction is an exception: it's a real static activation
// condition, not a fabricated activity claim.
export const FACTORY_AGENTS: FactoryAgent[] = [
  {
    slug: 'outreachforge', name: 'OutreachForge', icon: '⇢', status: 'RUNNING',
    description: 'Finds warm leads. Drafts messages. Escalates to founder.',
    lastAction: null,
    totalRuns: null, successRate: null, lastRun: null,
  },
  {
    slug: 'contractforge', name: 'ContractForge', icon: '§', status: 'LIVE',
    description: 'GST-compliant contracts. Indian law. 60 seconds.',
    lastAction: null,
    totalRuns: null, successRate: null, lastRun: null,
  },
  {
    slug: 'clientforge', name: 'ClientForge', icon: '◈', status: 'RUNNING',
    description: 'Converts connections to paying clients.',
    lastAction: null,
    totalRuns: null, successRate: null, lastRun: null,
  },
  {
    slug: 'specforge', name: 'SpecForge', icon: '◇', status: 'RUNNING',
    description: 'Prompt → full product spec. 18-stage pipeline.',
    lastAction: null,
    totalRuns: null, successRate: null, lastRun: null,
  },
  {
    slug: 'meetingforge', name: 'MeetingForge', icon: '◎', status: 'QUEUED',
    description: 'Agendas, notes, follow-ups. Auto.',
    lastAction: 'ACTIVATES AT 10 ACTIVE CLIENTS',
    totalRuns: null, successRate: null, lastRun: null,
  },
  {
    slug: 'reputationforge', name: 'ReputationForge', icon: '✦', status: 'QUEUED',
    description: 'Brand monitoring. Response drafts.',
    lastAction: 'ACTIVATES AT 100 USERS',
    totalRuns: null, successRate: null, lastRun: null,
  },
  {
    slug: 'gbrain', name: 'GBrain', icon: '◉', status: 'ACTIVE',
    description: 'Intelligence layer. Nightly reasoning. AGENTS.md updates.',
    lastAction: null,
    totalRuns: null, successRate: null, lastRun: null,
  },
]

export function statusColor(status: FactoryAgentStatus): string {
  if (status === 'QUEUED') return 'rgba(164,216,255,0.35)'
  return '#A4D8FF'
}
