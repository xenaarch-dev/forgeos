'use client'

import { useDashboardEvents } from '@/hooks/useDashboardEvents'

const TAG_COLOR: Record<string, string> = {
  error: 'var(--error)',
  gate: 'rgba(164,216,255,0.70)',
  action: 'rgba(164,216,255,0.55)',
  info: 'rgba(164,216,255,0.45)',
}

export function ActivityStream() {
  const logs = useDashboardEvents()

  return (
    <div style={{ borderRight: '0.5px solid rgba(164,216,255,0.10)', display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '0.5px solid rgba(164,216,255,0.10)' }}>
        <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.20em' }}>ACTIVITY STREAM</span>
        <span style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.10em', animation: logs.length > 0 ? 'fg-pulse 2.4s ease-in-out infinite' : 'none' }}>
          + LIVE
        </span>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', padding: '8px 0' }}>
        {logs.length === 0 && (
          <div style={{ padding: '6px 20px', font: '300 13px var(--font-body)', color: 'rgba(236,235,230,0.30)' }}>
            No agent activity yet — this fills in as the pipeline runs.
          </div>
        )}
        {[...logs].reverse().map((log) => (
          <div
            key={log.id}
            style={{
              display: 'flex', gap: 12, padding: '7px 20px',
              borderLeft: `2px solid ${TAG_COLOR[log.event_type] ?? TAG_COLOR.info}`,
            }}
          >
            <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.30)', width: 56, flexShrink: 0 }}>
              {new Date(log.created_at).toLocaleTimeString('en-IN', { hour12: false })}
            </span>
            <span style={{ font: '400 7px var(--font-mono)', letterSpacing: '0.10em', color: TAG_COLOR[log.event_type] ?? TAG_COLOR.info, flexShrink: 0, minWidth: 70 }}>
              [{log.agent.toUpperCase()}]
            </span>
            <span style={{ font: '300 13px var(--font-body)', color: 'rgba(236,235,230,0.65)' }}>{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
