'use client'

import { useEffect, useRef } from 'react'

type Node = { x: number; y: number; phase: number }

export function SignalBloom() {
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
    let arms: { cp1x: number; cp1y: number; cp2x: number; cp2y: number; ex: number; ey: number }[] = []
    let nodes: Node[] = []

    function build() {
      const rect = wrap!.getBoundingClientRect()
      w = rect.width
      h = rect.height
      canvas!.width = w
      canvas!.height = h

      const cx = w * 0.5
      const cy = h * 0.42
      arms = []
      nodes = []
      const ARM_COUNT = 40
      for (let i = 0; i < ARM_COUNT; i++) {
        const angle = (i / ARM_COUNT) * Math.PI * 2
        const length = w * (0.6 + Math.random() * 0.25)
        const ex = cx + Math.cos(angle) * length
        const ey = cy + Math.sin(angle) * length * 0.6
        const cp1x = cx + Math.cos(angle + 0.3) * length * 0.35
        const cp1y = cy + Math.sin(angle + 0.3) * length * 0.35
        const cp2x = cx + Math.cos(angle - 0.2) * length * 0.7
        const cp2y = cy + Math.sin(angle - 0.2) * length * 0.7
        arms.push({ cp1x, cp1y, cp2x, cp2y, ex, ey })
      }
      for (let i = 0; i < 120; i++) {
        const arm = arms[i % arms.length]
        const t = Math.random()
        const x = (1 - t) ** 3 * cx + 3 * (1 - t) ** 2 * t * arm.cp1x + 3 * (1 - t) * t ** 2 * arm.cp2x + t ** 3 * arm.ex
        const y = (1 - t) ** 3 * cy + 3 * (1 - t) ** 2 * t * arm.cp1y + 3 * (1 - t) * t ** 2 * arm.cp2y + t ** 3 * arm.ey
        nodes.push({ x, y, phase: Math.random() * Math.PI * 2 })
      }
    }

    build()
    const onResize = () => build()
    window.addEventListener('resize', onResize)

    let raf: number | null = null
    let lastFrame = 0

    function draw(now: number) {
      raf = requestAnimationFrame(draw)
      if (now - lastFrame < 33) return
      lastFrame = now
      ctx!.clearRect(0, 0, w, h)
      const cx = w * 0.5
      const cy = h * 0.42

      ctx!.strokeStyle = 'rgba(164,216,255,0.16)'
      ctx!.lineWidth = 1
      for (const arm of arms) {
        ctx!.beginPath()
        ctx!.moveTo(cx, cy)
        ctx!.bezierCurveTo(arm.cp1x, arm.cp1y, arm.cp2x, arm.cp2y, arm.ex, arm.ey)
        ctx!.stroke()
      }

      for (const node of nodes) {
        const pulse = reduced ? 1 : 0.5 + 0.5 * Math.sin(now / 2000 + node.phase)
        ctx!.beginPath()
        ctx!.arc(node.x, node.y, 1.5, 0, Math.PI * 2)
        ctx!.fillStyle = `rgba(164,216,255,${(0.25 + pulse * 0.4).toFixed(2)})`
        ctx!.fill()
      }
    }
    raf = requestAnimationFrame(draw)

    return () => {
      window.removeEventListener('resize', onResize)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div
      ref={wrapRef}
      style={{
        position: 'absolute', inset: 0, zIndex: 3, pointerEvents: 'none',
        opacity: 0, animation: 'fg-fadein 1.4s ease 1.3s forwards',
      }}
    >
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }} />
    </div>
  )
}
