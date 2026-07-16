'use client'

import { useState } from 'react'

const SECTIONS = ['PROFILE', 'WORKSPACE', 'AGENTS', 'INTEGRATIONS', 'SECURITY', 'DANGER ZONE'] as const
type Section = (typeof SECTIONS)[number]

const FIELD_STYLE: React.CSSProperties = {
  width: '100%', background: 'var(--glass-bg)', border: '0.5px solid rgba(164,216,255,0.20)',
  borderRadius: 2, padding: '10px 12px', color: '#ECEBE6', font: '400 13px var(--font-body)', marginTop: 8,
}

const LABEL_STYLE: React.CSSProperties = {
  font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.14em',
}

const INTEGRATIONS = [
  { name: 'Discord Webhook', subtitle: 'approvals + escalations channel', status: 'CONNECTED', action: 'REGENERATE' },
  { name: 'Supabase', subtitle: 'ap-south-1 · realtime enabled', status: 'CONNECTED', action: 'VIEW' },
  { name: 'Lemon Squeezy', subtitle: 'store #323289', status: 'CONNECTED', action: 'VIEW' },
  { name: 'Resend', subtitle: 'mail.contractforge.co.in', status: 'CONNECTED', action: 'VIEW' },
  { name: 'Telegram', subtitle: 'unavailable in this region', status: 'BLOCKED IN INDIA', action: null },
  { name: 'LinkedIn', subtitle: 'API access under review', status: 'RESTRICTED', action: 'STATUS' },
]

function statusColor(status: string) {
  if (status === 'CONNECTED') return '#A4D8FF'
  if (status === 'BLOCKED IN INDIA') return 'var(--error)'
  return '#E8961F'
}

