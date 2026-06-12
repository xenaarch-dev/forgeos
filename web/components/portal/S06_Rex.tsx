'use client'

import AgentChapter from '@/components/portal/AgentChapter'
import TerminalSim from '@/components/fx/TerminalSim'
import { rexScaffold } from '@/data/simulations'

export default function S06_Rex() {
  return (
    <AgentChapter
      eyebrow="// Rex → ScaffoldAgent"
      name="Rex"
      role="He builds the skeleton in 90 seconds."
      glow="gold"
      tint="glass-warm"
    >
      {(active) => (
        <TerminalSim
          lines={rexScaffold}
          active={active}
          title="rex@forgeos — scaffold"
        />
      )}
    </AgentChapter>
  )
}
