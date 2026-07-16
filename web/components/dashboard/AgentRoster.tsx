import { AGENT_ROSTER, statusDotColor, statusLabel } from '@/lib/agents/roster'

export function AgentRoster() {
  return (
    <div style={{ borderRight: '0.5px solid rgba(164,216,255,0.10)', display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto', padding: '18px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
        <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.20em' }}>
          AGENT ROSTER
        </span>
        <span style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.10em', animation: 'fg-pulse 2.4s ease-in-out infinite' }}>
          + LIVE
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {AGENT_ROSTER.map((agent) => (
          <div key={agent.slug} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 6px' }}>
            <span
              style={{
                width: 6, height: 6, borderRadius: '50%', background: statusDotColor(agent.defaultStatus), flexShrink: 0,
                animation: agent.defaultStatus === 'running' || agent.defaultStatus === 'active' ? 'fg-pulse 2.4s ease-in-out infinite' : 'none',
              }}
            />
            <span style={{ font: '400 14px var(--font-body)', color: '#ECEBE6', flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {agent.name}
            </span>
            <span style={{ font: '400 7px var(--font-mono)', letterSpacing: '0.10em', color: statusDotColor(agent.defaultStatus), flexShrink: 0 }}>
              {statusLabel(agent.defaultStatus)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
