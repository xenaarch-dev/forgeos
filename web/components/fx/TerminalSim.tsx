'use client'

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import type { TermLine } from '@/data/simulations'

const TONE_COLOR: Record<TermLine['tone'], string> = {
  cmd: '#E8E3D2',
  ok: '#3EB489',
  info: 'rgba(232,227,210,0.72)',
}

/**
 * Terminal output — lines appended with realistic variable timing,
 * auto-scroll, blinking block cursor while running. Replays when
 * `active` flips back to true.
 */
export default function TerminalSim({
  lines,
  active,
  title,
}: {
  lines: TermLine[]
  active: boolean
  title: string
}) {
  const [shown, setShown] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  const running = active && shown < lines.length

  useEffect(() => {
    if (!active) {
      setShown(0)
      return
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setShown(lines.length)
      return
    }
    let i = 0
    let t: ReturnType<typeof setTimeout>
    const next = () => {
      if (i >= lines.length) return
      t = setTimeout(() => {
        i += 1
        setShown(i)
        next()
      }, lines[i].delayMs)
    }
    next()
    return () => clearTimeout(t)
  }, [active, lines])

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [shown])

  return (
    <div className="w-full">
      <div
        className="flex items-center gap-2 border-b px-4 py-2.5 text-[11px]"
        style={{
          borderColor: 'rgba(232,227,210,0.08)',
          color: 'var(--w-dim)',
          letterSpacing: '0.12em',
        }}
      >
        <span
          aria-hidden
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: running ? 'var(--fire)' : 'var(--cel)' }}
        />
        {title}
      </div>
      <div
        ref={scrollRef}
        className="overflow-hidden px-4 py-4 text-[15px] leading-[1.9]"
        style={{ height: 240 }}
        aria-live="off"
      >
        {lines.slice(0, shown).map((l, i) => (
          <div key={i} style={{ color: TONE_COLOR[l.tone], whiteSpace: 'pre-wrap' }}>
            {l.link ? (
              <>
                {l.text.split(l.link.text)[0]}
                <a
                  href={l.link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-4 transition-opacity hover:opacity-80"
                  style={{ color: 'var(--cel)' }}
                >
                  {l.link.text}
                </a>
                {l.text.split(l.link.text)[1]}
              </>
            ) : (
              l.text
            )}
          </div>
        ))}
        {running && (
          <motion.span
            aria-hidden
            className="inline-block h-[15px] w-[8px]"
            style={{ background: 'rgba(232,227,210,0.6)' }}
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 0.8, repeat: Infinity }}
          />
        )}
      </div>
    </div>
  )
}
