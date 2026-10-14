'use client'

// Re-mounts on every navigation (that is what a template is for), so each page
// fades in instead of snapping. Opacity only: a transform on this wrapper would
// become the containing block for the fixed Nav / MissionBar and shift them.

import { motion, useReducedMotion } from 'framer-motion'

export default function RootTemplate({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}
