'use client'

import { useEffect, useRef } from 'react'

/**
 * PortalScene — Path B cosmic-garden backgrounds. Five Canvas 2D
 * scenes sharing one API with the (future) Path A images:
 *
 *   hero   — vast teal ring overhead, rising particle streams, garden
 *   field  — amber embers rising from dark earth, teal horizon
 *   agents — luminous machine interior: circuit beziers, violet core
 *   proof  — crystalline light nodes at parallax depths
 *   loop   — star field, orbital arcs, aurora through the canopy
 *
 * Guards (all mandatory): IO-gated RAF, DPR ≤ 1.5, paused when
 * document.hidden, prefers-reduced-motion → single static frame,
 * clean dispose. Every frame ends with a void vignette so text on
 * top stays readable.
 */

export type PortalVariant = 'hero' | 'field' | 'agents' | 'proof' | 'loop'

const TEAL = [0, 229, 204] as const
const GOLD = [232, 150, 31] as const
const VIOLET = [124, 58, 237] as const
const AZURE = [59, 130, 246] as const

const rgba = (c: readonly [number, number, number], a: number) =>
  `rgba(${c[0]},${c[1]},${c[2]},${a})`

const rand = (a: number, b: number) => a + Math.random() * (b - a)

type P = {
  x: number
  y: number
  r: number
  vy: number
  vx: number
  a: number
  c: readonly [number, number, number]
}

function makeRising(
  n: number,
  w: number,
  h: number,
  colors: { c: readonly [number, number, number]; weight: number }[],
  speed: [number, number],
  fromBottomThird = false
): P[] {
  const pick = () => {
    const t = Math.random()
    let acc = 0
    for (const { c, weight } of colors) {
      acc += weight
      if (t <= acc) return c
    }
    return colors[0].c
  }
  return Array.from({ length: n }, () => ({
    x: Math.random() * w,
    y: fromBottomThird ? h * (0.66 + Math.random() * 0.34) : Math.random() * h,
    r: rand(1, 3),
    vy: -rand(speed[0], speed[1]),
    vx: rand(-0.05, 0.05),
    a: rand(0.12, 0.5),
    c: pick(),
  }))
}

