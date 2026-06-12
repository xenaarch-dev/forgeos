'use client'

import { ReactNode, useEffect, useRef, useState } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'
import Glow from '@/components/fx/Glow'

const EASE = [0.22, 1, 0.36, 1] as const

/* ------------------------------------------------------------------
   LensPanel — the one glass recipe, with the water-lens cursor wipe.

   The wrapper paints the glass tint + border + shadow. The blur lives
   on an inner overlay whose mask is punched out in a ~140px circle at
   the (lerped) cursor position — the cursor literally wipes the glass
   clear where it touches, like a finger on fogged glass. Content sits
   above the overlay so text stays sharp. Touch devices and reduced
   motion get the plain static glass.
   ------------------------------------------------------------------ */
export function LensPanel({ children }: { children: ReactNode }) {
  const panelRef = useRef<HTMLDivElement>(null)
  const lensRef = useRef<HTMLDivElement>(null)
  const [lensEnabled, setLensEnabled] = useState(false)

  useEffect(() => {
    const fine = window.matchMedia('(pointer: fine)').matches
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!fine || reduced) return
    setLensEnabled(true)

    const panel = panelRef.current
    const lens = lensRef.current
    if (!panel || !lens) return

    const OFF = -400
    const cur = { x: OFF, y: OFF }
    const target = { x: OFF, y: OFF }
    let raf = 0
    let running = false

    const apply = () => {
      const m = `radial-gradient(circle 140px at ${cur.x}px ${cur.y}px, transparent 0px, transparent 52px, black 132px)`
      lens.style.maskImage = m
      lens.style.webkitMaskImage = m
    }

    const tick = () => {
      // spring-smooth follow — lerp 0.12
      cur.x += (target.x - cur.x) * 0.12
      cur.y += (target.y - cur.y) * 0.12
      apply()
      const settled =
        Math.abs(target.x - cur.x) < 0.5 && Math.abs(target.y - cur.y) < 0.5
      if (settled && target.x === OFF) {
        running = false
        return
      }
      raf = requestAnimationFrame(tick)
    }

    const start = () => {
      if (!running) {
        running = true
        raf = requestAnimationFrame(tick)
      }
    }
    const onMove = (e: MouseEvent) => {
      const r = panel.getBoundingClientRect()
      target.x = e.clientX - r.left
      target.y = e.clientY - r.top
      start()
    }
    const onLeave = () => {
      target.x = OFF
      target.y = OFF
      start()
    }
    panel.addEventListener('mousemove', onMove, { passive: true })
    panel.addEventListener('mouseleave', onLeave)
    return () => {
      cancelAnimationFrame(raf)
      panel.removeEventListener('mousemove', onMove)
      panel.removeEventListener('mouseleave', onLeave)
    }
  }, [])

  return (
    <div
      ref={panelRef}
      className="relative overflow-hidden rounded-2xl"
      style={{
        background: 'var(--glass)',
        border: '1px solid var(--glass-border)',
        borderTopColor: 'var(--glass-highlight)',
        boxShadow:
          '0 24px 64px rgba(0,0,0,0.45), inset 0 1px 0 var(--glass-highlight)',
      }}
    >
      <div
        ref={lensRef}
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          backdropFilter: 'blur(24px) saturate(1.2)',
          WebkitBackdropFilter: 'blur(24px) saturate(1.2)',
          // until JS enables the lens, mask is absent → uniform glass
          maskImage: lensEnabled ? undefined : 'none',
        }}
      />
      <div className="relative z-10">{children}</div>
    </div>
  )
}

/* ------------------------------------------------------------------
   AgentChapter — identical scaffold for all seven agents.
   Simulation plays when the panel is ≥50% in viewport, pauses when
   out, replays on re-entry (the render-prop receives `active`).
   ------------------------------------------------------------------ */
export default function AgentChapter({
  id,
  eyebrow,
  name,
  role,
  glow,
  heavy = false,
  caption,
  children,
}: {
  id?: string
  eyebrow: string
  name: string
  role: string
  glow: 'fire' | 'cel'
  /** Lexi gets ~10% more visual weight */
  heavy?: boolean
  caption?: string
  children: (active: boolean) => ReactNode
}) {
  const reduced = useReducedMotion() ?? false
  const panelWrapRef = useRef<HTMLDivElement>(null)
  const inView = useInView(panelWrapRef, { amount: 0.5 })
  const active = reduced || inView

  const glowColor =
    glow === 'fire' ? 'rgba(217,131,42,0.10)' : 'rgba(62,180,137,0.09)'
  const maxW = heavy ? 'max-w-[62rem]' : 'max-w-4xl'

  return (
    <section
      id={id}
      className={`relative flex min-h-screen flex-col items-center justify-center overflow-hidden ${
        heavy ? 'py-40' : 'py-32'
      }`}
    >
      <div className={`w-full ${maxW} px-6 md:px-10`}>
        <motion.p
          className="eyebrow"
          style={{ color: 'var(--cel)' }}
          initial={{ opacity: 0, x: -28 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: '0px 0px -15% 0px' }}
          transition={{ duration: 0.8, ease: EASE }}
        >
          {eyebrow}
        </motion.p>

        <div className="mt-5 overflow-hidden">
          <motion.h2
            className="type-chapter"
            initial={{ y: '105%' }}
            whileInView={{ y: 0 }}
            viewport={{ once: true, margin: '0px 0px -15% 0px' }}
            transition={{ duration: 0.9, ease: EASE }}
          >
            {name}
          </motion.h2>
        </div>

        <motion.p
          className="mt-4 text-base"
          style={{ color: 'var(--w-dim)' }}
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '0px 0px -15% 0px' }}
          transition={{ duration: 0.8, delay: 0.2, ease: EASE }}
        >
          {role}
        </motion.p>
      </div>

      <div
        ref={panelWrapRef}
        className={`relative mt-14 w-full ${maxW} px-6 md:px-10`}
      >
        <Glow
          color={glowColor}
          size={heavy ? 640 : 560}
          style={{
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
          }}
        />
        <motion.div
          initial={{ opacity: 0, y: 80 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '0px 0px -10% 0px' }}
          transition={{ duration: 1, delay: 0.15, ease: EASE }}
        >
          <LensPanel>{children(active)}</LensPanel>
        </motion.div>
        {caption && (
          <motion.p
            className="mt-6 text-center text-[13px]"
            style={{ color: 'var(--w-dim)' }}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.5, ease: EASE }}
          >
            {caption}
          </motion.p>
        )}
      </div>
    </section>
  )
}
