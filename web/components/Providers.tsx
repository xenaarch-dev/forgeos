'use client'

import { AnimatePresence } from 'framer-motion'

export default function Providers({ children }: { children: React.ReactNode }) {
  return <AnimatePresence>{children}</AnimatePresence>
}
