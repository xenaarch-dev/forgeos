'use client'

import { motion } from 'framer-motion'
import AgentChapter from '@/components/portal/AgentChapter'
import { lexiClauses, lexiAnnotation } from '@/data/simulations'

const EASE = [0.22, 1, 0.36, 1] as const

/* Contract clauses assembling on paper — the one light surface on the page. */
function ClausesSim({ active }: { active: boolean }) {
  return (
    <div className="relative flex flex-col gap-6 p-6 md:flex-row md:gap-8 md:p-10">
      {/* the paper — warm sheet under glass */}
      <div
        className="relative flex-1 px-7 py-8 md:px-10 md:py-10"
        style={{
          background: 'var(--w)',
          borderRadius: 10,
          boxShadow: '0 12px 40px rgba(0,0,0,0.35)',
        }}
      >
        <div
          className="mb-7 text-[10px] font-bold uppercase"
          style={{
            color: 'rgba(18,32,23,0.45)',
            letterSpacing: '0.22em',
            fontFamily: 'var(--font-body)',
          }}
        >
          Service Agreement — ContractForge
        </div>
        <div className="flex flex-col gap-4">
          {lexiClauses.map((clause, i) => (
            <motion.p
              key={clause}
              style={{
                fontFamily: 'var(--font-serif)',
                fontWeight: 500,
                fontSize: 'clamp(15px, 2vw, 19px)',
                lineHeight: 1.55,
                color: '#15241B',
              }}
              initial={{ opacity: 0, y: 10 }}
              animate={active ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
              transition={{ duration: 0.7, delay: 0.3 + i * 0.45, ease: EASE }}
            >
              {clause}
            </motion.p>
          ))}
        </div>
      </div>

      {/* margin annotation */}
      <motion.div
        className="shrink-0 md:w-36 md:pt-16"
        initial={{ opacity: 0 }}
        animate={active ? { opacity: 1 } : { opacity: 0 }}
        transition={{
          duration: 0.8,
          delay: 0.3 + lexiClauses.length * 0.45 + 0.4,
          ease: EASE,
        }}
      >
        <span
          aria-hidden
          className="mb-2 block h-px w-8"
          style={{ background: 'var(--gold)' }}
        />
        <p
          className="text-[11px] leading-relaxed"
          style={{
            color: 'var(--gold)',
            letterSpacing: '0.08em',
            fontFamily: 'var(--font-body)',
          }}
        >
          {lexiAnnotation}
        </p>
      </motion.div>
    </div>
  )
}

export default function S09_Lexi() {
  return (
    <AgentChapter
      eyebrow="// Lexi → LegalAgent"
      name="Lexi"
      role="She knows Indian law. By design."
      glow="teal"
      tint="glass-cosmic"
    >
      {(active) => <ClausesSim active={active} />}
    </AgentChapter>
  )
}
