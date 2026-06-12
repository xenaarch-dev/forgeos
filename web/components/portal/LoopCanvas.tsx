'use client'

import { useEffect, useRef } from 'react'

/**
 * The Loop constellation — Canvas 2D, no Three.js.
 *
 * Forge core (gold, pulsing) orbited by the seven named agents. Dashed
 * bezier connections feed the core; sparks travel inward every 3–5s.
 * Orbit speed responds to scroll velocity; nodes lean toward the
 * cursor within 240px.
 *
 * Guards: IO-gated animation, DPR ≤ 1.5, RAF paused when
 * document.hidden, prefers-reduced-motion → single static frame,
 * clean dispose.
 */

type AgentNode = {
  name: string
  r: number
  speed: number // seconds per orbit
  color: string
  angle: number
  ox: number // cursor-lean offset
  oy: number
  nextSpark: number
  spark: number | null // 0→1 progress of travelling spark
}

const AGENTS: Omit<AgentNode, 'angle' | 'ox' | 'oy' | 'nextSpark' | 'spark'>[] = [
  { name: 'Maya', r: 150, speed: 20, color: '#2EF5C4' },
  { name: 'Aria', r: 190, speed: 26, color: '#7C3AED' },
  { name: 'Rex', r: 230, speed: 16, color: '#E8961F' },
  { name: 'Zen', r: 265, speed: 30, color: '#3B82F6' },
  { name: 'Marcus', r: 295, speed: 22, color: '#EF4444' },
  { name: 'Lexi', r: 320, speed: 28, color: '#2EF5C4' },
  { name: 'Kira', r: 340, speed: 18, color: '#7C3AED' },
]