function vignette(ctx: CanvasRenderingContext2D, w: number, h: number) {
  const g = ctx.createRadialGradient(
    w / 2,
    h / 2,
    Math.min(w, h) * 0.25,
    w / 2,
    h / 2,
    Math.max(w, h) * 0.72
  )
  g.addColorStop(0, 'rgba(0,0,8,0)')
  g.addColorStop(1, 'rgba(0,0,8,0.62)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, w, h)
}

export default function PortalScene({
  variant,
  density = 1,
  className = '',
}: {
  variant: PortalVariant
  density?: number
  className?: string
}) {
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
    let parts: P[] = []
    let embers: P[] = []
    let stars: { x: number; y: number; r: number; ph: number }[] = []
    let circuits: { pts: number[][]; drift: number }[] = []

    const isMobile = () => w < 768
    const D = () => density * (isMobile() ? 0.45 : 1)

    const build = () => {
      w = canvas.offsetWidth
      h = canvas.offsetHeight
      canvas.width = Math.max(1, w * dpr)
      canvas.height = Math.max(1, h * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      if (variant === 'hero') {
        parts = makeRising(
          Math.round(600 * D()),
          w,
          h,
          [
            { c: TEAL, weight: 0.7 },
            { c: VIOLET, weight: 0.3 },
          ],
          [0.15, 0.55]
        )
        embers = makeRising(
          Math.round(200 * D()),
          w,
          h,
          [{ c: GOLD, weight: 1 }],
          [0.05, 0.2]
        )
      } else if (variant === 'field') {
        parts = makeRising(
          Math.round(800 * D()),
          w,
          h,
          [{ c: GOLD, weight: 1 }],
          [0.06, 0.28],
          true
        )
      } else if (variant === 'agents') {
        circuits = Array.from({ length: 14 }, (_, i) => {
          const y0 = (h / 14) * i + rand(-20, 20)
          const pts = [
            [rand(-80, 0), y0],
            [w * rand(0.2, 0.4), y0 + rand(-90, 90)],
            [w * rand(0.55, 0.75), y0 + rand(-90, 90)],
            [w + rand(0, 80), y0 + rand(-40, 40)],
          ]
          return { pts, drift: rand(0.04, 0.16) }
        })
      } else if (variant === 'proof') {
        // three parallax depth layers of light nodes
        parts = Array.from({ length: Math.round(70 * D()) }, (_, i) => ({
          x: Math.random() * w,
          y: Math.random() * h,
          r: rand(1, 3.5),
          vy: 0,
          vx: 0.03 + (i % 3) * 0.035, // depth layer → drift speed
          a: rand(0.15, 0.55),
          c: Math.random() > 0.4 ? TEAL : VIOLET,
        }))
      } else if (variant === 'loop') {
        stars = Array.from({ length: Math.round(300 * D()) }, () => ({
          x: Math.random() * w,
          y: Math.random() * h,
          r: rand(0.4, 1.4),
          ph: Math.random() * Math.PI * 2,
        }))
      }
    }
    build()

    const ringR = () => Math.min(280, w * 0.34)

    const draw = (t: number) => {
      ctx.clearRect(0, 0, w, h)

      if (variant === 'hero') {
        // garden simulation — layered dark-green mounds at the bottom
        const greens = ['#0B2B1A', '#07331F', '#0E241C', '#052015']
        greens.forEach((g, i) => {
          const gy = h - i * 26
          const grad = ctx.createRadialGradient(
            w * (0.18 + i * 0.22),
            gy + 120,
            10,
            w * (0.18 + i * 0.22),
            gy + 120,
            w * 0.42
          )
          grad.addColorStop(0, g + '26') // 0.15 alpha
          grad.addColorStop(1, 'transparent')
          ctx.fillStyle = grad
          ctx.fillRect(0, h * 0.6, w, h * 0.4)
        })

        // the lone figure's path glow
        const pathG = ctx.createLinearGradient(0, h, 0, h * 0.78)
        pathG.addColorStop(0, 'rgba(0,229,204,0.05)')
        pathG.addColorStop(1, 'transparent')
        ctx.fillStyle = pathG
        ctx.fillRect(0, h * 0.78, w, h * 0.22)

        // particles rise; the upper ones lean toward the ring
        const cx = w / 2
        const cy = h * 0.33
        for (const p of [...parts, ...embers]) {
          if (p.y < h * 0.55) {
            p.vx += ((cx - p.x) / w) * 0.004
          }
          p.x += p.vx
          p.y += p.vy
          if (p.y < -4) {
            p.y = h + 4
            p.x = Math.random() * w
            p.vx = rand(-0.05, 0.05)
          }
          ctx.fillStyle = rgba(p.c, p.a)
          ctx.fillRect(p.x, p.y, p.r, p.r)
        }

        // the vast luminous ring
        const r = ringR()
        ctx.save()
        ctx.shadowColor = rgba(TEAL, 0.9)
        ctx.shadowBlur = 40
        ctx.strokeStyle = rgba(TEAL, 0.75)
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.stroke()
        // slowly travelling bright arc
        const a0 = (t / 6000) % (Math.PI * 2)
        ctx.strokeStyle = rgba(TEAL, 0.95)
        ctx.lineWidth = 2.5
        ctx.beginPath()
        ctx.arc(cx, cy, r, a0, a0 + Math.PI / 3)
        ctx.stroke()
        ctx.restore()
        // inner haze
        const haze = ctx.createRadialGradient(cx, cy, r * 0.2, cx, cy, r)
        haze.addColorStop(0, 'rgba(0,229,204,0.05)')
        haze.addColorStop(1, 'transparent')
        ctx.fillStyle = haze
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.fill()
      }

      if (variant === 'field') {
        // teal horizon glow
        const hor = ctx.createLinearGradient(0, h, 0, h * 0.55)
        hor.addColorStop(0, 'rgba(0,229,204,0.10)')
        hor.addColorStop(1, 'transparent')
        ctx.fillStyle = hor
        ctx.fillRect(0, h * 0.55, w, h * 0.45)
        for (const p of parts) {
          p.x += p.vx
          p.y += p.vy
          if (p.y < -4) {
            p.y = h + 4
            p.x = Math.random() * w
          }
          ctx.fillStyle = rgba(p.c, p.a)
          ctx.fillRect(p.x, p.y, p.r, p.r)
        }
      }

      if (variant === 'agents') {
        // violet radial core
        const core = ctx.createRadialGradient(
          w / 2,
          h / 2,
          0,
          w / 2,
          h / 2,
          Math.min(w, h) * 0.55
        )
        const breathe = 0.1 + Math.sin(t / 2400) * 0.025
        core.addColorStop(0, rgba(VIOLET, breathe))
        core.addColorStop(1, 'transparent')
        ctx.fillStyle = core
        ctx.fillRect(0, 0, w, h)

        ctx.strokeStyle = rgba(TEAL, 0.2)
        ctx.lineWidth = 1
        for (const c of circuits) {
          const off = ((t * c.drift) / 16) % (w + 160)
          for (const shift of [0, -(w + 160)]) {
            const [p0, p1, p2, p3] = c.pts
            ctx.beginPath()
            ctx.moveTo(p0[0] + off + shift, p0[1])
            ctx.bezierCurveTo(
              p1[0] + off + shift,
              p1[1],
              p2[0] + off + shift,
              p2[1],
              p3[0] + off + shift,
              p3[1]
            )
            ctx.stroke()
            // junction node
            ctx.fillStyle = rgba(TEAL, 0.35)
            ctx.beginPath()
            ctx.arc(p2[0] + off + shift, p2[1], 1.6, 0, Math.PI * 2)
            ctx.fill()
          }
        }
      }

      if (variant === 'proof') {
        for (const p of parts) {
          p.x += p.vx
          if (p.x > w + 6) p.x = -6
          const tw = 0.7 + Math.sin(t / 1400 + p.y) * 0.3
          ctx.save()
          ctx.shadowColor = rgba(p.c, 0.8)
          ctx.shadowBlur = 8
          ctx.fillStyle = rgba(p.c, p.a * tw)
          ctx.beginPath()
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
          ctx.fill()
          ctx.restore()
        }
        // crystal geometry — slow-rotating stroked diamonds
        ctx.strokeStyle = rgba(TEAL, 0.15)
        ctx.lineWidth = 1
        const cs = [
          [w * 0.18, h * 0.3, 46],
          [w * 0.82, h * 0.24, 64],
          [w * 0.7, h * 0.74, 38],
        ]
        cs.forEach(([cx, cy, r], i) => {
          ctx.save()
          ctx.translate(cx, cy)
          ctx.rotate(t / 22000 + i)
          ctx.beginPath()
          ctx.moveTo(0, -r)
          ctx.lineTo(r * 0.62, 0)
          ctx.lineTo(0, r)
          ctx.lineTo(-r * 0.62, 0)
          ctx.closePath()
          ctx.stroke()
          ctx.restore()
        })
      }

      if (variant === 'loop') {
        // aurora through the canopy
        const au = ctx.createLinearGradient(0, 0, 0, h * 0.5)
        au.addColorStop(0, rgba(VIOLET, 0.08))
        au.addColorStop(0.6, rgba(TEAL, 0.05))
        au.addColorStop(1, 'transparent')
        ctx.fillStyle = au
        ctx.fillRect(0, 0, w, h * 0.5)
        // amber warmth from below
        const warm = ctx.createLinearGradient(0, h, 0, h * 0.7)
        warm.addColorStop(0, rgba(GOLD, 0.06))
        warm.addColorStop(1, 'transparent')
        ctx.fillStyle = warm
        ctx.fillRect(0, h * 0.7, w, h * 0.3)

        for (const s of stars) {
          const tw = 0.5 + Math.sin(t / 1800 + s.ph) * 0.5
          ctx.fillStyle = `rgba(240,237,232,${0.18 + tw * 0.35})`
          ctx.fillRect(s.x, s.y, s.r, s.r)
        }
        // 7 orbital arcs
        const cx = w / 2
        const cy = h * 0.46
        for (let i = 0; i < 7; i++) {
          const r = Math.min(w, h) * (0.16 + i * 0.055)
          const a0 = t / (9000 + i * 2600) + i * 1.7
          ctx.strokeStyle = rgba(i % 2 ? VIOLET : TEAL, 0.16)
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.arc(cx, cy, r, a0, a0 + Math.PI * rand(0.9, 0.9) + 0.9)
          ctx.stroke()
        }
      }

      vignette(ctx, w, h)
    }

    if (reduced) {
      draw(0)
      const onResize = () => {
        build()
        draw(0)
      }
      window.addEventListener('resize', onResize)
      return () => window.removeEventListener('resize', onResize)
    }

    let raf = 0
    let visible = true
    const io = new IntersectionObserver(
      ([e]) => {
        visible = e.isIntersecting
      },
      { rootMargin: '20% 0px 20% 0px' }
    )
    io.observe(canvas)

    const tick = (t: number) => {
      raf = requestAnimationFrame(tick)
      if (!visible || document.hidden) return
      draw(t)
    }
    raf = requestAnimationFrame(tick)

    let timer: ReturnType<typeof setTimeout>
    const onResize = () => {
      clearTimeout(timer)
      timer = setTimeout(build, 200)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      io.disconnect()
      clearTimeout(timer)
      window.removeEventListener('resize', onResize)
    }
  }, [variant, density])

  return (
    <canvas
      ref={canvasRef}
      role="img"
      aria-label={`Cosmic garden background — ${variant}`}
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
    />
  )
}
