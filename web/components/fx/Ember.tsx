'use client'

import { CSSProperties } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

/**
 * The recurring amber ember motif — hero baseline, pipeline traveller,
 * CTA input. 6px glowing dot with a slow 2.4s breathing pulse.
 */
export default function Ember({
  size = 6,
  style,
  className = '',
}: {
  size?: number
  style?: CSSProperties
  className?: string
}) {
  const reduced = useReducedMotion()
  return (
    <motion.span
      aria-hidden
      className={`inline-block ${className}`}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: 'var(--fire)',
        boxShadow:
          '0 0 10px 2px rgba(217,131,42,0.85), 0 0 28px 8px rgba(217,131,42,0.30)',
        ...style,
      }}
      animate={
        reduced
          ? { opacity: 1 }
          : { scale: [1, 1.15, 1], opacity: [0.7, 1, 0.7] }
      }
      transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
}
