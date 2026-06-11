'use client'

import { motion } from 'framer-motion'

const stats = [
  { label: 'Products shipped', value: '1' },
  { label: 'Forge agents',     value: '7' },
  { label: 'Build cost',       value: '$0.03' },
]

export default function GBrainStrip() {
  return (
    <motion.section
      id="gbrain"
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      className="grid grid-cols-2 md:grid-cols-4"
      style={{
        background: 'var(--surf)',
        borderTop: '1px solid var(--bd)',
        padding: '24px 40px',
        gap: '24px',
      }}
    >
      {/* GBrain patterns counter */}
      <div>
        <div
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 34,
            fontWeight: 400,
            color: 'var(--cel)',
            lineHeight: 1,
          }}
        >
          7
        </div>
        <div className="label" style={{ lineHeight: 1.7, marginTop: '6px' }}>
          GBrain patterns
        </div>
      </div>

      {stats.map((stat) => (
        <div key={stat.label}>
          <div
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 34,
              fontWeight: 400,
              color: 'var(--cel)',
              lineHeight: 1,
            }}
          >
            {stat.value}
          </div>
          <div className="label" style={{ lineHeight: 1.7, marginTop: '6px' }}>
            {stat.label}
          </div>
        </div>
      ))}
    </motion.section>
  )
}
