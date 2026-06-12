'use client'

import { Component, ReactNode, useEffect, useRef, useState } from 'react'
import dynamic from 'next/dynamic'
import { motion } from 'framer-motion'
import Glow from '@/components/fx/Glow'
import S12_LoopFallback from '@/components/manifesto/S12_LoopFallback'

const EASE = [0.22, 1, 0.36, 1] as const

// Three.js loads only on the client, only when needed; the SVG
// fallback stands in while it loads.
const LoopScene = dynamic(() => import('@/components/manifesto/LoopScene'), {
  ssr: false,
  loading: () => <S12_LoopFallback />,
})

/* Any error inside the 3D scene renders the fallback — the page can
   never break on Three.js. */
class SceneBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch() {
    try {
      sessionStorage.setItem('forgeos-loop3d', 'failed')
    } catch {}
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

function Constellation() {
  const hostRef = useRef<HTMLDivElement>(null)
  const [mode, setMode] = useState<'fallback' | 'three'>('fallback')

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const smallTouch =
      window.matchMedia('(pointer: coarse)').matches && window.innerWidth < 768
    let failedBefore = false
    try {
      failedBefore = sessionStorage.getItem('forgeos-loop3d') === 'failed'
    } catch {}
    if (reduced || smallTouch || failedBefore) return

    // mount Three only once the section is within one viewport
    const el = hostRef.current
    if (!el) return
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setMode('three')
          io.disconnect()
        }
      },
      { rootMargin: '100% 0px 100% 0px' }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <div ref={hostRef}>
      {mode === 'three' ? (
        <SceneBoundary fallback={<S12_LoopFallback />}>
          <LoopScene onFail={() => setMode('fallback')} />
        </SceneBoundary>
      ) : (
        <S12_LoopFallback />
      )}
    </div>
  )
}

export default function S12_Loop() {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden py-32">
      <div className="w-full max-w-4xl px-6 md:px-10">
        <motion.p
          className="eyebrow"
          style={{ color: 'var(--cel)' }}
          initial={{ opacity: 0, x: -28 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: '0px 0px -15% 0px' }}
          transition={{ duration: 0.8, ease: EASE }}
        >
          {'// 04 — it learns while you sleep'}
        </motion.p>

        <div className="mt-5 overflow-hidden">
          <motion.h2
            className="type-chapter"
            initial={{ y: '105%' }}
            whileInView={{ y: 0 }}
            viewport={{ once: true, margin: '0px 0px -15% 0px' }}
            transition={{ duration: 0.9, ease: EASE }}
          >
            Every night at 02:00 IST, ForgeOS reads everything it did.
          </motion.h2>
        </div>

        <motion.p
          className="mt-6 text-base"
          style={{ color: 'var(--w-dim)', maxWidth: '50ch' }}
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '0px 0px -15% 0px' }}
          transition={{ duration: 0.8, delay: 0.2, ease: EASE }}
        >
          Agent logs. Payments. Emails. Commits. A Nightly Reasoning Agent
          finds the patterns and rewrites the rules. Every product it ships
          makes the next one better.
        </motion.p>
      </div>

      <motion.div
        className="relative mt-12 w-full px-6"
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '0px 0px -10% 0px' }}
        transition={{ duration: 1, delay: 0.15, ease: EASE }}
      >
        <Glow
          color="rgba(217,131,42,0.08)"
          size={560}
          style={{ top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}
        />
        <Constellation />
      </motion.div>
    </section>
  )
}
