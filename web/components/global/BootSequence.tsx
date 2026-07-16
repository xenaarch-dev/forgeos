'use client'

import { useEffect, useState } from 'react'
import { getDayNumber } from '@/lib/forge/dates'

export function BootSequence() {
  const [visible, setVisible] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    if (sessionStorage.getItem('forgeos-booted')) return
    setVisible(true)
    sessionStorage.setItem('forgeos-booted', '1')
    const t = setTimeout(() => setVisible(false), 1900)
    return () => clearTimeout(t)
  }, [])

  if (!mounted || !visible) return null

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 3000, background: '#0C0E10',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        animation: 'boot-out 1.9s ease forwards',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ font: '900 30px var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6' }}>
          ForgeOS
        </div>
        <div style={{ position: 'relative', width: 200, height: 1, margin: '18px auto 0', background: 'rgba(164,216,255,0.15)' }}>
          <div
            style={{
              position: 'absolute', top: 0, left: 0, height: 1, background: '#A4D8FF',
              boxShadow: '0 0 8px rgba(164,216,255,0.6)', animation: 'boot-line 1.2s ease forwards',
            }}
          />
        </div>
        <div style={{ marginTop: 14, font: '400 9px var(--font-mono)', letterSpacing: '0.14em', color: 'rgba(164,216,255,0.50)' }}>
          INITIALIZING AGENT MESH · DAY {getDayNumber()}
        </div>
      </div>
    </div>
  )
}
