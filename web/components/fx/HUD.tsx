'use client'

import { motion } from 'framer-motion'

/**
 * HUD — sparse engineering callouts over the portal imagery, like
 * technical annotations on a photograph. Space Mono 10–11px, cream at
 * 50%, 1px connector line, corner-bracket frame on the anchor point.
 *
 * Desktop only (hidden < 1024px). Max 3–4 notes per scene — sparse is
 * the entire point. Notes fade in 600ms after the scene, staggered.
 *
 * `depth` (0 | 1 | 2) marks the parallax layer — consumed by the hero
 * scroll choreography (0.3x / 0.6x / 1x translate rates).
 */

export type HudNote = {
  label: string
  x: number // anchor, % from left
  y: number // anchor, % from top
  side?: 'left' | 'right' // which side of the anchor the label extends
  depth?: 0 | 1 | 2
}

const EASE = [0.22, 1, 0.36, 1] as const

function Bracket() {
  const s = 'rgba(232,227,210,0.5)'
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="shrink-0">
      <path d="M1 6 V1 H6" stroke={s} strokeWidth="1" />
      <path d="M12 1 H17 V6" stroke={s} strokeWidth="1" />
      <path d="M17 12 V17 H12" stroke={s} strokeWidth="1" />
      <path d="M6 17 H1 V12" stroke={s} strokeWidth="1" />
    </svg>
  )
}

function Note({ note, index }: { note: HudNote; index: number }) {
  const leftward = note.side === 'left'
  return (
    <motion.div
      data-hud-depth={note.depth ?? 1}
      className="absolute flex items-center gap-0"
      style={{
        left: `${note.x}%`,
        top: `${note.y}%`,
        transform: leftward ? 'translate(calc(-100% + 9px), -9px)' : 'translate(-9px, -9px)',
      }}
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, margin: '0px 0px -10% 0px' }}
      transition={{ duration: 0.8, delay: 0.6 + index * 0.18, ease: EASE }}
    >
      {leftward ? (
        <>
          <span
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: 10.5,
              letterSpacing: '0.18em',
              color: 'rgba(232,227,210,0.5)',
              whiteSpace: 'nowrap',
              textTransform: 'uppercase',
            }}
          >
            {note.label}
          </span>
          <span className="h-px w-10 shrink-0" style={{ background: 'rgba(232,227,210,0.28)' }} />
          <Bracket />
        </>
      ) : (
        <>
          <Bracket />
          <span className="h-px w-10 shrink-0" style={{ background: 'rgba(232,227,210,0.28)' }} />
          <span
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: 10.5,
              letterSpacing: '0.18em',
              color: 'rgba(232,227,210,0.5)',
              whiteSpace: 'nowrap',
              textTransform: 'uppercase',
            }}
          >
            {note.label}
          </span>
        </>
      )}
    </motion.div>
  )
}

export default function HUD({ notes }: { notes: HudNote[] }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-20 hidden lg:block">
      {notes.map((n, i) => (
        <Note key={n.label} note={n} index={i} />
      ))}
    </div>
  )
}
