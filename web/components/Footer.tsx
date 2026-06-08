'use client'

import { motion } from 'framer-motion'

export default function Footer() {
  return (
    <motion.footer
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      style={{
        padding: '28px 40px',
        borderTop: '1px solid var(--bd)',
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
      }}
    >
      {/* Left: large wordmark */}
      <div
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(44px, 9vw, 80px)',
          fontWeight: 300,
          color: 'var(--bd2)',
          lineHeight: 1,
          letterSpacing: '-0.01em',
        }}
      >
        FORGEOS
      </div>

      {/* Right: meta info */}
      <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <span
          style={{ fontFamily: 'var(--font-mono)', fontSize: '8.5px', color: 'var(--m)' }}
        >
          MIT License · 2026
        </span>
        <span
          style={{ fontFamily: 'var(--font-mono)', fontSize: '8.5px', color: 'var(--m)' }}
        >
          Built by @xenarch, Mumbai
        </span>
        <a
          href="https://github.com/xenaarch-dev/forgeos"
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontFamily: 'var(--font-mono)', fontSize: '8.5px', color: 'var(--cel)' }}
        >
          github.com/xenaarch-dev/forgeos
        </a>
      </div>
    </motion.footer>
  )
}
