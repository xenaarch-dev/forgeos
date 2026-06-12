'use client'

import { useEffect, useState } from 'react'
import {
  motion,
  useMotionTemplate,
  useReducedMotion,
  useScroll,
  useTransform,
} from 'framer-motion'
import Ember from '@/components/fx/Ember'
import PortalScene from '@/components/fx/PortalScene'
import HUD from '@/components/fx/HUD'

const EASE = [0.22, 1, 0.36, 1] as const
const LINE1 = 'One sentence in.'
const LINE2 = 'Full SaaS out.'

const HERO_NOTES = [
  { label: 'FORGE CORE // ONLINE', x: 64, y: 32, depth: 0 as const },
  { label: 'PIPELINE 18 STAGES', x: 15, y: 57, depth: 1 as const },
  { label: 'DAY 157 — MUMBAI', x: 81, y: 73, side: 'left' as const, depth: 2 as const },
]

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
      <PortalScene variant="hero" />
      <HUD notes={HERO_NOTES} />

      <motion.div
        className="relative z-10 flex flex-col items-center px-6 text-center"
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
        className="absolute bottom-8 left-1/2 z-10 flex -translate-x-1/2 flex-col items-center gap-3"
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
