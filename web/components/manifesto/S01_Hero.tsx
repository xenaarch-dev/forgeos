'use client'

import { useEffect, useRef, useState } from 'react'
import {
  motion,
  useMotionTemplate,
  useReducedMotion,
  useScroll,
  useTransform,
} from 'framer-motion'
import Ember from '@/components/fx/Ember'

const EASE = [0.22, 1, 0.36, 1] as const
const LINE1 = 'One sentence in.'
const LINE2 = 'Full SaaS out.'

/* ------------------------------------------------------------------
   Forge sparks — 40-60 canvas particles drifting upward, pushed
   gently away by the cursor. DPR capped 1.5, paused when hidden.
   ------------------------------------------------------------------ */
function Sparks() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = Math.min(window.devicePixelRatio || 1, 1.5)
    let w = 0
    let h = 0
    const resize = () => {
      w = canvas.offsetWidth
      h = canvas.offsetHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()

    const count = w < 768 ? 40 : 56
    const parts = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: 1 + Math.random(),
      vy: -(0.08 + Math.random() * 0.18),
      vx: 0,
      drift: (Math.random() - 0.5) * 0.04,
      a: 0.1 + Math.random() * 0.1,
    }))

    const mouse = { x: -9999, y: -9999 }
    const fine = window.matchMedia('(pointer: fine)').matches
    const onMove = (e: MouseEvent) => {
      const r = canvas.getBoundingClientRect()
      mouse.x = e.clientX - r.left
      mouse.y = e.clientY - r.top
    }
    if (fine) window.addEventListener('mousemove', onMove, { passive: true })

    let raf = 0
    let visible = true
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting
    })
    io.observe(canvas)

    const tick = () => {
      raf = requestAnimationFrame(tick)
      if (!visible || document.hidden) return
      ctx.clearRect(0, 0, w, h)
      for (const p of parts) {
        // cursor repulsion — gentle push within 110px
        const dx = p.x - mouse.x
        const dy = p.y - mouse.y
        const d = Math.hypot(dx, dy)
        if (d < 110 && d > 0.01) {
          const f = ((110 - d) / 110) * 0.5
          p.vx += (dx / d) * f
          p.vy += (dy / d) * f * 0.3
        }
        p.vx = p.vx * 0.92 + p.drift
        p.vy = Math.min(p.vy * 0.98, -0.06)
        p.x += p.vx
        p.y += p.vy
        if (p.y < -4) {
          p.y = h + 4
          p.x = Math.random() * w
        }
        if (p.x < -4) p.x = w + 4
        if (p.x > w + 4) p.x = -4
        ctx.fillStyle = `rgba(62,180,137,${p.a})`
        ctx.fillRect(p.x, p.y, p.r, p.r)
      }
    }
    tick()

    const onResize = () => resize()
    window.addEventListener('resize', onResize)
    return () => {
      cancelAnimationFrame(raf)
      io.disconnect()
      window.removeEventListener('resize', onResize)
      if (fine) window.removeEventListener('mousemove', onMove)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="absolute inset-0 h-full w-full"
    />
  )
}

export default function S01_Hero() {
  const reduced = useReducedMotion()
  const [c1, setC1] = useState(0)
  const [c2, setC2] = useState(0)
  const [typingDone, setTypingDone] = useState(false)

  // letter-by-letter typewriter: line 1 → 600ms pause → line 2
  useEffect(() => {
    if (reduced) {
      setC1(LINE1.length)
      setC2(LINE2.length)
      setTypingDone(true)
      return
    }
    const timers: ReturnType<typeof setTimeout>[] = []
    let i1 = 0
    let i2 = 0
    const t0 = setTimeout(() => {
      const iv1 = setInterval(() => {
        i1 += 1
        setC1(i1)
        if (i1 >= LINE1.length) {
          clearInterval(iv1)
          const tp = setTimeout(() => {
            const iv2 = setInterval(() => {
              i2 += 1
              setC2(i2)
              if (i2 >= LINE2.length) {
                clearInterval(iv2)
                setTypingDone(true)
              }
            }, 42)
            timers.push(iv2 as unknown as ReturnType<typeof setTimeout>)
          }, 600)
          timers.push(tp)
        }
      }, 42)
      timers.push(iv1 as unknown as ReturnType<typeof setTimeout>)
    }, 1400)
    timers.push(t0)
    return () => timers.forEach((t) => clearTimeout(t))
  }, [reduced])

  // scroll depth-of-field handoff — past ~10vh the hero recedes
  const { scrollY } = useScroll()
  const scale = useTransform(scrollY, [80, 640], [1, 0.92])
  const blurV = useTransform(scrollY, [80, 640], [0, 5])
  const filter = useMotionTemplate`blur(${blurV}px)`

  return (
    <section
      id="top"
      className="relative flex h-[100svh] flex-col items-center justify-center overflow-hidden"
      style={{ background: 'var(--bg)' }}
    >
      <Sparks />

      <motion.div
        className="relative flex flex-col items-center px-6 text-center"
        style={reduced ? undefined : { scale, filter }}
      >
        <motion.h1
          className="type-hero"
          initial={{ opacity: 0, filter: 'blur(12px)' }}
          animate={{ opacity: 1, filter: 'blur(0px)' }}
          transition={{ duration: 1.2, ease: EASE }}
        >
          Forge.
        </motion.h1>

        <p
          className="mt-8 flex h-7 items-baseline text-lg"
          style={{ color: 'var(--w)', letterSpacing: '0.02em' }}
          aria-label={`${LINE1} ${LINE2}`}
        >
          <span aria-hidden>
            {LINE1.slice(0, c1)}
            {c1 >= LINE1.length && <span className="inline-block w-3" />}
            {LINE2.slice(0, c2)}
          </span>
          {!typingDone && !reduced && (
            <motion.span
              aria-hidden
              className="ml-1 inline-block h-[18px] w-[9px] self-center"
              style={{ background: 'rgba(232,227,210,0.7)' }}
              animate={{ opacity: [1, 0, 1] }}
              transition={{ duration: 0.9, repeat: Infinity }}
            />
          )}
          {typingDone && (
            <motion.span
              className="ml-3 self-center"
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, ease: EASE }}
            >
              <Ember />
            </motion.span>
          )}
        </p>
      </motion.div>

      {/* scroll cue */}
      <motion.div
        className="absolute bottom-8 left-1/2 flex -translate-x-1/2 flex-col items-center gap-3"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: reduced ? 0 : 3.4, duration: 1, ease: EASE }}
      >
        <span
          className="text-[11px] uppercase"
          style={{ color: 'var(--w-dim)', letterSpacing: '0.3em' }}
        >
          scroll
        </span>
        <div className="h-12 w-px overflow-hidden">
          <motion.div
            className="h-full w-px"
            style={{ background: 'var(--w)', transformOrigin: 'top' }}
            animate={
              reduced
                ? { scaleY: 1 }
                : { scaleY: [0, 1, 1], opacity: [1, 1, 0] }
            }
            transition={{
              duration: 2.2,
              times: [0, 0.65, 1],
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        </div>
      </motion.div>
    </section>
  )
}
