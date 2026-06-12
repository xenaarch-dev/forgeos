'use client'

import { CSSProperties, useEffect, useRef } from 'react'

/**
 * PortalScene — the Act II imagery layer (Path B: generative scenes).
 *
 * Each variant is a layered composition built to the same art direction
 * as the Higgsfield image briefs — deep #060D08 base, celadon + ember
 * light sources, cream highlights — so real generated assets can be
 * swapped in later behind this identical API:
 *
 *   <PortalScene variant="hero | field | garden | loop" />
 *
 * Layer stack (bottom → top): gradient volumes → SVG/div light
 * structures → canvas particle field → #060D08 vignette (contrast
 * lock, heavier at edges) → photographic grain.
 *
 * Guards (v1 pattern): IO-gated RAF · DPR ≤ 1.5 · paused when hidden
 * or off-screen · reduced-motion renders one static frame · the
 * 'loop' variant is fully static (Phase 5's canvas piece lives above it).
 */

export type PortalVariant = 'hero' | 'field' | 'garden' | 'loop'

const CEL = '62,180,137'
const FIRE = '217,131,42'
const CREAM = '232,227,210'

const HORIZON = 0.64 // field variant — horizon line as fraction of height

/* tiny inline turbulence tile — kills banding, adds long-exposure grain */
const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.55'/%3E%3C/svg%3E\")"

const vignetteStyle: CSSProperties = {
  position: 'absolute',
  inset: 0,
  background: `radial-gradient(ellipse 120% 90% at 50% 45%, rgba(6,13,8,0.38) 0%, rgba(6,13,8,0.50) 55%, rgba(6,13,8,0.74) 100%),
    linear-gradient(180deg, rgba(6,13,8,0.62) 0%, rgba(6,13,8,0.18) 28%, rgba(6,13,8,0.18) 66%, rgba(6,13,8,0.72) 100%)`,
}

const grainStyle: CSSProperties = {
  position: 'absolute',
  inset: 0,
  backgroundImage: GRAIN,
  opacity: 0.05,
  mixBlendMode: 'overlay',
}

/* ------------------------------------------------------------------ */
/* Structural layers per variant — pure CSS/SVG, zero JS               */
/* ------------------------------------------------------------------ */

