'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'
import PortalScene from '@/components/portal/PortalScene'

const EASE = [0.22, 1, 0.36, 1] as const

const TASKS = [
  'architect the system',
  'write every line of code',
  'configure auth and RLS',
  'wire the payment webhooks',
  'run the security audit',
  'write the legal clauses',
  'deploy to production',
  'monitor uptime at 3am',
  'write the cold emails',
]

function TaskLine({
  text,
  onStruck,
  reduced,
}: {
  text: string
  onStruck: () => void
  reduced: boolean
}) {
  const ref = useRef<HTMLLIElement>(null)
  // fires when the line crosses ~60% of the viewport
  const inView = useInView(ref, { once: true, margin: '0px 0px -40% 0px' })
  const struck = reduced || inView

  useEffect(() => {
    if (struck) onStruck()
  }, [struck, onStruck])

  return (
    <li ref={ref} className="text-[20px] leading-loose">
      <span className="relative inline-block">
        <motion.span
          animate={{ color: struck ? 'rgba(240,237,232,0.55)' : '#F0EDE8' }}
          transition={{ duration: 0.5, ease: EASE }}
        >
          {text}
        </motion.span>
        <motion.span
          aria-hidden
          className="absolute left-0 top-1/2 h-px w-full"
          style={{ background: 'var(--teal)', transformOrigin: 'left' }}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: struck ? 1 : 0 }}
          transition={{ duration: 0.5, ease: EASE }}
        />
      </span>
    </li>
  )
}

function HumanCounter({
  allStruck,
  started,
}: {
  allStruck: boolean
  started: boolean
}) {
  const [hours, setHours] = useState(0)

  useEffect(() => {
    if (!started || allStruck) return
    const iv = setInterval(() => {
      setHours((h) => Math.min(h + 7, 347))
    }, 50)
    return () => clearInterval(iv)
  }, [started, allStruck])

  return (
    <motion.div
      className="glass glass-warm relative flex flex-col items-start gap-4 p-8 md:p-10"
      animate={
        allStruck
          ? {
              boxShadow: [
                '0 40px 100px rgba(0,0,5,0.7)',
                '0 0 56px rgba(0,229,204,0.45)',
                '0 40px 100px rgba(0,0,5,0.7)',
              ],
            }
          : undefined
      }
      transition={{ duration: 0.8, times: [0, 0.2, 1] }}
    >
      <span className="eyebrow" style={{ color: 'var(--w-dim)', fontSize: 11 }}>
        {allStruck ? 'time the machine needs' : 'time a human needs'}
      </span>
      {allStruck ? (
        // the hard cut — a power switch, no transition
        <span
          className="font-bold"
          style={{
            color: 'var(--teal)',
            fontSize: 'clamp(28px, 4.5vw, 46px)',
            letterSpacing: '0.04em',
            lineHeight: 1.1,
          }}
        >
          FORGEOS: 04:07:32
        </span>
      ) : (
        <span
          className="tabular-nums font-bold"
          style={{
            color: 'var(--w)',
            fontSize: 'clamp(44px, 6vw, 68px)',
            lineHeight: 1.05,
          }}
        >
          {String(Math.floor(hours)).padStart(3, '0')}
          <span style={{ fontSize: '0.4em', color: 'var(--w-dim)' }}> HRS</span>
        </span>
      )}
      <span className="text-[13px]" style={{ color: 'var(--w-dim)' }}>
        {allStruck ? 'idea → deployed product' : 'and counting'}
      </span>
    </motion.div>
  )
}

export default function S02_Problem() {
  const reduced = useReducedMotion() ?? false
  const [struckCount, setStruckCount] = useState(0)
  const counts = useRef(new Set<number>())

  const allStruck = struckCount >= TASKS.length

  return (
    <section
      id="problem"
      data-imagery
      className="relative flex min-h-screen items-center overflow-hidden py-32"
    >
      <PortalScene variant="field" />

      <div className="relative mx-auto w-full max-w-6xl px-6 md:px-10">
        <motion.p
          className="eyebrow mb-16"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '0px 0px -20% 0px' }}
          transition={{ duration: 0.8, ease: EASE }}
        >
          {'// 01 — the founder’s burden'}
        </motion.p>

        <div className="grid items-center gap-16 md:grid-cols-2">
          <ul className="flex list-none flex-col gap-2">
            {TASKS.map((t, i) => (
              <TaskLine
                key={t}
                text={t}
                reduced={reduced}
                onStruck={() => {
                  if (!counts.current.has(i)) {
                    counts.current.add(i)
                    setStruckCount(counts.current.size)
                  }
                }}
              />
            ))}
            <motion.li
              className="mt-8 text-lg font-bold"
              style={{ color: 'var(--gold)' }}
              initial={{ opacity: 0, y: 16 }}
              animate={allStruck ? { opacity: 1, y: 0 } : undefined}
              transition={{ duration: 0.9, ease: EASE, delay: 0.4 }}
            >
              decide.
            </motion.li>
          </ul>

          <div className="relative">
            <div
              aria-hidden
              className="glow-orb glow-gold"
              style={{
                width: 620,
                height: 620,
                top: '50%',
                left: '50%',
                transform: 'translate(-50%,-50%)',
              }}
            />
            <HumanCounter allStruck={allStruck} started={struckCount > 0} />
          </div>
        </div>
      </div>
    </section>
  )
}
