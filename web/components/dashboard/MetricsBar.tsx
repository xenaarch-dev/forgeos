'use client'

import { useProductMetrics } from '@/hooks/useProductMetrics'

export function MetricsBar() {
  const rows = useProductMetrics()
  const totals = rows.reduce(
    (acc, r) => ({
      mrr: acc.mrr + r.mrr_inr,
      signups: acc.signups + r.signups,
      conversions: acc.conversions + r.conversions,
    }),
    { mrr: 0, signups: 0, conversions: 0 }
  )

  const cells = [
    { value: `₹${totals.mrr.toLocaleString('en-IN')}`, label: 'MRR', color: '#ECEBE6' },
    { value: String(totals.signups), label: 'LEADS', color: '#A4D8FF' },
    { value: '276 ✓', label: 'TESTS', color: '#A4D8FF' },
  ]

  return (
    <div
      style={{
        height: 52, flexShrink: 0, background: 'rgba(7,8,10,0.99)', borderTop: '0.5px solid rgba(164,216,255,0.12)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-evenly',
      }}
    >
      {cells.map((cell, i) => (
        <div key={cell.label} style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          {i > 0 && <div style={{ width: 1, height: 24, background: 'rgba(236,235,230,0.10)' }} />}
          <div style={{ textAlign: 'center' }}>
            <div style={{ font: '700 22px var(--font-display)', color: cell.color, fontStyle: 'normal' }}>{cell.value}</div>
            <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(236,235,230,0.20)', letterSpacing: '0.14em', marginTop: 2 }}>{cell.label}</div>
          </div>
        </div>
      ))}
      <div style={{ width: 1, height: 24, background: 'rgba(236,235,230,0.10)' }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#A4D8FF', animation: 'fg-pulse 2.4s ease-in-out infinite' }} />
        <div>
          <div style={{ font: '700 14px var(--font-mono)', color: '#A4D8FF' }}>LIVE</div>
          <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(236,235,230,0.20)', letterSpacing: '0.14em', marginTop: 2 }}>CONTRACTFORGE</div>
        </div>
      </div>
    </div>
  )
}