function HeroLayers() {
  return (
    <>
      {/* volumetric haze */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(ellipse 80% 55% at 50% 60%, rgba(${FIRE},0.10) 0%, transparent 62%),
            radial-gradient(ellipse 55% 38% at 16% 28%, rgba(${CEL},0.05) 0%, transparent 65%),
            radial-gradient(ellipse 55% 38% at 86% 22%, rgba(${CEL},0.04) 0%, transparent 65%)`,
        }}
      />
      {/* vaulted architecture dissolving into the star field */}
      <svg
        viewBox="0 0 1000 620"
        preserveAspectRatio="xMidYMin slice"
        style={{
          position: 'absolute',
          insetInline: 0,
          top: 0,
          width: '100%',
          height: '64%',
          maskImage: 'linear-gradient(to top, black 30%, transparent 96%)',
          WebkitMaskImage: 'linear-gradient(to top, black 30%, transparent 96%)',
        }}
      >
        {[0, 1, 2, 3].map((i) => (
          <path
            key={`rib${i}`}
            d={`M ${-80 - i * 30} 620 Q 500 ${-150 + i * 95} ${1080 + i * 30} 620`}
            fill="none"
            stroke={`rgba(${CREAM},${0.085 - i * 0.018})`}
            strokeWidth={1}
          />
        ))}
        {[140, 320, 680, 860].map((x, i) => (
          <line
            key={`col${i}`}
            x1={x}
            y1={620}
            x2={500 + (x - 500) * 0.55}
            y2={120}
            stroke={`rgba(${CREAM},0.045)`}
            strokeWidth={1}
          />
        ))}
      </svg>
      {/* the colossal portal ring */}
      <div
        data-portal-ring
        style={{
          position: 'absolute',
          left: '50%',
          top: '56%',
          width: 'min(58vw, 640px)',
          aspectRatio: '1 / 1',
          transform: 'translate(-50%, -50%) scaleY(0.97)',
          borderRadius: '50%',
          border: `1.5px solid rgba(${FIRE},0.8)`,
          boxShadow: `0 0 24px 4px rgba(${FIRE},0.45),
            0 0 90px 28px rgba(${FIRE},0.26),
            0 0 220px 90px rgba(${FIRE},0.11),
            inset 0 0 60px 14px rgba(${FIRE},0.16)`,
        }}
      />
      {/* light catching the ring's lower rim */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '56%',
          width: 'min(58vw, 640px)',
          aspectRatio: '1 / 1',
          transform: 'translate(-50%, -50%) scaleY(0.97)',
          borderRadius: '50%',
          border: '2px solid transparent',
          borderBottomColor: `rgba(${CREAM},0.55)`,
          filter: 'blur(3px)',
        }}
      />
      {/* forge-floor reflection */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '80%',
          transform: 'translateX(-50%)',
          width: '74%',
          height: '20%',
          background: `radial-gradient(ellipse 50% 46% at 50% 50%, rgba(${FIRE},0.10), transparent 72%)`,
          filter: 'blur(10px)',
        }}
      />
    </>
  )
}

function FieldLayers() {
  return (
    <>
      {/* ground falling away below the horizon */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(180deg, transparent ${HORIZON * 100 - 2}%, rgba(2,5,3,0.55) ${HORIZON * 100 + 10}%, rgba(2,5,3,0.8) 100%)`,
        }}
      />
      {/* celadon horizon glow */}
      <div
        style={{
          position: 'absolute',
          insetInline: 0,
          top: `${HORIZON * 100 - 9}%`,
          height: '18%',
          background: `radial-gradient(ellipse 75% 52% at 50% 50%, rgba(${CEL},0.16), transparent 72%)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          insetInline: '6%',
          top: `${HORIZON * 100}%`,
          height: 1,
          background: `linear-gradient(90deg, transparent, rgba(${CEL},0.45) 30%, rgba(${CEL},0.45) 70%, transparent)`,
        }}
      />
      {/* faint ember warmth low in the field */}
      <div
        style={{
          position: 'absolute',
          insetInline: 0,
          top: `${HORIZON * 100}%`,
          bottom: 0,
          background: `radial-gradient(ellipse 60% 80% at 50% 100%, rgba(${FIRE},0.07), transparent 70%)`,
        }}
      />
    </>
  )
}

function GardenLayers() {
  /* bokeh discs — macro depth of field */
  const bokeh: Array<[number, number, number, string, number]> = [
    // [x%, y%, size, color, alpha]
    [12, 22, 150, FIRE, 0.1],
    [85, 16, 110, CEL, 0.08],
    [78, 74, 190, FIRE, 0.09],
    [8, 78, 120, CEL, 0.07],
    [55, 8, 80, CREAM, 0.05],
    [38, 88, 90, FIRE, 0.07],
  ]
  return (
    <>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(ellipse 70% 60% at 50% 80%, rgba(${CEL},0.06) 0%, transparent 65%)`,
        }}
      />
      {bokeh.map(([x, y, s, c, a], i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${x}%`,
            top: `${y}%`,
            width: s,
            height: s,
            transform: 'translate(-50%, -50%)',
            borderRadius: '50%',
            background: `radial-gradient(circle, rgba(${c},${a}) 0%, transparent 70%)`,
            filter: 'blur(18px)',
          }}
        />
      ))}
      {/* stems growing through machinery — abstract botanical strokes */}
      <svg
        viewBox="0 0 1000 800"
        preserveAspectRatio="xMidYMax slice"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      >
        {/* machinery: great riveted wheel arcs at the edges */}
        <circle
          cx={-60}
          cy={820}
          r={340}
          fill="none"
          stroke={`rgba(${CREAM},0.06)`}
          strokeWidth={1.5}
          strokeDasharray="3 14"
        />
        <circle cx={-60} cy={820} r={290} fill="none" stroke={`rgba(${CREAM},0.045)`} strokeWidth={1} />
        <circle
          cx={1075}
          cy={860}
          r={400}
          fill="none"
          stroke={`rgba(${CREAM},0.055)`}
          strokeWidth={1.5}
          strokeDasharray="3 16"
        />
        <circle cx={1075} cy={860} r={345} fill="none" stroke={`rgba(${CREAM},0.04)`} strokeWidth={1} />
        {/* stems */}
        {(
          [
            ['M 180 800 Q 150 560 255 430', 0.085],
            ['M 240 800 Q 280 600 235 500', 0.06],
            ['M 760 800 Q 820 580 720 440', 0.08],
            ['M 845 800 Q 870 660 800 560', 0.055],
            ['M 510 800 Q 470 680 530 600', 0.05],
          ] as Array<[string, number]>
        ).map(([d, a], i) => (
          <path key={`stem${i}`} d={d} fill="none" stroke={`rgba(${CREAM},${a})`} strokeWidth={1.5} />
        ))}
        {/* ember blooms at the stem tips */}
        {(
          [
            [255, 430, 5],
            [235, 500, 3.5],
            [720, 440, 5.5],
            [800, 560, 3.5],
            [530, 600, 3],
          ] as Array<[number, number, number]>
        ).map(([x, y, r], i) => (
          <g key={`bloom${i}`}>
            <circle cx={x} cy={y} r={r * 3.4} fill={`rgba(${FIRE},0.12)`} />
            <circle cx={x} cy={y} r={r} fill={`rgba(${FIRE},0.85)`} />
          </g>
        ))}
        {/* bioluminescent celadon accents */}
        {(
          [
            [310, 520, 2], [205, 620, 1.6], [680, 540, 2.2], [770, 650, 1.5],
            [450, 700, 1.8], [565, 660, 1.4], [880, 480, 1.8],
          ] as Array<[number, number, number]>
        ).map(([x, y, r], i) => (
          <g key={`acc${i}`}>
            <circle cx={x} cy={y} r={r * 3} fill={`rgba(${CEL},0.14)`} />
            <circle cx={x} cy={y} r={r} fill={`rgba(${CEL},0.8)`} />
          </g>
        ))}
      </svg>
    </>
  )
}

function LoopLayers() {
  return (
    <>
      {/* the ember core's halo */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '46%',
          width: 'min(48vw, 560px)',
          aspectRatio: '1 / 1',
          transform: 'translate(-50%, -50%)',
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(${FIRE},0.16) 0%, rgba(${FIRE},0.05) 38%, transparent 68%)`,
        }}
      />
      {/* long-exposure orbital traces */}
      <svg
        viewBox="0 0 1000 900"
        preserveAspectRatio="xMidYMid slice"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      >
        {[170, 215, 265, 320].map((r, i) => (
          <circle
            key={`trace${i}`}
            cx={500}
            cy={414}
            r={r}
            fill="none"
            stroke={`rgba(${CREAM},${0.075 - i * 0.014})`}
            strokeWidth={1}
            strokeDasharray={i % 2 ? '2 11' : undefined}
          />
        ))}
        {/* brighter celadon exposure arcs — partial sweeps */}
        <circle
          cx={500}
          cy={414}
          r={240}
          fill="none"
          stroke={`rgba(${CEL},0.16)`}
          strokeWidth={1.2}
          strokeDasharray="200 1500"
          strokeDashoffset={-180}
          strokeLinecap="round"
        />
        <circle
          cx={500}
          cy={414}
          r={190}
          fill="none"
          stroke={`rgba(${CEL},0.12)`}
          strokeWidth={1}
          strokeDasharray="140 1200"
          strokeDashoffset={-700}
          strokeLinecap="round"
        />
        {/* distant static light points on the traces */}
        {(
          [
            [500 + 215, 414, 1.6], [500 - 250, 330, 1.3], [380, 414 + 290, 1.5],
            [690, 250, 1.2], [260, 520, 1.4], [745, 600, 1.2],
          ] as Array<[number, number, number]>
        ).map(([x, y, r], i) => (
          <circle key={`pt${i}`} cx={x} cy={y} r={r} fill={`rgba(${FIRE},0.5)`} />
        ))}
      </svg>
    </>
  )
}

