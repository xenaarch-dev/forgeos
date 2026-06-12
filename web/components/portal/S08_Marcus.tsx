'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import AgentChapter from '@/components/portal/AgentChapter'
import { marcusMatrix } from '@/data/simulations'

const EASE = [0.22, 1, 0.36, 1] as const

/* One matrix row: slides in, scans ⚠ amber, resolves ✓ teal. */
function Row({
  label,
  holdMs,
  appearMs,
  active,
}: {
  label: string
  holdMs: number
  appearMs: number
  active: boolean
}) {
  const [state, setState] = useState<'hidden' | 'scanning' | 'ok'>('hidden')

  useEffect(() => {
    if (!active) {
      setState('hidden')
      return
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setState('ok')
      return
    }
    const t1 = setTimeout(() => setState('scanning'), appearMs)
    const t2 = setTimeout(() => setState('ok'), appearMs + holdMs)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [active, appearMs, holdMs])

  if (state === 'hidden') return null
  return (
    <motion.div
      className="flex items-baseline justify-between gap-4 text-[15px]"
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.45, ease: EASE }}
    >
      <span className="whitespace-pre" style={{ color: 'var(--w)' }}>
        {label}
      </span>
      {state === 'scanning' ? (
        <motion.span
          className="shrink-0 font-bold"
          style={{ color: 'var(--gold)' }}
          animate={{ opacity: [1, 0.35, 1] }}
          transition={{ duration: 0.7, repeat: Infinity }}
        >
          ⚠
        </motion.span>
      ) : (
        <motion.span
          className="shrink-0 font-bold"
          style={{ color: 'var(--teal)' }}
          initial={{ scale: 0.4 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.35, ease: EASE }}
        >
          ✓
        </motion.span>
      )}
    </motion.div>
  )
}

function MatrixSim({ active }: { active: boolean }) {
  return (
    <div className="w-full">
      <div
        className="flex items-center gap-2 border-b px-4 py-2.5 text-[11px]"
        style={{
          borderColor: 'rgba(240,237,232,0.08)',
          color: 'var(--w-dim)',
          letterSpacing: '0.12em',
        }}
      >
        <span
          aria-hidden
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: 'var(--gold)' }}
        />
        marcus@forgeos — threat matrix
      </div>
      <div className="flex flex-col gap-3 overflow-x-auto px-4 py-6 md:px-7">
        {marcusMatrix.map((r, i) => (
          <Row
            key={r.label}
            label={r.label}
            holdMs={r.holdMs}
            appearMs={350 + i * 320}
            active={active}
          />
        ))}
      </div>
    </div>
  )
}

export default function S08_Marcus() {
  return (
    <AgentChapter
      eyebrow="// Marcus → SecurityAgent"
      name="Marcus"
      role="He attacks it before anyone else can."
      glow="red"
    >
      {(active) => <MatrixSim active={active} />}
    </AgentChapter>
  )
}
