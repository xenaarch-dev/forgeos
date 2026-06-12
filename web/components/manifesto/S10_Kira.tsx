'use client'

import AgentChapter from '@/components/fx/AgentPanel'
import TerminalSim from '@/components/fx/TerminalSim'
import { kiraDeploy, kiraCaption } from '@/data/simulations'

export default function S10_Kira() {
  return (
    <AgentChapter
      eyebrow="// Kira → DeployAgent"
      name="Kira"
      role="She ships it. To production. Tonight."
      glow="cel"
      caption={kiraCaption}
    >
      {(active) => (
        <TerminalSim lines={kiraDeploy} active={active} title="kira@forgeos — deploy" />
      )}
    </AgentChapter>
  )
}
