'use client'

import { motion } from 'framer-motion'

const EASE = [0.22, 1, 0.36, 1] as const

/**
 * SVG draw primitives — edges draw via pathLength (stroke-dashoffset
 * under the hood), nodes fade in after their edges.
 */
export function DrawPath({
  d,
  active,
  delay = 0,
  duration = 0.7,
  stroke = 'var(--cel)',
  strokeWidth = 1.5,
}: {
  d: string
  active: boolean
  delay?: number
  duration?: number
  stroke?: string
  strokeWidth?: number
}) {
  return (
    <motion.path
      d={d}
      fill="none"
      stroke={stroke}
      strokeWidth={strokeWidth}
      initial={{ pathLength: 0, opacity: 0 }}
      animate={active ? { pathLength: 1, opacity: 1 } : { pathLength: 0, opacity: 0 }}
      transition={{ duration, delay, ease: EASE }}
    />
  )
}

export function Appear({
  active,
  delay = 0,
  children,
}: {
  active: boolean
  delay?: number
  children: React.ReactNode
}) {
  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={active ? { opacity: 1 } : { opacity: 0 }}
      transition={{ duration: 0.6, delay, ease: EASE }}
    >
      {children}
    </motion.g>
  )
}
