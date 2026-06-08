'use client'

import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'

type StageState = 'done' | 'running' | 'pending'
type Stage = { name: string; state: StageState }

const initialStages: Stage[] = [
  { name: 'PM',       state: 'done' },
  { name: 'Spec',     state: 'done' },
  { name: 'Arch',     state: 'done' },
  { name: 'Design',   state: 'running' },
  { name: 'Scaffold', state: 'pending' },
  { name: 'Code',     state: 'pending' },
  { name: 'Test',     state: 'pending' },
  { name: 'QA',       state: 'pending' },
  { name: 'Security', state: 'pending' },
  { name: 'Legal',    state: 'pending' },
  { name: 'Deploy',   state: 'pending' },
  { name: 'Launch',   state: 'pending' },
]

function connectorColor(curr: StageState, next: StageState): string {
  if (curr === 'done' && next === 'done') return 'var(--cel)'
  if (curr === 'done' && next === 'running')
    return 'linear-gradient(90deg, var(--cel), var(--fire))'
  return 'var(--bd)'
}

export default function Pipeline() {
  const [stages, setStages] = useState<Stage[]>(initialStages)

  useEffect(() => {
    const interval = setInterval(() => {
      setStages((prev) => {
        const runningIdx = prev.findIndex((s) => s.state === 'running')
        if (runningIdx === -1) return prev
        const next = [...prev]
        next[runningIdx] = { ...next[runningIdx], state: 'done' }
        const nextPending = next.findIndex((s) => s.state === 'pending')
        if (nextPending !== -1) {
          next[nextPending] = { ...next[nextPending], state: 'running' }
        }
        return next
      })
    }, 2400)
    return () => clearInterval(interval)
  }, [])

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      style={{ padding: '40px 0' }}
    >
      <div style={{ padding: '0 40px', marginBottom: '20px' }}>
        <span className="label">18-stage pipeline — one idea, one deployed URL</span>
      </div>

      <div
        className="no-scrollbar"
        style={{
          overflowX: 'auto',
          display: 'flex',
          alignItems: 'center',
          padding: '0 40px 16px',
        }}
      >
        {stages.map((stage, i) => (
          <div key={stage.name} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
            <div
              style={{
                padding: '8px 14px',
                border: `1px solid ${
                  stage.state === 'done'
                    ? 'var(--cel)'
                    : stage.state === 'running'
                    ? 'var(--fire)'
                    : 'var(--bd2)'
                }`,
                background:
                  stage.state === 'done'
                    ? 'var(--cel-dim)'
                    : stage.state === 'running'
                    ? 'var(--fire-dim)'
                    : 'var(--surf)',
                color:
                  stage.state === 'done'
                    ? 'var(--cel)'
                    : stage.state === 'running'
                    ? 'var(--fire)'
                    : 'var(--m)',
                fontFamily: 'var(--font-mono)',
                fontSize: '9px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.15em',
                whiteSpace: 'nowrap',
                animation:
                  stage.state === 'running'
                    ? 'running-pulse 1.5s ease-in-out infinite'
                    : 'none',
                transition: 'all 0.3s ease',
              }}
            >
              {stage.name}
            </div>

            {i < stages.length - 1 && (
              <div
                style={{
                  width: '24px',
                  height: '1px',
                  flexShrink: 0,
                  background: connectorColor(stage.state, stages[i + 1].state),
                  transition: 'background 0.3s ease',
                }}
              />
            )}
          </div>
        ))}
      </div>
    </motion.section>
  )
}
