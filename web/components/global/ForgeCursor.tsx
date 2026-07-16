'use client'

import { useEffect, useRef } from 'react'

export function ForgeCursor() {
  const ringRef = useRef<HTMLDivElement>(null)
  const dotRef = useRef<HTMLDivElement>(null)
  const hLineRef = useRef<HTMLDivElement>(null)
  const vLineRef = useRef<HTMLDivElement>(null)
  const coordsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return

    let raf: number | null = null
    let magnetic = false

    const onMove = (e: MouseEvent) => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = null
        const { clientX: x, clientY: y } = e
        if (dotRef.current) dotRef.current.style.transform = `translate(${x - 2.5}px, ${y - 2.5}px)`
        if (ringRef.current) {
          const size = magnetic ? 52 : 34
          ringRef.current.style.width = `${size}px`
          ringRef.current.style.height = `${size}px`
          ringRef.current.style.transform = `translate(${x - size / 2}px, ${y - size / 2}px)`
        }
        if (hLineRef.current) hLineRef.current.style.transform = `translate(${x - 9}px, ${y - 0.5}px)`
        if (vLineRef.current) vLineRef.current.style.transform = `translate(${x - 0.5}px, ${y - 9}px)`
        if (coordsRef.current) {
          coordsRef.current.style.transform = `translate(${x + 14}px, ${y + 14}px)`
          coordsRef.current.textContent = `${x.toFixed(0)}, ${y.toFixed(0)}`
        }
      })
    }

    const onOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      magnetic = !!target.closest('[data-magnetic]')
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    window.addEventListener('mouseover', onOver, { passive: true })
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseover', onOver)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div className="forge-cursor-root" aria-hidden style={{ display: 'none' }}>
      <style>{`
        @media (pointer: fine) {
          .forge-cursor-root { display: block !important; }
        }
      `}</style>
      <div
        ref={ringRef}
        style={{
          position: 'fixed', top: 0, left: 0, width: 34, height: 34,
          borderRadius: '50%', border: '1px solid rgba(164,216,255,0.55)',
          zIndex: 2090, pointerEvents: 'none', transition: 'width 0.12s ease, height 0.12s ease',
        }}
      />
      <div
        ref={dotRef}
        style={{
          position: 'fixed', top: 0, left: 0, width: 5, height: 5,
          borderRadius: '50%', background: '#A4D8FF', zIndex: 2100, pointerEvents: 'none',
        }}
      />
      <div
        ref={hLineRef}
        style={{ position: 'fixed', top: 0, left: 0, width: 18, height: 1, background: 'rgba(164,216,255,0.50)', zIndex: 2089, pointerEvents: 'none' }}
      />
      <div
        ref={vLineRef}
        style={{ position: 'fixed', top: 0, left: 0, width: 1, height: 18, background: 'rgba(164,216,255,0.50)', zIndex: 2089, pointerEvents: 'none' }}
      />
      <div
        ref={coordsRef}
        style={{
          position: 'fixed', top: 0, left: 0, font: '400 8px var(--font-mono)',
          color: 'rgba(164,216,255,0.55)', zIndex: 2100, pointerEvents: 'none', whiteSpace: 'nowrap',
        }}
      />
    </div>
  )
}