export default function LoopCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5)

    let w = 0
    let h = 0
    let scale = 1
    const nodes: AgentNode[] = AGENTS.map((a) => ({
      ...a,
      angle: Math.random() * Math.PI * 2,
      ox: 0,
      oy: 0,
      nextSpark: performance.now() + 3000 + Math.random() * 2000,
      spark: null,
    }))

    const resize = () => {
      w = canvas.offsetWidth
      h = canvas.offsetHeight
      canvas.width = Math.max(1, w * dpr)
      canvas.height = Math.max(1, h * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      scale = Math.min(1, w / 760, h / 760)
    }
    resize()

    const mouse = { x: -9999, y: -9999 }
    const fine = window.matchMedia('(pointer: fine)').matches
    const onMove = (e: MouseEvent) => {
      const r = canvas.getBoundingClientRect()
      mouse.x = e.clientX - r.left
      mouse.y = e.clientY - r.top
    }
    if (fine && !reduced) {
      window.addEventListener('mousemove', onMove, { passive: true })
    }

    // scroll velocity → orbit speed multiplier
    let lastScrollY = window.scrollY
    let speedMult = 1
    let dashOffset = 0

    const draw = (now: number, dt: number) => {
      ctx.clearRect(0, 0, w, h)
      const cx = w / 2
      const cy = h / 2

      // core pulse — 2.4s ease-in-out
      const pulse = 1 + 0.12 * (0.5 - 0.5 * Math.cos((now / 2400) * Math.PI * 2))

      for (const n of nodes) {
        n.angle += ((Math.PI * 2) / (n.speed * 1000)) * dt * speedMult
        const baseX = cx + Math.cos(n.angle) * n.r * scale
        const baseY = cy + Math.sin(n.angle) * n.r * scale * 0.92

        // cursor attraction — lean within 240px
        const dxm = mouse.x - baseX
        const dym = mouse.y - baseY
        const dm = Math.hypot(dxm, dym)
        const tx = dm < 240 ? dxm * 0.07 : 0
        const ty = dm < 240 ? dym * 0.07 : 0
        n.ox += (tx - n.ox) * 0.1
        n.oy += (ty - n.oy) * 0.1
        const x = baseX + n.ox
        const y = baseY + n.oy

        // connection — dashed bezier feeding the core
        const mx = (x + cx) / 2 - (y - cy) * 0.18
        const my = (y + cy) / 2 + (x - cx) * 0.18
        ctx.save()
        ctx.strokeStyle = n.color
        ctx.globalAlpha = 0.18
        ctx.lineWidth = 1
        ctx.setLineDash([6, 10])
        ctx.lineDashOffset = dashOffset
        ctx.beginPath()
        ctx.moveTo(x, y)
        ctx.quadraticCurveTo(mx, my, cx, cy)
        ctx.stroke()
        ctx.restore()

        // spark travelling node → core
        if (n.spark === null && now >= n.nextSpark && !reduced) {
          n.spark = 0
        }
        if (n.spark !== null) {
          n.spark += dt / 900
          if (n.spark >= 1) {
            n.spark = null
            n.nextSpark = now + 3000 + Math.random() * 2000
          } else {
            const t = n.spark
            const sx = (1 - t) * (1 - t) * x + 2 * (1 - t) * t * mx + t * t * cx
            const sy = (1 - t) * (1 - t) * y + 2 * (1 - t) * t * my + t * t * cy
            ctx.save()
            ctx.shadowColor = n.color
            ctx.shadowBlur = 12
            ctx.fillStyle = n.color
            ctx.beginPath()
            ctx.arc(sx, sy, 2.5, 0, Math.PI * 2)
            ctx.fill()
            ctx.restore()
          }
        }

        // node + glow + label
        ctx.save()
        ctx.shadowColor = n.color
        ctx.shadowBlur = 24
        ctx.fillStyle = n.color
        ctx.beginPath()
        ctx.arc(x, y, 3.5, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()
        ctx.fillStyle = 'rgba(240,237,232,0.62)'
        ctx.font = '9px "Space Mono", monospace'
        ctx.fillText(n.name, x + 10, y + 3)
      }

      // forge core — drawn last, above connections
      const coreR = 7 * pulse
      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, 80)
      glow.addColorStop(0, 'rgba(232,150,31,0.18)')
      glow.addColorStop(1, 'transparent')
      ctx.fillStyle = glow
      ctx.beginPath()
      ctx.arc(cx, cy, 80, 0, Math.PI * 2)
      ctx.fill()
      ctx.save()
      ctx.shadowColor = '#E8961F'
      ctx.shadowBlur = 26
      ctx.fillStyle = '#E8961F'
      ctx.beginPath()
      ctx.arc(cx, cy, coreR, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    }

    if (reduced) {
      draw(0, 0)
      const onResize = () => {
        resize()
        draw(0, 0)
      }
      window.addEventListener('resize', onResize)
      return () => window.removeEventListener('resize', onResize)
    }

    let visible = false
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting
    })
    io.observe(canvas)

    let raf = 0
    let last = performance.now()
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick)
      const dt = Math.min(50, now - last)
      last = now
      if (!visible || document.hidden) return

      // scroll velocity impulse, decaying back to 1.0 at 0.04/frame
      const dy = Math.abs(window.scrollY - lastScrollY)
      lastScrollY = window.scrollY
      const impulse = Math.min(4, Math.max(0.5, 1 + dy * 0.04 * 0.6))
      if (impulse > speedMult) speedMult = impulse
      else speedMult += (1 - speedMult) * 0.04

      dashOffset -= 16 * (dt / 16.7)
      draw(now, dt)
    }
    raf = requestAnimationFrame(tick)

    let timer: ReturnType<typeof setTimeout>
    const onResize = () => {
      clearTimeout(timer)
      timer = setTimeout(resize, 200)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      io.disconnect()
      clearTimeout(timer)
      window.removeEventListener('resize', onResize)
      if (fine) window.removeEventListener('mousemove', onMove)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      role="img"
      aria-label="The Loop — seven ForgeOS agents orbiting the forge core, feeding it what they learned"
      className="mx-auto block h-[520px] w-full max-w-3xl md:h-[680px]"
    />
  )
}
