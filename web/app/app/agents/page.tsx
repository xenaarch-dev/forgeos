'use client'

import { useState } from 'react'
import { FACTORY_AGENTS, statusColor, type FactoryAgentStatus } from '@/lib/forge/agents'

const FILTERS: (FactoryAgentStatus | 'ALL')[] = ['ALL', 'RUNNING', 'LIVE', 'QUEUED']

export default function AgentsPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('ALL')
  const activeCount = FACTORY_AGENTS.filter((a) => a.status !== 'QUEUED').length
  const visible = filter === 'ALL' ? FACTORY_AGENTS : FACTORY_AGENTS.filter((a) => a.status === filter)

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', letterSpacing: '-0.03em' }}>Agents</h1>
          <p style={{ font: '400 9px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.10em', marginTop: 8 }}>
            SEVEN IN MESH · {activeCount} ACTIVE NOW
          </p>
        </div>
        <button className="glass" data-magnetic style={{ padding: '10px 18px', borderRadius: 3, font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.10em' }}>
          + NEW AGENT
        </button>
      </div>

      <div style={{ display: 'flex', gap: 4, margin: '28px 0 24px', borderBottom: '0.5px solid rgba(164,216,255,0.10)' }}>
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '10px 16px', font: '400 9px var(--font-mono)', letterSpacing: '0.08em',
              background: filter === f ? 'rgba(164,216,255,0.12)' : 'transparent',
              borderBottom: filter === f ? '2px solid #A4D8FF' : '2px solid transparent',
              color: filter === f ? '#A4D8FF' : 'rgba(236,235,230,0.40)',
            }}
          >
            {f}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
        {visible.map((agent) => {
          const queued = agent.status === 'QUEUED'
          return (
            <div key={agent.slug} className="glass" style={{ borderRadius: 4, padding: 22, borderTop: `2px solid ${statusColor(agent.status)}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
                <span style={{ font: '700 24px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal' }}>{agent.name}</span>
                <span style={{ font: '400 8px var(--font-mono)', color: statusColor(agent.status) }}>• {agent.status} v2.1</span>
              </div>
              <p style={{ font: '300 13px var(--font-body)', color: 'rgba(236,235,230,0.55)', marginBottom: 16 }}>
                {agent.description}
              </p>

              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.50)', marginBottom: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {agent.lastAction ?? 'No activity logged yet'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 20, flexShrink: 0 }}>
                  {[
                    { v: agent.totalRuns ?? '—', l: 'TOTAL RUNS' },
                    { v: agent.successRate ?? '—', l: 'SUCCESS RATE' },
                    { v: agent.lastRun ?? '—', l: 'LAST RUN' },
                  ].map((s) => (
                    <div key={s.l} style={{ textAlign: 'right' }}>
                      <div style={{ font: '700 20px var(--font-display)', color: queued ? 'rgba(236,235,230,0.25)' : '#ECEBE6', fontStyle: 'normal' }}>{s.v}</div>
                      <div style={{ font: '400 6.5px var(--font-mono)', color: 'rgba(236,235,230,0.25)', letterSpacing: '0.08em', marginTop: 2 }}>{s.l}</div>
                    </div>
                  ))}
                </div>
              </div>

              {queued && agent.lastAction && (
                <div style={{ font: '300 11px var(--font-body)', color: 'rgba(236,235,230,0.30)', marginTop: 10 }}>
                  Awaiting activation / Trigger: {agent.lastAction.toLowerCase().replace('activates at ', '')}
                </div>
              )}

              <div style={{ display: 'flex', gap: 8, marginTop: 18, borderTop: '0.5px solid rgba(164,216,255,0.10)', paddingTop: 16 }}>
                <button style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.08em' }}>VIEW LOGS →</button>
                <button className="glass" style={{ padding: '6px 12px', borderRadius: 2, font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.45)' }}>PAUSE</button>
                <button className="glass" style={{ padding: '6px 12px', borderRadius: 2, font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.45)' }}>CONFIGURE</button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
