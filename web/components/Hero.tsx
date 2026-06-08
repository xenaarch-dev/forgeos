'use client'

import { motion } from 'framer-motion'
import AgentMesh from './AgentMesh'

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
}

const childVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
}

export default function Hero() {
  return (
    <section
      className="grid grid-cols-1 md:grid-cols-[1.1fr_0.9fr] items-center"
      style={{ gap: '32px', padding: '48px 40px' }}
    >
      {/* LEFT COLUMN */}
      <motion.div variants={containerVariants} initial="hidden" animate="show">
        {/* Badge */}
        <motion.div
          variants={childVariants}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '28px' }}
        >
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              backgroundColor: 'var(--cel)',
              flexShrink: 0,
              animation: 'dot-pulse 2s ease-in-out infinite',
            }}
          />
          <span className="label">Open source · MIT License · India-first</span>
        </motion.div>

        {/* H1 */}
        <motion.h1 variants={childVariants} style={{ marginBottom: '20px' }}>
          One sentence in.
          <br />
          <em style={{ color: 'var(--m)' }}>Full SaaS</em>{' '}
          <em style={{ color: 'var(--cel)' }}>out.</em>
        </motion.h1>

        {/* Descriptor */}
        <motion.p
          variants={childVariants}
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            textTransform: 'uppercase',
            color: 'var(--m)',
            lineHeight: 2.1,
            letterSpacing: '0.08em',
            marginBottom: '28px',
            whiteSpace: 'pre-line',
          }}
        >
          {'The AI product factory that builds, deploys,\nand operates complete software businesses\n— autonomously.'}
        </motion.p>

        {/* Proof pill */}
        <motion.div
          variants={childVariants}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '9px',
            border: '1px solid var(--bd2)',
            padding: '6px 12px',
            marginBottom: '24px',
          }}
        >
          <span
            style={{
              background: 'var(--cel-dim)',
              color: 'var(--cel)',
              fontFamily: 'var(--font-mono)',
              fontSize: '8px',
              fontWeight: 700,
              padding: '2px 6px',
              letterSpacing: '0.15em',
              animation: 'live-pulse 2s ease-in-out infinite',
            }}
          >
            LIVE
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--m)' }}>
            ContractForge is live —{' '}
            <a
              href="https://contractforge.co.in"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--cel)' }}
            >
              contractforge.co.in ↗
            </a>
          </span>
        </motion.div>

        {/* CTA row */}
        <motion.div
          variants={childVariants}
          style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}
        >
          {/* Install block */}
          <div
            style={{
              border: '1px solid var(--bd2)',
              padding: '8px 14px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--m)' }}>
              $
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--cel)' }}>
              pip install forgeos
            </span>
          </div>

          {/* Start building button */}
          <button
            style={{
              background: 'var(--cel)',
              color: 'var(--bg)',
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              fontWeight: 700,
              padding: '8px 16px',
              letterSpacing: '0.10em',
            }}
          >
            Start building →
          </button>

          {/* Docs ghost */}
          <a
            href="#"
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              color: 'var(--m)',
              letterSpacing: '0.10em',
            }}
          >
            Docs ↗
          </a>
        </motion.div>
      </motion.div>

      {/* RIGHT COLUMN — AgentMesh canvas */}
      <div className="mt-8 md:mt-0 min-h-[280px] md:min-h-[360px]">
        <AgentMesh />
      </div>
    </section>
  )
}
