// web/components/app-shell/BotAvatar.tsx
'use client'

import { useEffect, useRef } from 'react'

export function BotAvatar({ accent, size = 30, label }: { accent: string; size?: number; label?: string }) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!window.matchMedia('(pointer:fine)').matches) return
    const svg = svgRef.current
    if (!svg) return
    let raf: number | null = null
    const onMove = (e: MouseEvent) => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = null
        const r = svg.getBoundingClientRect()
        const dx = e.clientX - (r.left + r.width / 2)
        const dy = e.clientY - (r.top + r.height / 2)
        const d = Math.hypot(dx, dy) || 1
        const m = Math.min(2.4, d / 40)
        svg.querySelectorAll('[data-pupil]').forEach((p) => {
          p.setAttribute('transform', `translate(${((dx / d) * m).toFixed(1)},${((dy / d) * m).toFixed(1)})`)
        })
      })
    }
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [])

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <svg ref={svgRef} viewBox="0 0 64 64" width={size} height={size} style={{ flexShrink: 0, overflow: 'visible' }}>
        <line x1="32" y1="9" x2="32" y2="17" stroke={accent} strokeWidth="2" />
        <circle cx="32" cy="7" r="2.8" fill={accent} />
        <rect x="13" y="17" width="38" height="31" rx="11" fill={`${accent}18`} stroke={accent} strokeWidth="1.5" />
        <g>
          <circle cx="25" cy="33" r="5.2" fill="var(--void)" stroke={accent} strokeWidth="1" />
          <circle cx="39" cy="33" r="5.2" fill="var(--void)" stroke={accent} strokeWidth="1" />
          <circle data-pupil cx="25" cy="33" r="2.3" fill={accent} />
          <circle data-pupil cx="39" cy="33" r="2.3" fill={accent} />
        </g>
        <path d="M28 42.5 Q32 45.5 36 42.5" stroke={accent} strokeWidth="1.6" fill="none" strokeLinecap="round" />
      </svg>
      {label && (
        <span style={{ font: '400 10.5px var(--font-body)', color: 'var(--w)' }}>{label}</span>
      )}
    </div>
  )
}
