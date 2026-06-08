'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'

const agentData = [
  { name: 'Maya',   role: 'PMAgent',        color: '#3EB489', caps: ['Spec', 'Research', 'Scope'] },
  { name: 'Aria',   role: 'ArchitectAgent', color: '#3EB489', caps: ['ERD', 'API', 'Stack'] },
  { name: 'Rex',    role: 'ScaffoldAgent',  color: '#1D5FC5', caps: ['Scaffold', 'Templates'] },
  { name: 'Coder',  role: 'CoderAgent',     color: '#1D5FC5', caps: ['Code', 'Review'] },
  { name: 'Marcus', role: 'SecurityAgent',  color: '#D9832A', caps: ['Scan', 'Harden'] },
  { name: 'Kira',   role: 'DeployAgent',    color: '#D9832A', caps: ['Vercel', 'Render'] },
  { name: 'Nova',   role: 'EvalAgent',      color: '#1D5FC5', caps: ['QA', 'Tests'] },
  { name: 'GBrain', role: 'Memory',         color: '#E8E3D2', caps: ['Patterns', 'Learn'] },
]

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
}

export default function AgentGrid() {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      style={{ padding: '56px 40px' }}
    >
      <span className="label" style={{ display: 'block', marginBottom: '24px' }}>
        Forge agents
      </span>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        className="grid grid-cols-2 md:grid-cols-4"
        style={{ gap: '10px' }}
      >
        {agentData.map((agent, i) => (
          <motion.div
            key={agent.name}
            variants={itemVariants}
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
            style={{
              border: `1px solid ${hoveredIdx === i ? 'var(--bd2)' : 'var(--bd)'}`,
              background: 'var(--surf)',
              padding: '14px',
              transition: 'border-color 0.2s',
            }}
          >
            {/* Top row: stage number + dot */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '8px',
              }}
            >
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', color: 'var(--m)' }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              <div
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: agent.color,
                }}
              />
            </div>

            {/* Agent name */}
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                fontWeight: 700,
                color: agent.color,
                marginBottom: '2px',
              }}
            >
              {agent.name}
            </div>

            {/* Role */}
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '8.5px',
                color: 'var(--m)',
                textTransform: 'uppercase',
                letterSpacing: '0.10em',
                marginBottom: '8px',
              }}
            >
              {agent.role}
            </div>

            {/* Capability tags */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {agent.caps.map((cap) => (
                <span
                  key={cap}
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '7.5px',
                    color: 'var(--m)',
                    border: '1px solid var(--bd2)',
                    padding: '2px 6px',
                  }}
                >
                  {cap}
                </span>
              ))}
            </div>
          </motion.div>
        ))}
      </motion.div>
    </motion.section>
  )
}
