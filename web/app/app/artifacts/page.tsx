'use client'

import { useState } from 'react'
import { ARTIFACTS, TYPE_COLOR, STATUS_COLOR, type ArtifactType, type Artifact } from '@/lib/forge/artifacts'

const FILTERS: (ArtifactType | 'ALL')[] = ['ALL', 'CONTRACT', 'SPEC', 'EMAIL', 'PROPOSAL']

export default function ArtifactsPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('ALL')
  const [selected, setSelected] = useState<Artifact | null>(null)
  const visible = filter === 'ALL' ? ARTIFACTS : ARTIFACTS.filter((a) => a.type === filter)

  return (
    <div style={{ padding: 32, position: 'relative' }}>
      <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', letterSpacing: '-0.03em' }}>Artifacts</h1>
      <p style={{ font: '400 9px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.10em', marginTop: 8 }}>
        ALL AGENT OUTPUTS · CONTRACT · SPEC · EMAIL
      </p>

      <div style={{ display: 'flex', gap: 4, margin: '28px 0 20px', borderBottom: '0.5px solid rgba(164,216,255,0.10)' }}>
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

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '0.5px solid rgba(164,216,255,0.12)' }}>
              {['TYPE', 'TITLE', 'AGENT', 'DATE', 'STATUS', 'ACTIONS'].map((h) => (
                <th key={h} style={{ textAlign: 'left', padding: '10px 14px', font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.20em' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((a) => (
              <tr
                key={a.id}
                onClick={() => setSelected(a)}
                style={{ borderBottom: '0.5px solid rgba(164,216,255,0.06)', cursor: 'pointer' }}
              >
                <td style={{ padding: '12px 14px' }}>
                  <span className="glass" style={{ display: 'inline-block', padding: '3px 8px', borderRadius: 2, font: '400 7px var(--font-mono)', color: TYPE_COLOR[a.type] }}>
                    {a.type}
                  </span>
                </td>
                <td style={{ padding: '12px 14px', font: '400 13px var(--font-body)', color: '#ECEBE6' }}>{a.title}</td>
                <td style={{ padding: '12px 14px', font: '400 10px var(--font-mono)', color: 'rgba(236,235,230,0.45)' }}>{a.agent}</td>
                <td style={{ padding: '12px 14px', font: '400 10px var(--font-mono)', color: 'rgba(236,235,230,0.35)' }}>{a.date}</td>
                <td style={{ padding: '12px 14px', font: '400 9px var(--font-mono)', color: STATUS_COLOR[a.status] }}>{a.status}</td>
                <td style={{ padding: '12px 14px', font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.08em' }}>VIEW · EXPORT</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <>
          <div onClick={() => setSelected(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 300 }} />
          <div
            className="glass"
            style={{
              position: 'fixed', top: 78, right: 0, bottom: 52, width: 400, zIndex: 301,
              padding: 28, overflowY: 'auto', borderRadius: 0,
            }}
          >
            <span className="glass" style={{ display: 'inline-block', padding: '3px 8px', borderRadius: 2, font: '400 7px var(--font-mono)', color: TYPE_COLOR[selected.type], marginBottom: 14 }}>
              [{selected.type}]
            </span>
            <h2 style={{ font: '700 24px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 20 }}>
              {selected.title}
            </h2>
            <pre
              style={{
                whiteSpace: 'pre-wrap', font: selected.type === 'CONTRACT' ? '400 8.5px var(--font-mono)' : '400 12px var(--font-body)',
                color: 'rgba(236,235,230,0.60)', lineHeight: 1.7, marginBottom: 24,
              }}
            >
              {selected.body}
            </pre>
            <button style={{ background: '#A4D8FF', color: '#0C0E10', font: '400 9px var(--font-mono)', letterSpacing: '0.10em', padding: '12px 20px' }}>
              EXPORT PDF
            </button>
          </div>
        </>
      )}
    </div>
  )
}
