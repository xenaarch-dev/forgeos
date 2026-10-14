'use client'

// In-app page transition: content rises and fades in under the fixed shell
// (sidebar, topbar and metrics bar live in layout.tsx and do not re-mount).

import { motion, useReducedMotion } from 'framer-motion'

export default function AppTemplate({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      style={{ minHeight: '100%' }}
    >
      {children}
    </motion.div>
  )
}
