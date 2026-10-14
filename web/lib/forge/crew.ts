// The factory-floor crew: how each agent in FACTORY_AGENTS looks and what it
// visibly does at each station. Status still comes from FACTORY_AGENTS, so a
// QUEUED agent naps in the standby bay instead of pretending to work.
//
// Colour note: the UI chrome stays on the locked ice-blue accent (#A4D8FF).
// Suits are the one place agents get their own hue, in muted tones chosen to
// sit under that accent on the #0C0E10 floor.

import type { SpriteProp } from '@/components/agents/AgentSprite'
import { FACTORY_AGENTS, type FactoryAgent } from '@/lib/forge/agents'

export type StationId = 'intake' | 'forge' | 'qa' | 'dock'

export const STATIONS: { id: StationId; label: string; x: number }[] = [
  // x starts at 0.24: the left of the floor is the standby bay.
  { id: 'intake', label: 'INTAKE · RESEARCH', x: 0.25 },
  { id: 'forge', label: 'FORGE · BUILD', x: 0.47 },
  { id: 'qa', label: 'QA LAB · BREAK IT', x: 0.69 },
  { id: 'dock', label: 'SHIP DOCK', x: 0.89 },
]

export type CrewMember = FactoryAgent & {
  suit: string
  prop: SpriteProp
  lane: number                                      // 0..1 depth on the floor
  route: StationId[]                                // stations it walks between
  actions: Partial<Record<StationId, string[]>>     // what its bubble says there
}

const LOOKS: Record<string, Omit<CrewMember, keyof FactoryAgent>> = {
  outreachforge: {
    suit: '#E0A96D', prop: 'megaphone', lane: 0, route: ['intake', 'dock'],
    actions: { intake: ['finding warm leads', 'scoring a lead'], dock: ['drafting a DM', 'waiting on founder ✓'] },
  },
  contractforge: {
    suit: '#A4D8FF', prop: 'scroll', lane: 0.5, route: ['forge', 'qa', 'dock'],
    actions: { forge: ['drafting NDA', 'adding GST clause'], qa: ['DPDP check'], dock: ['contract.pdf shipped'] },
  },
  clientforge: {
    suit: '#8FD3B8', prop: 'clipboard', lane: 0.25, route: ['intake', 'forge'],
    actions: { intake: ['reading the brief'], forge: ['writing a proposal', 'pricing in ₹'] },
  },
  specforge: {
    suit: '#B9A8F0', prop: 'magnifier', lane: 0.75, route: ['intake', 'forge', 'qa'],
    actions: { intake: ['jobs to be done'], forge: ['SPEC.md', 'ARCH.md', 'TASKS.json'], qa: ['gate 4/11 ✓'] },
  },
  gbrain: {
    suit: '#E89BB8', prop: 'brain', lane: 1, route: ['qa', 'intake', 'dock'],
    actions: { qa: ['reading 30 days of logs'], intake: ['new pattern found'], dock: ['updating AGENTS.md'] },
  },
  meetingforge: {
    suit: '#CDBF9C', prop: 'clipboard', lane: 0, route: [], actions: {},
  },
  reputationforge: {
    suit: '#E38B7E', prop: 'shield', lane: 0, route: [], actions: {},
  },
}

export const CREW: CrewMember[] = FACTORY_AGENTS.map((agent) => ({
  ...agent,
  ...(LOOKS[agent.slug] ?? { suit: '#A4D8FF', prop: 'wrench', lane: 0.5, route: ['forge'], actions: {} }),
}))

export const WORKING_CREW = CREW.filter((c) => c.status !== 'QUEUED' && c.route.length > 0)
export const STANDBY_CREW = CREW.filter((c) => c.status === 'QUEUED' || c.route.length === 0)

/** Artifacts that ride the conveyor belt, left to right. */
export const BELT_ITEMS = ['SPEC.md', 'ARCH.md', 'auth ✓', 'tests 309', 'SECURITY.md', 'contract.pdf', 'deploy →']
