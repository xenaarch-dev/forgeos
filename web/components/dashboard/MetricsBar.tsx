// web/components/dashboard/MetricsBar.tsx
'use client'

import { GlassPanel } from '@/components/app-shell/GlassPanel'
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
    { label: 'MRR · LIVE', value: `₹${totals.mrr.toLocaleString('en-IN')}` },
    { label: 'SIGNUPS', value: String(totals.signups) },
    { label: 'CONVERSIONS', value: String(totals.conversions) },
    { label: 'PRODUCTS TRACKED', value: String(rows.length) },
  ]

  return (
    <GlassPanel>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1 }}>
        {cells.map((cell) => (
          <div key={cell.label} style={{ padding: '16px 22px' }}>
            <div style={{ font: '400 7.5px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.2em', marginBottom: 7 }}>
              {cell.label}
            </div>
            <div style={{ font: '700 24px var(--font-serif)', color: 'var(--w)' }}>{cell.value}</div>
          </div>
        ))}
      </div>
    </GlassPanel>
  )
}
