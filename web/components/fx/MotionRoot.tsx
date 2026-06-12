'use client'

import { ReactNode } from 'react'
import { MotionConfig } from 'framer-motion'

/**
 * Framer Motion ignores the CSS prefers-reduced-motion kill switch —
 * reducedMotion="user" makes every motion component degrade transform
 * animations to simple fades when the OS asks for reduced motion.
 */
export default function MotionRoot({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>
}
