'use client'

import { motion } from 'framer-motion'

const products = [
  {
    name: 'ContractForge',
    meta: '14 days · ₹2,499/mo',
    link: { label: '↗ Live', href: 'https://contractforge.co.in' },
    opacity: 1,
  },
  {
    name: 'ClientForge',
    meta: 'Q3 2026',
    link: null,
    opacity: 0.4,
  },
  {
    name: 'OutreachForge',
    meta: 'Q4 2026',
    link: null,
    opacity: 0.22,
  },
]

export default function ProofBar() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      style={{
        background: 'var(--surf)',
        borderTop: '1px solid var(--bd)',
        borderBottom: '1px solid var(--bd)',
        position: 'relative',
        padding: '16px 40px 16px 48px',
        display: 'flex',
        alignItems: 'center',
        gap: '32px',
        flexWrap: 'wrap',
      }}
    >
      {/* 3px celadon left accent */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: '3px',
          background: 'var(--cel)',
        }}
      />

      <span className="label" style={{ flexShrink: 0 }}>
        Built by ForgeOS
      </span>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        {products.map((p) => (
          <div
            key={p.name}
            style={{
              opacity: p.opacity,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              border: '1px solid var(--bd2)',
              padding: '4px 10px',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '8.5px',
                color: 'var(--w)',
                fontWeight: 700,
              }}
            >
              {p.name}
            </span>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '8px',
                color: 'var(--m)',
              }}
            >
              {p.meta}
            </span>
            {p.link && (
              <a
                href={p.link.href}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '8px',
                  color: 'var(--cel)',
                }}
              >
                {p.link.label}
              </a>
            )}
          </div>
        ))}
      </div>
    </motion.section>
  )
}
