'use client'

import { useState } from 'react'
import Link from 'next/link'
import { PIPELINE_STAGES, pipelineProgress, type PipelineStage } from '@/lib/forge/pipeline'

const STATUS_COLOR: Record<PipelineStage['status'], string> = {
  COMPLETE: '#A4D8FF',
  RUNNING: '#A4D8FF',
  PENDING: 'rgba(236,235,230,0.25)',
}

export default function PipelinePage({ params }: { params: { id: string } }) {
  const [selected, setSelected] = useState<PipelineStage | null>(null)
  const { complete, total, pct } = pipelineProgress()

  return (
    <div style={{ padding: 32, display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 8 }}>
        <span style={{ font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.10em' }}>GSTACK PIPELINE</span>
        <h1 style={{ font: '900 30px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', display: 'inline' }}>
          ContractForge
        </h1>
        <Link href={`/app/products/${params.id}`} style={{ marginLeft: 'auto', font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.40)' }}>
          ← BACK TO PRODUCT
        </Link>
      </div>

      <div style={{ margin: '16px 0 24px' }}>
        <div style={{ font: '400 9px var(--font-mono)', color: 'rgba(164,216,255,0.60)', marginBottom: 8 }}>
          STAGE {complete + 1} / {total} · {pct}% COMPLETE
        </div>
        <div style={{ height: 2, background: 'rgba(164,216,255,0.15)' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: '#A4D8FF', boxShadow: '0 0 8px rgba(164,216,255,0.6)' }} />
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflowX: 'auto', gap: 0, alignItems: 'center', paddingBottom: 16 }}>
        {PIPELINE_STAGES.map((stage, i) => (
          <div key={stage.n} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
            <button
              onClick={() => setSelected(stage)}
              className="glass"
              style={{
                minWidth: 180, height: 280, borderRadius: 4, padding: 18, textAlign: 'left',
                display: 'flex', flexDirection: 'column', position: 'relative',
                borderTop: stage.gate ? '2px solid rgba(164,216,255,0.80)' : undefined,
              }}
            >
              <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.30)', marginBottom: 12 }}>
                {stage.n} / {total}
              </div>
              <div style={{ width: 40, height: 40, background: '#101316', border: '0.5px solid rgba(164,216,255,0.15)', display: 'grid', placeItems: 'center', font: '400 18px var(--font-mono)', color: '#A4D8FF', marginBottom: 14 }}>
                {stage.icon}
              </div>
              <div style={{ font: '700 19px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 10, lineHeight: 1.1 }}>
                {stage.name}
              </div>
              <p style={{ font: '300 10.5px var(--font-body)', color: 'rgba(236,235,230,0.40)', lineHeight: 1.5, flex: 1 }}>
                {stage.description}
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: STATUS_COLOR[stage.status], animation: stage.status === 'RUNNING' ? 'fg-pulse 2.4s ease-in-out infinite' : 'none' }} />
                <span style={{ font: '400 7px var(--font-mono)', color: STATUS_COLOR[stage.status], letterSpacing: '0.10em' }}>{stage.status}</span>
              </div>
              {stage.status === 'COMPLETE' && (
                <div style={{ position: 'absolute', bottom: 12, right: 12, width: 18, height: 18, borderRadius: '50%', border: '1px solid #A4D8FF', color: '#A4D8FF', display: 'grid', placeItems: 'center', font: '400 10px var(--font-mono)' }}>
                  ✓
                </div>
              )}
            </button>
            {i < PIPELINE_STAGES.length - 1 && (
              <div style={{ width: 36, height: 1, borderTop: '1px solid rgba(164,216,255,0.25)', position: 'relative', flexShrink: 0 }}>
                <span style={{ position: 'absolute', right: -4, top: -5, color: 'rgba(164,216,255,0.25)', fontSize: 10 }}>▸</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {selected && (
        <div
          onClick={() => setSelected(null)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(12,14,16,0.85)', backdropFilter: 'blur(4px)', zIndex: 400, display: 'grid', placeItems: 'center' }}
        >
          <div onClick={(e) => e.stopPropagation()} className="glass" style={{ width: 420, borderRadius: 6, padding: 32 }}>
            <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.30)', marginBottom: 10 }}>
              STAGE {selected.n} / {total}
            </div>
            <h2 style={{ font: '900 28px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 14 }}>
              {selected.name}
            </h2>
            <p style={{ font: '400 14px var(--font-body)', color: 'rgba(236,235,230,0.55)', lineHeight: 1.6, marginBottom: 20 }}>
              {selected.description}
            </p>
            {selected.status === 'COMPLETE' && (
              <div style={{ font: '400 10px var(--font-mono)', color: '#A4D8FF', marginBottom: 20 }}>
                output: {selected.name.toLowerCase().replace(/\s+/g, '_')}_v1.md · committed to repo
              </div>
            )}
            <button onClick={() => setSelected(null)} style={{ font: '400 9px var(--font-mono)', color: 'rgba(236,235,230,0.45)', letterSpacing: '0.10em' }}>
              ← CLOSE
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
