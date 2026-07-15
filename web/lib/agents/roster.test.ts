// web/lib/agents/roster.test.ts
import { describe, expect, it } from 'vitest'
import { AGENT_ROSTER, statusDotColor } from './roster'

describe('statusDotColor', () => {
  it('returns the agent accent when running', () => {
    expect(statusDotColor('running', '#00E5CC')).toBe('#00E5CC')
  })

  it('returns a dim neutral when queued', () => {
    expect(statusDotColor('queued', '#00E5CC')).toBe('rgba(240,237,232,0.35)')
  })

  it('returns a dimmer neutral when idle', () => {
    expect(statusDotColor('idle', '#00E5CC')).toBe('rgba(240,237,232,0.15)')
  })
})

describe('AGENT_ROSTER', () => {
  it('has exactly 7 agents, matching the PRD roster', () => {
    expect(AGENT_ROSTER).toHaveLength(7)
  })

  it('uses only Cosmic Garden accents, no ice-blue leftover from the mockup', () => {
    const iceBlue = '#A4D8FF'
    expect(AGENT_ROSTER.some((a) => a.accent === iceBlue)).toBe(false)
  })
})
