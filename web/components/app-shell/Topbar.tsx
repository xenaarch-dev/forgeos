'use client'

export function Topbar() {
  return (
    <div
      style={{
        height: 48, flexShrink: 0, background: 'rgba(7,8,10,0.99)', borderBottom: '0.5px solid rgba(164,216,255,0.10)',
        display: 'flex', alignItems: 'center', padding: '0 24px', position: 'relative',
      }}
    >
      <div style={{ font: '400 9px var(--font-mono)', color: 'rgba(236,235,230,0.45)' }}>
        xenarch ·
      </div>
      <div style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', font: '900 22px var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal' }}>
        ForgeOS
      </div>
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          aria-label="Refresh"
          style={{ width: 26, height: 26, display: 'grid', placeItems: 'center', color: 'rgba(236,235,230,0.45)', font: '400 12px var(--font-mono)' }}
        >
          ↻
        </button>
        <div className="glass" style={{ display: 'flex', alignItems: 'center', padding: '5px 10px', borderRadius: 3 }}>
          <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.55)', letterSpacing: '0.08em' }}>COMMAND ⌘K</span>
        </div>
        <a
          href="/login"
          aria-label="Log out"
          style={{
            width: 26, height: 26, borderRadius: '50%', border: '0.5px solid rgba(236,235,230,0.20)',
            display: 'grid', placeItems: 'center', font: '400 10px var(--font-mono)', color: 'rgba(236,235,230,0.45)',
          }}
        >
          ✕
        </a>
      </div>
    </div>
  )
}
