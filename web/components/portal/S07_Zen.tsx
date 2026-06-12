'use client'

import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import AgentChapter from '@/components/portal/AgentChapter'
import { zenCode, zenVerdict, type CodeTok } from '@/data/simulations'

const TOK_COLOR: Record<CodeTok['c'], string> = {
  k: '#00E5CC', // keywords — teal
  s: '#E8961F', // strings — gold
  n: '#E8961F', // numbers — gold
  d: '#E8961F', // decorator — gold
  f: '#F0EDE8', // function names — warm white
  p: '#F0EDE8', // plain — warm white
  m: 'rgba(240,237,232,0.5)', // punctuation — dim
}

/* Syntax-highlighted Python typing itself, then Nova's verdict. */
function CodeSim({ active }: { active: boolean }) {
  // absolute char offsets per token so we can slice the stream
  const { lines, total } = useMemo(() => {
    let off = 0
    const lines = zenCode.map((toks) =>
      toks.map((tok) => {
        const start = off
        off += tok.t.length
        return { ...tok, start }
      })
    )
    return { lines, total: off }
  }, [])

  const [count, setCount] = useState(0)
  const done = count >= total
  const [verdict, setVerdict] = useState(false)

  useEffect(() => {
    if (!active) {
      setCount(0)
      setVerdict(false)
      return
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setCount(total)
      return
    }
    let c = 0
    const iv = setInterval(() => {
      c += 2
      setCount(Math.min(c, total))
      if (c >= total) clearInterval(iv)
    }, 24)
    return () => clearInterval(iv)
  }, [active, total])

  useEffect(() => {
    if (!done) return
    const t = setTimeout(() => setVerdict(true), 450)
    return () => clearTimeout(t)
  }, [done])

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
          style={{ background: done ? 'var(--teal)' : 'var(--gold)' }}
        />
        api/contracts.py
      </div>

      <div className="overflow-x-auto px-4 py-4 text-[15px] leading-[1.85]">
        <pre style={{ fontFamily: 'var(--font-body)', margin: 0 }}>
          {lines.map((toks, li) => {
            const lineStart = toks[0]?.start ?? 0
            if (count <= lineStart) return null
            const lineEnd = toks.length
              ? toks[toks.length - 1].start + toks[toks.length - 1].t.length
              : lineStart
            const hasCaret = !done && count > lineStart && count <= lineEnd
            return (
              <div key={li} className="flex">
                <span
                  aria-hidden
                  className="w-7 shrink-0 select-none text-right"
                  style={{ color: 'rgba(240,237,232,0.22)', marginRight: 18 }}
                >
                  {li + 1}
                </span>
                <span className="whitespace-pre">
                  {toks.map((tok, ti) => {
                    const visible = Math.max(
                      0,
                      Math.min(tok.t.length, count - tok.start)
                    )
                    if (visible === 0) return null
                    return (
                      <span key={ti} style={{ color: TOK_COLOR[tok.c] }}>
                        {tok.t.slice(0, visible)}
                      </span>
                    )
                  })}
                  {hasCaret && (
                    <span
                      aria-hidden
                      className="inline-block h-[14px] w-[8px] align-middle"
                      style={{ background: 'rgba(240,237,232,0.6)' }}
                    />
                  )}
                </span>
              </div>
            )
          })}
        </pre>

        {verdict && (
          <motion.div
            className="mt-4 flex flex-wrap items-baseline justify-between gap-2 border-t pt-3 text-[12px]"
            style={{ borderColor: 'rgba(240,237,232,0.08)' }}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <span style={{ color: 'var(--teal)' }}>{zenVerdict.status}</span>
            <span style={{ color: 'var(--w-dim)' }}>{zenVerdict.credit}</span>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default function S07_Zen() {
  return (
    <AgentChapter
      eyebrow="// Zen → WorkerLoopAgent"
      name="Zen"
      role="He writes the code. Then rewrites it."
      glow="azure"
      tint="glass-cosmic"
    >
      {(active) => <CodeSim active={active} />}
    </AgentChapter>
  )
}
