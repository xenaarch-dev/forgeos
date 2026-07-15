// web/components/dashboard/ActivityStream.tsx
'use client'

import { useDashboardEvents } from '@/hooks/useDashboardEvents'

export function ActivityStream() {
  const logs = useDashboardEvents()

  return (
    <div style={{ border: '0.5px solid rgba(0,229,204,0.14)', borderRadius: 6, background: '#07080A', display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', borderBottom: '0.5px solid rgba(0,229,204,0.1)' }}>
        <span style={{ font: '400 8.5px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.18em' }}>AGENT ACTIVITY STREAM</span>
        <span style={{ font: '400 8px var(--font-body)', color: 'var(--w-ghost)', letterSpacing: '0.12em' }}>
          SUPABASE REALTIME · <span style={{ color: 'var(--teal)' }}>CONNECTED</span>
        </span>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', padding: '8px 0' }}>
        {logs.length === 0 && (
          <div style={{ padding: '5.5px 18px', font: '400 9.5px var(--font-body)', color: 'var(--w-ghost)' }}>
            No agent activity yet — this fills in as the pipeline runs.
          </div>
        )}
        {logs.map((log) => (
          <div key={log.id} style={{ display: 'flex', gap: 12, padding: '5.5px 18px', font: '400 9.5px var(--font-body)' }}>
            <span style={{ color: 'var(--w-ghost)', flexShrink: 0 }}>
              {new Date(log.created_at).toLocaleTimeString('en-IN', { hour12: false })}
            </span>
            <span style={{ color: 'var(--hud)', flexShrink: 0, minWidth: 88 }}>[{log.agent.toUpperCase()}]</span>
            <span style={{ color: log.event_type === 'error' ? 'var(--gold)' : 'var(--w-dim)' }}>{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
