'use client'

import { useEffect, useRef } from 'react'

export function FilamentForge() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    function draw() {
      const rect = wrap!.getBoundingClientRect()
      const w = rect.width
      const h = rect.height
      canvas!.width = w
      canvas!.height = h
      ctx!.clearRect(0, 0, w, h)

      const fx = w * 0.03
      const fy = h * 0.5
      const LINE_COUNT = 60
      for (let i = 0; i < LINE_COUNT; i++) {
        const t = i / (LINE_COUNT - 1)
        const startY = h * t
        const opacity = 0.06 + Math.random() * 0.08
        ctx!.beginPath()
        ctx!.moveTo(w, startY)
        ctx!.quadraticCurveTo(w * 0.5, startY + (fy - startY) * 0.3, fx, fy)
        ctx!.strokeStyle = `rgba(164,216,255,${opacity.toFixed(2)})`
        ctx!.lineWidth = 1
        ctx!.stroke()
      }
    }

    draw()
    window.addEventListener('resize', draw)
    return () => window.removeEventListener('resize', draw)
  }, [])

  return (
    <div ref={wrapRef} style={{ position: 'absolute', left: 0, top: 0, width: '52%', height: '100%', pointerEvents: 'none' }}>
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }} />
    </div>
  )
}