/* ------------------------------------------------------------------ */
/* Canvas particle field — hero / field / garden                       */
/* ------------------------------------------------------------------ */

type Particle = {
  kind: 'streak' | 'ember' | 'mote'
  x: number
  y: number
  vx: number
  vy: number
  r: number
  len: number
  a: number
  tw: number
  c: string
}

type Star = { x: number; y: number; r: number; a: number; c: string }

const rand = (a: number, b: number) => a + Math.random() * (b - a)

function SceneField({ variant }: { variant: Exclude<PortalVariant, 'loop'> }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const fine = window.matchMedia('(pointer: fine)').matches
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5)

    let w = 0
    let h = 0
    let stars: Star[] = []
    let parts: Particle[] = []

    const spawn = (initial: boolean): Particle => {
      if (variant === 'hero') {
        const ember = Math.random() < 0.2
        if (ember) {
          return {
            kind: 'ember', x: rand(0, w), y: initial ? rand(0, h) : h + 4,
            vx: 0, vy: -rand(0.04, 0.14), r: rand(1, 2), len: 0,
            a: rand(0.12, 0.3), tw: rand(0, Math.PI * 2), c: FIRE,
          }
        }
        return {
          kind: 'streak', x: rand(0, w), y: initial ? rand(0, h) : h + 12,
          vx: 0, vy: -rand(0.3, 0.85), r: 1, len: rand(6, 14),
          a: rand(0.1, 0.26), tw: 0, c: CEL,
        }
      }
      if (variant === 'field') {
        return {
          kind: 'ember', x: rand(0, w), y: initial ? rand(h * HORIZON, h) : h + 3,
          vx: rand(-0.02, 0.02), vy: -rand(0.08, 0.3), r: rand(0.8, 1.8), len: 0,
          a: rand(0.1, 0.3), tw: rand(0, Math.PI * 2), c: FIRE,
        }
      }
      return {
        kind: 'mote', x: rand(0, w), y: rand(0, h),
        vx: rand(-0.05, 0.05), vy: rand(-0.06, 0.02), r: rand(0.6, 1.4), len: 0,
        a: rand(0.06, 0.16), tw: rand(0, Math.PI * 2),
        c: Math.random() < 0.5 ? CEL : CREAM,
      }
    }

    const init = () => {
      w = canvas.offsetWidth
      h = canvas.offsetHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      const mobile = w < 768
      stars = []
      if (variant === 'hero') {
        const n = mobile ? 70 : 120
        for (let i = 0; i < n; i++) {
          stars.push({
            x: rand(0, w), y: rand(0, h * 0.66), r: rand(0.4, 1.5),
            a: rand(0.04, 0.32), c: Math.random() < 0.12 ? CEL : CREAM,
          })
        }
      } else if (variant === 'field') {
        const n = mobile ? 55 : 95
        for (let i = 0; i < n; i++) {
          stars.push({
            x: rand(0, w), y: rand(0, h * (HORIZON - 0.04)), r: rand(0.4, 1.4),
            a: rand(0.05, 0.35), c: Math.random() < 0.1 ? CEL : CREAM,
          })
        }
      }

      const counts: Record<typeof variant, [number, number]> = {
        hero: [64, 36],
        field: [110, 64],
        garden: [26, 14],
      }
      const n = mobile ? counts[variant][1] : counts[variant][0]
      parts = Array.from({ length: n }, () => spawn(true))
    }

    const mouse = { x: -9999, y: -9999 }
    const onMove = (e: MouseEvent) => {
      const r = canvas.getBoundingClientRect()
      mouse.x = e.clientX - r.left
      mouse.y = e.clientY - r.top
    }

    const drawFrame = (t: number) => {
      ctx.clearRect(0, 0, w, h)
      for (const s of stars) {
        ctx.fillStyle = `rgba(${s.c},${s.a})`
        ctx.fillRect(s.x, s.y, s.r, s.r)
      }
      for (const p of parts) {
        let alpha = p.a
        if (p.kind === 'ember' || p.kind === 'mote') {
          alpha = p.a * (0.72 + 0.28 * Math.sin(t * 0.002 + p.tw))
        }
        if (variant === 'field') {
          // embers dim as they climb away from the ground
          const env = Math.min(Math.max((p.y - h * 0.3) / (h * 0.34), 0), 1)
          alpha *= env
        }
        ctx.fillStyle = `rgba(${p.c},${alpha.toFixed(3)})`
        if (p.kind === 'streak') {
          ctx.fillRect(p.x, p.y, 1, p.len)
        } else {
          ctx.fillRect(p.x, p.y, p.r, p.r)
        }
      }
    }

    const step = (t: number) => {
      const cx = w * 0.5
      for (let i = 0; i < parts.length; i++) {
        const p = parts[i]
        if (variant === 'hero') {
          if (p.kind === 'streak') {
            // streams converge gently on the portal as they rise
            p.vx += (cx - p.x) * 0.0000028 * (1 - p.y / h) * h
            p.vx *= 0.92
          }
          if (fine) {
            const dx = p.x - mouse.x
            const dy = p.y - mouse.y
            const d = Math.hypot(dx, dy)
            if (d < 100 && d > 0.01) {
              const f = ((100 - d) / 100) * 0.4
              p.vx += (dx / d) * f
              p.vy += (dy / d) * f * 0.25
            }
          }
          p.vy = Math.min(p.vy * 0.985, -0.04)
        }
        p.x += p.vx
        p.y += p.vy
        const gone =
          variant === 'garden'
            ? false
            : p.y < (variant === 'field' ? h * 0.28 : -16)
        if (gone) {
          parts[i] = spawn(false)
          continue
        }
        if (variant === 'garden') {
          if (p.x < -4) p.x = w + 4
          if (p.x > w + 4) p.x = -4
          if (p.y < -4) p.y = h + 4
          if (p.y > h + 4) p.y = -4
        } else {
          if (p.x < -6) p.x = w + 6
          if (p.x > w + 6) p.x = -6
        }
      }
      drawFrame(t)
    }

    init()

    if (reduced) {
      // one static frame — the scene as a photograph
      drawFrame(0)
      return
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
      step(t)
    }
    raf = requestAnimationFrame(tick)

    if (variant === 'hero' && fine) {
      window.addEventListener('mousemove', onMove, { passive: true })
    }

    let timer: ReturnType<typeof setTimeout>
    const onResize = () => {
      clearTimeout(timer)
      timer = setTimeout(init, 200)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      io.disconnect()
      clearTimeout(timer)
      window.removeEventListener('resize', onResize)
      if (variant === 'hero' && fine) window.removeEventListener('mousemove', onMove)
    }
  }, [variant])

  return (
    <canvas ref={canvasRef} aria-hidden className="absolute inset-0 h-full w-full" />
  )
}

/* ------------------------------------------------------------------ */

export default function PortalScene({
  variant,
  className = '',
}: {
  variant: PortalVariant
  className?: string
}) {
  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
    >
      {variant === 'hero' && <HeroLayers />}
      {variant === 'field' && <FieldLayers />}
      {variant === 'garden' && <GardenLayers />}
      {variant === 'loop' && <LoopLayers />}
      {variant !== 'loop' && <SceneField variant={variant} />}
      {/* contrast lock — the palette holds even if a real asset lands here */}
      <div style={vignetteStyle} />
      <div style={grainStyle} />
    </div>
  )
}