export default function SettingsPage() {
  const [section, setSection] = useState<Section>('PROFILE')
  const [confirmAction, setConfirmAction] = useState<string | null>(null)

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <nav style={{ width: 220, flexShrink: 0, borderRight: '0.5px solid rgba(164,216,255,0.10)', padding: '20px 12px' }}>
        {SECTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setSection(s)}
            style={{
              display: 'block', width: '100%', textAlign: 'left', padding: '10px 12px',
              background: section === s ? 'rgba(164,216,255,0.08)' : 'transparent',
              borderLeft: section === s ? '2px solid #A4D8FF' : '2px solid transparent',
              color: section === s ? '#A4D8FF' : 'rgba(236,235,230,0.45)',
              font: '400 9px var(--font-mono)', letterSpacing: '0.14em',
            }}
          >
            {s}
          </button>
        ))}
      </nav>

      <div style={{ flex: 1, padding: 32, overflowY: 'auto' }}>
        {section === 'PROFILE' && (
          <div style={{ maxWidth: 440 }}>
            <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 28 }}>Profile</h1>
            <div style={{ width: 80, height: 80, borderRadius: '50%', border: '1px dashed rgba(164,216,255,0.30)', display: 'grid', placeItems: 'center', font: '700 24px var(--font-display)', color: '#A4D8FF', marginBottom: 24 }}>
              X
            </div>
            <label style={LABEL_STYLE}>FULL NAME</label>
            <input defaultValue="xenarch" style={FIELD_STYLE} />
            <label style={{ ...LABEL_STYLE, display: 'block', marginTop: 18 }}>DISPLAY NAME</label>
            <input defaultValue="xenarch" style={FIELD_STYLE} />
            <label style={{ ...LABEL_STYLE, display: 'block', marginTop: 18 }}>EMAIL — READ ONLY</label>
            <input defaultValue="x@xenarch.in" disabled style={{ ...FIELD_STYLE, opacity: 0.5 }} />
            <label style={{ ...LABEL_STYLE, display: 'block', marginTop: 18 }}>LOCATION</label>
            <input defaultValue="Mumbai, India" style={FIELD_STYLE} />
            <button style={{ marginTop: 24, background: '#A4D8FF', color: '#0C0E10', font: '400 9px var(--font-mono)', letterSpacing: '0.08em', padding: '12px 24px' }}>
              SAVE CHANGES
            </button>
          </div>
        )}

        {section === 'WORKSPACE' && (
          <div style={{ maxWidth: 440 }}>
            <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 28 }}>Workspace</h1>
            <label style={LABEL_STYLE}>WORKSPACE NAME</label>
            <input defaultValue="xenarch" style={FIELD_STYLE} />
            <label style={{ ...LABEL_STYLE, display: 'block', marginTop: 18 }}>DATA REGION</label>
            <input defaultValue="ap-south-1 · Mumbai" disabled style={{ ...FIELD_STYLE, opacity: 0.5 }} />
            <button style={{ marginTop: 24, background: '#A4D8FF', color: '#0C0E10', font: '400 9px var(--font-mono)', letterSpacing: '0.08em', padding: '12px 24px' }}>
              SAVE CHANGES
            </button>
          </div>
        )}

        {section === 'AGENTS' && (
          <div style={{ maxWidth: 560 }}>
            <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 28 }}>Agent Defaults</h1>
            {[
              { label: 'Nightly reasoning loop · 02:00 IST', on: true },
              { label: 'Escalate warm leads to Discord', on: true },
              { label: 'Auto-approve artifacts under ₹0 value', on: false },
            ].map((row) => (
              <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '0.5px solid rgba(164,216,255,0.10)' }}>
                <span style={{ font: '400 13px var(--font-body)', color: '#ECEBE6' }}>{row.label}</span>
                <span style={{ font: '400 8px var(--font-mono)', color: row.on ? '#A4D8FF' : 'rgba(236,235,230,0.30)', letterSpacing: '0.10em' }}>
                  {row.on ? 'ENABLED' : 'OFF'}
                </span>
              </div>
            ))}
          </div>
        )}

        {section === 'INTEGRATIONS' && (
          <div style={{ maxWidth: 640 }}>
            <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 28 }}>Integrations</h1>
            {INTEGRATIONS.map((i) => (
              <div key={i.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '0.5px solid rgba(164,216,255,0.10)' }}>
                <div>
                  <div style={{ font: '400 13px var(--font-body)', color: '#ECEBE6' }}>{i.name}</div>
                  <div style={{ font: '400 10px var(--font-mono)', color: 'rgba(236,235,230,0.35)', marginTop: 3 }}>{i.subtitle}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <span className="glass" style={{ padding: '4px 10px', borderRadius: 2, font: '400 7px var(--font-mono)', color: statusColor(i.status), letterSpacing: '0.08em' }}>
                    {i.status}
                  </span>
                  {i.action && (
                    <button style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.08em' }}>{i.action}</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {section === 'SECURITY' && (
          <div style={{ maxWidth: 560 }}>
            <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 28 }}>Security</h1>
            {[
              { label: 'Two-factor authentication', value: 'ENABLED', color: '#A4D8FF' },
              { label: 'Active sessions', value: '1 · MUMBAI', color: 'rgba(236,235,230,0.55)' },
              { label: 'API keys', value: 'MANAGE →', color: '#A4D8FF' },
            ].map((row) => (
              <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '0.5px solid rgba(164,216,255,0.10)' }}>
                <span style={{ font: '400 13px var(--font-body)', color: '#ECEBE6' }}>{row.label}</span>
                <span style={{ font: '400 9px var(--font-mono)', color: row.color, letterSpacing: '0.08em' }}>{row.value}</span>
              </div>
            ))}
          </div>
        )}

        {section === 'DANGER ZONE' && (
          <div style={{ maxWidth: 640 }}>
            <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 28 }}>Danger Zone</h1>
            <div style={{ border: '0.5px solid rgba(226,76,75,0.40)', borderRadius: 4, padding: 24 }}>
              <div style={{ font: '400 8px var(--font-mono)', color: 'var(--error)', letterSpacing: '0.16em', marginBottom: 20 }}>
                DANGER ZONE
              </div>
              {[
                { label: 'Permanently delete every artifact the mesh has produced.', action: 'DELETE ALL ARTIFACTS' },
                { label: 'Clear 186 days of agent logs. GBrain loses its memory.', action: 'RESET AGENT LOGS' },
              ].map((row) => (
                <div key={row.action} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 20, padding: '14px 0' }}>
                  <span style={{ font: '300 12px var(--font-body)', color: 'rgba(236,235,230,0.55)' }}>{row.label}</span>
                  <button
                    onClick={() => setConfirmAction(row.action)}
                    style={{ flexShrink: 0, border: '0.5px solid var(--error)', color: 'var(--error)', font: '400 8px var(--font-mono)', letterSpacing: '0.08em', padding: '10px 14px' }}
                  >
                    {row.action}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {confirmAction && (
        <div onClick={() => setConfirmAction(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(12,14,16,0.85)', zIndex: 400, display: 'grid', placeItems: 'center' }}>
          <div onClick={(e) => e.stopPropagation()} className="glass" style={{ width: 380, borderRadius: 6, padding: 28, border: '0.5px solid rgba(226,76,75,0.40)' }}>
            <div style={{ font: '400 8px var(--font-mono)', color: 'var(--error)', letterSpacing: '0.16em', marginBottom: 14 }}>CONFIRM</div>
            <p style={{ font: '300 14px var(--font-body)', color: '#ECEBE6', lineHeight: 1.6, marginBottom: 24 }}>
              Are you sure you want to {confirmAction.toLowerCase()}? This cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setConfirmAction(null)} style={{ flex: 1, border: '0.5px solid var(--error)', color: 'var(--error)', font: '400 9px var(--font-mono)', padding: '12px 0' }}>
                CONFIRM
              </button>
              <button onClick={() => setConfirmAction(null)} style={{ flex: 1, border: '0.5px solid rgba(236,235,230,0.20)', color: 'rgba(236,235,230,0.55)', font: '400 9px var(--font-mono)', padding: '12px 0' }}>
                CANCEL
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
