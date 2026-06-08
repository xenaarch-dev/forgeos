'use client'

import { useEffect, useRef } from 'react'

const AGENTS = [
  { name: 'MAYA',   role: 'PM',       color: '#3EB489' },
  { name: 'ARIA',   role: 'ARCH',     color: '#3EB489' },
  { name: 'REX',    role: 'SCAFFOLD', color: '#1D5FC5' },
  { name: 'KIRA',   role: 'DEPLOY',   color: '#D9832A' },
  { name: 'MARCUS', role: 'SECURITY', color: '#D9832A' },
  { name: 'NOVA',   role: 'EVAL',     color: '#1D5FC5' },
  { name: 'CODER',  role: 'CODE',     color: '#1D5FC5' },
]

function hexAlpha(hex: string, alpha: string): string {
  return hex + alpha
}

export default function AgentMesh() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId: number
    let t = 0

    const resize = () => {
      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }

    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    resize()

    type Point = { x: number; y: number }
    type Edge = { from: Point; to: Point; color: string }

    const draw = () => {
      const W = canvas.width
      const H = canvas.height

      if (W === 0 || H === 0) {
        t += 0.02
        animId = requestAnimationFrame(draw)
        return
      }

      const CX = W / 2
      const CY = H / 2
      const R = Math.min(W, H) * 0.36

      ctx.clearRect(0, 0, W, H)

      // 7 outer node positions
      const positions: Point[] = AGENTS.map((_, i) => {
        const angle = -Math.PI / 2 + (i / AGENTS.length) * Math.PI * 2
        return { x: CX + R * Math.cos(angle), y: CY + R * Math.sin(angle) }
      })
      const center: Point = { x: CX, y: CY }

      // Build edge list
      const edges: Edge[] = []

      // Ring: i → (i+1) % 7
      for (let i = 0; i < AGENTS.length; i++) {
        edges.push({
          from: positions[i],
          to: positions[(i + 1) % AGENTS.length],
          color: AGENTS[i].color,
        })
      }

      // Spokes: nodes 0, 2, 4, 6 → center
      ;[0, 2, 4, 6].forEach((i) => {
        edges.push({ from: positions[i], to: center, color: AGENTS[i].color })
      })

      const activeIdx = Math.floor(t) % edges.length
      const progress = (t * 1.3) % 1.0

      // Draw all edges
      edges.forEach((edge, idx) => {
        ctx.beginPath()
        ctx.moveTo(edge.from.x, edge.from.y)
        ctx.lineTo(edge.to.x, edge.to.y)
        if (idx === activeIdx) {
          ctx.strokeStyle = hexAlpha(edge.color, '80')
          ctx.lineWidth = 1.5
        } else {
          ctx.strokeStyle = 'rgba(28,46,34,0.9)'
          ctx.lineWidth = 0.5
        }
        ctx.stroke()
      })

      // Traveling dot on active edge
      const ae = edges[activeIdx]
      const dotX = ae.from.x + (ae.to.x - ae.from.x) * progress
      const dotY = ae.from.y + (ae.to.y - ae.from.y) * progress
      ctx.beginPath()
      ctx.arc(dotX, dotY, 2.5, 0, Math.PI * 2)
      ctx.fillStyle = '#3EB489'
      ctx.fill()

      // Draw outer nodes
      positions.forEach((pos, i) => {
        const agent = AGENTS[i]
        const glowR = 18 + Math.sin(t * 1.5 + i) * 3

        // Oscillating glow ring
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, glowR, 0, Math.PI * 2)
        ctx.fillStyle = hexAlpha(agent.color, '1A')
        ctx.fill()

        // Node body
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, 13, 0, Math.PI * 2)
        ctx.fillStyle = '#0D1810'
        ctx.fill()
        ctx.strokeStyle = agent.color
        ctx.lineWidth = 1
        ctx.stroke()

        // Labels
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.font = 'bold 6.5px "Space Mono", monospace'
        ctx.fillStyle = agent.color
        ctx.fillText(agent.name, pos.x, pos.y - 3.5)

        ctx.font = '5.5px "Space Mono", monospace'
        ctx.fillStyle = hexAlpha(agent.color, '99')
        ctx.fillText(agent.role, pos.x, pos.y + 5)
      })

      // GBrain center node
      const gbR = 20 + Math.sin(t * 1.2) * 2

      // Outer glow pulse
      ctx.beginPath()
      ctx.arc(CX, CY, gbR + 10, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(232,227,210,0.04)'
      ctx.fill()

      // Body
      ctx.beginPath()
      ctx.arc(CX, CY, gbR, 0, Math.PI * 2)
      ctx.fillStyle = '#142018'
      ctx.fill()
      ctx.strokeStyle = 'rgba(232,227,210,0.35)'
      ctx.lineWidth = 1
      ctx.stroke()

      // GBrain labels
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.font = 'bold 7px "Space Mono", monospace'
      ctx.fillStyle = '#E8E3D2'
      ctx.fillText('GBRAIN', CX, CY - 4)

      ctx.font = '5.5px "Space Mono", monospace'
      ctx.fillStyle = 'rgba(232,227,210,0.6)'
      ctx.fillText('MEMORY', CX, CY + 5)

      t += 0.02
      animId = requestAnimationFrame(draw)
    }

    animId = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(animId)
      ro.disconnect()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  )
}
