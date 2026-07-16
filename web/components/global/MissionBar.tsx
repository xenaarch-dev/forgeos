'use client'

import { useEffect, useState } from 'react'
import { getIstTimeString } from '@/lib/forge/dates'

export function MissionBar({ chapter }: { chapter: string }) {
  const [time, setTime] = useState<string | null>(null)

  useEffect(() => {
    setTime(getIstTimeString())
    const id = setInterval(() => setTime(getIstTimeString()), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, height: 26, zIndex: 250,
        background: 'rgba(7,8,10,0.99)', borderBottom: '0.5px solid rgba(164,216,255,0.12)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 16px', font: '400 8.5px var(--font-mono)', letterSpacing: '0.14em',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#A4D8FF', animation: 'fg-pulse 2.4s ease-in-out infinite' }} />
        <span style={{ color: 'var(--warm-white)' }}>ALL SYSTEMS NOMINAL</span>
      </div>
      <div style={{ color: 'rgba(236,235,230,0.45)' }}>{time ?? '—:—:—'} IST</div>
      <div style={{ color: '#A4D8FF' }}>{chapter}</div>
    </div>
  )
}
