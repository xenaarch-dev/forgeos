// web/components/dashboard/AgentRoster.tsx
import { GlassPanel } from '@/components/app-shell/GlassPanel'
import { BotAvatar } from '@/components/app-shell/BotAvatar'
import { Sigil } from '@/components/app-shell/Sigil'
import { AGENT_ROSTER, statusDotColor } from '@/lib/agents/roster'

export function AgentRoster() {
  return (
    <GlassPanel style={{ height: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', padding: '16px 14px', height: '100%', overflowY: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBottom: 14, borderBottom: '0.5px solid rgba(0,229,204,0.12)', marginBottom: 14 }}>
          <Sigil size={30} glowIntensity={0.3} />
          <div>
            <div style={{ font: '900 14px var(--font-serif)', color: 'var(--w)' }}>ForgeOS</div>
            <div style={{ font: '400 7px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.14em', marginTop: 3 }}>
              WAR ROOM · DIM · HONEST
            </div>
          </div>
        </div>
        <div style={{ font: '400 8px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.2em', marginBottom: 12 }}>
          AGENT ROSTER · {AGENT_ROSTER.length}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {AGENT_ROSTER.map((agent) => (
            <div key={agent.slug} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 8px' }}>
              <BotAvatar accent={agent.accent} size={30} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ font: '400 10.5px var(--font-body)', color: 'var(--w)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {agent.name}
                </div>
                <div style={{ font: '400 7px var(--font-body)', color: 'var(--w-ghost)', letterSpacing: '0.12em' }}>
                  {agent.defaultStatus.toUpperCase()}
                </div>
              </div>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: statusDotColor(agent.defaultStatus, agent.accent), flexShrink: 0 }} />
            </div>
          ))}
        </div>
      </div>
    </GlassPanel>
  )
}
