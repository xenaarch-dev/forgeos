// web/lib/agents/roster.test.ts
import { describe, expect, it } from 'vitest'
import { AGENT_ROSTER, statusDotColor, statusLabel } from './roster'

describe('statusDotColor', () => {
  it('uses the ice-blue accent when running', () => {
    expect(statusDotColor('running')).toBe('#A4D8FF')
  })

  it('uses the ice-blue accent when live', () => {
    expect(statusDotColor('live')).toBe('#A4D8FF')
  })

  it('dims the accent when active', () => {
    expect(statusDotColor('active')).toBe('rgba(164,216,255,0.60)')
  })

  it('uses a dim neutral when queued', () => {
    expect(statusDotColor('queued')).toBe('rgba(236,235,230,0.25)')
  })
})

describe('statusLabel', () => {
  it('appends a checkmark for live', () => {
    expect(statusLabel('live')).toBe('LIVE ✓')
  })

  it('uppercases other statuses as-is', () => {
    expect(statusLabel('queued')).toBe('QUEUED')
  })
})

describe('AGENT_ROSTER', () => {
  it('has exactly 7 agents, matching the PRD roster', () => {
    expect(AGENT_ROSTER).toHaveLength(7)
  })

  it('uses the locked ice-blue system — no per-agent accent field', () => {
    expect(AGENT_ROSTER.every((a) => !('accent' in a))).toBe(true)
  })
})
