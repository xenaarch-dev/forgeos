'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'

const LINKS = [
  { label: 'Pipeline', href: '#pipeline' },
  { label: 'Agents', href: '#agents' },
  { label: 'Proof', href: '#proof' },
  {
    label: 'GitHub',
    href: 'https://github.com/xenaarch-dev/forgeos',
    external: true,
  },
]

export default function Nav() {
  const ref = useRef<HTMLElement>(null)
  const rx = useMotionValue(0)
  const ry = useMotionValue(0)
  const rotateX = useSpring(rx, { stiffness: 120, damping: 18, mass: 0.4 })
  const rotateY = useSpring(ry, { stiffness: 120, damping: 18, mass: 0.4 })
  const [pastHero, setPastHero] = useState(false)

  useEffect(() => {
    const onScroll = () => setPastHero(window.scrollY > window.innerHeight)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    const fine = window.matchMedia('(pointer: fine)').matches
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!fine || reduced) return

    const onMove = (e: MouseEvent) => {
      const el = ref.current
      if (!el) return
      const r = el.getBoundingClientRect()
      const cx = r.left + r.width / 2
      const cy = r.top + r.height / 2
      // proximity falloff — full tilt within the pill, fading ~360px out
      const dx = (e.clientX - cx) / 360
      const dy = (e.clientY - cy) / 360
      const dist = Math.hypot(dx, dy)
      const falloff = Math.max(0, 1 - Math.max(0, dist - 1) * 0.8)
      ry.set(Math.max(-1, Math.min(1, dx)) * 4 * falloff)
      rx.set(Math.max(-1, Math.min(1, -dy)) * 4 * falloff)
    }
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [rx, ry])

  return (
    <motion.header
      ref={ref}
      className="glass fixed left-1/2 top-4 z-50 flex h-14 items-center justify-between gap-6 pl-6 pr-2"
      style={{
        translateX: '-50%',
        rotateX,
        rotateY,
        transformPerspective: 800,
        width: 'min(720px, calc(100vw - 24px))',
        opacity: pastHero ? 1 : 0.85,
        transition: 'opacity 0.4s ease',
      }}
    >
      <a
        href="#hero"
        className="text-xl italic"
        style={{
          fontFamily: 'var(--font-serif)',
          fontWeight: 500,
          color: 'var(--w)',
        }}
      >
        ForgeOS
      </a>

      <nav aria-label="Primary" className="hidden items-center gap-6 md:flex">
        {LINKS.map((l) => (
          <a
            key={l.label}
            href={l.href}
            target={l.external ? '_blank' : undefined}
            rel={l.external ? 'noopener noreferrer' : undefined}
            className="relative z-10 text-[12px] transition-colors duration-300"
            style={{ color: 'var(--w-dim)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--w)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--w-dim)')}
          >
            {l.label}
          </a>
        ))}
      </nav>

      <a
        href="#cta"
        className="relative z-10 flex h-10 shrink-0 items-center px-4 text-[13px] font-bold transition-transform duration-300 hover:scale-[1.03]"
        style={{
          background:
            'linear-gradient(135deg, #F2A93C 0%, var(--gold) 55%, #C97A12 100%)',
          color: 'var(--void)',
          borderRadius: 10,
          boxShadow: '0 0 24px rgba(232,150,31,0.35)',
        }}
      >
        Build it →
      </a>
    </motion.header>
  )
}
