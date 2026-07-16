'use client'

import { useEffect, useRef } from 'react'

type Node = { x: number; y: number; vx: number; vy: number; r: number; o: number }

export function GlyphTide() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let w = 0
    let h = 0
    let nodes: Node[] = []

    function build() {
      const rect = wrap!.getBoundingClientRect()
      w = rect.width
      h = rect.height
      canvas!.width = w
      canvas!.height = h
      nodes = Array.from({ length: 80 }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        r: 2 + Math.random() * 2,
        o: 0.3 + Math.random() * 0.3,
      }))
    }

    build()
    window.addEventListener('resize', build)

    let raf: number | null = null
    function draw() {
      raf = requestAnimationFrame(draw)
      ctx!.clearRect(0, 0, w, h)
      for (const n of nodes) {
        if (!reduced) {
          n.x += n.vx
          n.y += n.vy
          if (n.x < 0) n.x = w
          if (n.x > w) n.x = 0
          if (n.y < 0) n.y = h
          if (n.y > h) n.y = 0
        }
        ctx!.beginPath()
        ctx!.arc(n.x, n.y, n.r, 0, Math.PI * 2)
        ctx!.fillStyle = `rgba(164,216,255,${n.o.toFixed(2)})`
        ctx!.fill()
      }
    }
    raf = requestAnimationFrame(draw)

    return () => {
      window.removeEventListener('resize', build)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div ref={wrapRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.55 }}>
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }} />
    </div>
  )
}
