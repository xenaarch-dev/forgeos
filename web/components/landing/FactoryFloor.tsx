import { FACTORY_AGENTS, statusColor } from '@/lib/forge/agents'

export function FactoryFloor() {
  return (
    <section id="agents" style={{ minHeight: '100vh', background: '#0C0E10', padding: '120px 56px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <span style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.22em', flexShrink: 0 }}>
          THE FACTORY FLOOR
        </span>
        <svg width="100%" height="6" style={{ maxWidth: 300 }}>
          <line x1="0" y1="3" x2="300" y2="3" stroke="rgba(164,216,255,0.15)" strokeWidth="1" strokeDasharray="2 6" />
        </svg>
      </div>

      <h2 style={{ font: '900 72px/1.0 var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', textAlign: 'center', fontStyle: 'normal' }}>
        Seven agents. One closed loop.
      </h2>
      <p style={{ font: '400 18px var(--font-body)', color: 'rgba(236,235,230,0.40)', textAlign: 'center', maxWidth: 620, margin: '24px auto 64px', lineHeight: 1.6 }}>
        Every agent runs 24/7, logs every action, and feeds into a nightly reasoning cycle
        that makes the system smarter without the founder touching it.
      </p>

      <div style={{ display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 16, scrollbarWidth: 'none' }}>
        {FACTORY_AGENTS.map((agent) => (
          <div key={agent.slug} className="glass" style={{ minWidth: 200, flexShrink: 0, padding: 18, borderRadius: 4 }}>
            <div style={{ width: 40, height: 40, background: '#101316', border: '0.5px solid rgba(164,216,255,0.15)', display: 'grid', placeItems: 'center', font: '400 18px var(--font-mono)', color: '#A4D8FF', marginBottom: 14 }}>
              {agent.icon}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: statusColor(agent.status), animation: agent.status !== 'QUEUED' ? 'fg-pulse 2.4s ease-in-out infinite' : 'none' }} />
              <span style={{ font: '400 6px var(--font-mono)', letterSpacing: '0.10em', color: statusColor(agent.status) }}>{agent.status}</span>
            </div>
            <div style={{ font: '700 20px var(--font-display)', letterSpacing: '-0.02em', color: '#ECEBE6', marginBottom: 8, fontStyle: 'normal' }}>
              {agent.name}
            </div>
            <p style={{ font: '300 11px var(--font-body)', color: 'rgba(236,235,230,0.40)', lineHeight: 1.55, marginBottom: 16, minHeight: 50 }}>
              {agent.description}
            </p>
            <div style={{ borderTop: '0.5px solid rgba(164,216,255,0.10)', paddingTop: 10, font: '400 7px var(--font-mono)', color: 'rgba(164,216,255,0.45)' }}>
              {agent.lastAction}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
