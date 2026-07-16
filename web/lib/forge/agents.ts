export type FactoryAgentStatus = 'RUNNING' | 'LIVE' | 'ACTIVE' | 'QUEUED'

export type FactoryAgent = {
  slug: string
  name: string
  icon: string
  status: FactoryAgentStatus
  description: string
  lastAction: string
  totalRuns: number | null
  successRate: string | null
  lastRun: string | null
}

export const FACTORY_AGENTS: FactoryAgent[] = [
  {
    slug: 'outreachforge', name: 'OutreachForge', icon: '⇢', status: 'RUNNING',
    description: 'Finds warm leads. Drafts messages. Escalates to founder.',
    lastAction: 'SENT DM → @PRIYA_FINTECH · 2H AGO',
    totalRuns: 1204, successRate: '92%', lastRun: '2h',
  },
  {
    slug: 'contractforge', name: 'ContractForge', icon: '§', status: 'LIVE',
    description: 'GST-compliant contracts. Indian law. 60 seconds.',
    lastAction: 'NDA GENERATED · 14 MIN AGO',
    totalRuns: 276, successRate: '100%', lastRun: '14m',
  },
  {
    slug: 'clientforge', name: 'ClientForge', icon: '◈', status: 'RUNNING',
    description: 'Converts connections to paying clients.',
    lastAction: 'PROPOSAL SENT @RAHUL_DEVTOOLS',
    totalRuns: 388, successRate: '87%', lastRun: '1h',
  },
  {
    slug: 'specforge', name: 'SpecForge', icon: '◇', status: 'RUNNING',
    description: 'Prompt → full product spec. 18-stage pipeline.',
    lastAction: 'SPEC INITIATED: INVOICEFORGE',
    totalRuns: 41, successRate: '95%', lastRun: '32m',
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
    lastAction: 'NIGHTLY LOOP COMPLETE · 06:00 IST',
    totalRuns: 186, successRate: '100%', lastRun: '06:00',
  },
]

export function statusColor(status: FactoryAgentStatus): string {
  if (status === 'QUEUED') return 'rgba(164,216,255,0.35)'
  return '#A4D8FF'
}
