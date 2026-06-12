'use client'

import { motion } from 'framer-motion'
import PortalScene from '@/components/portal/PortalScene'
import LoopCanvas from '@/components/portal/LoopCanvas'

const EASE = [0.22, 1, 0.36, 1] as const

export default function S12_Loop() {
  return (
    <section
      id="loop"
      data-imagery
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden py-32"
    >
      <PortalScene variant="loop" />

      <div className="relative w-full max-w-4xl px-6 md:px-10">
        <motion.p
          className="eyebrow"
          initial={{ opacity: 0, x: -28 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: '0px 0px -15% 0px' }}
          transition={{ duration: 0.8, ease: EASE }}
        >
          {'// 04 — the machine thinks'}
        </motion.p>

        <div className="mt-5 overflow-hidden">
          <motion.h2
            className="type-chapter"
            initial={{ y: '105%' }}
            whileInView={{ y: 0 }}
            viewport={{ once: true, margin: '0px 0px -15% 0px' }}
            transition={{ duration: 0.9, ease: EASE }}
          >
            Every night at 02:00 IST,
            <br />
            it reads everything.
          </motion.h2>
        </div>

        <motion.p
          className="mt-6 text-[18px]"
          style={{ color: 'var(--w-dim)', maxWidth: '52ch' }}
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '0px 0px -15% 0px' }}
          transition={{ duration: 0.8, delay: 0.2, ease: EASE }}
        >
          Agent logs. Payments. Emails. Commits. A Nightly Reasoning Agent
          finds the patterns and rewrites the rules. Every product it ships
          makes the next one better.
        </motion.p>
      </div>

      <motion.div
        className="relative mt-12 w-full px-6"
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '0px 0px -10% 0px' }}
        transition={{ duration: 1, delay: 0.15, ease: EASE }}
      >
        <div
          aria-hidden
          className="glow-orb glow-gold"
          style={{
            width: 560,
            height: 560,
            top: '50%',
            left: '50%',
            transform: 'translate(-50%,-50%)',
          }}
        />
        <LoopCanvas />
      </motion.div>
    </section>
  )
}
