'use client'

import { motion } from 'framer-motion'
import Glow from '@/components/fx/Glow'
import PortalScene from '@/components/fx/PortalScene'
import HUD from '@/components/fx/HUD'

const EASE = [0.22, 1, 0.36, 1] as const

const PROOF_NOTES = [
  { label: 'CONTRACTFORGE // LIVE', x: 13, y: 24, depth: 0 as const },
  { label: '₹2,499/MO', x: 86, y: 38, side: 'left' as const, depth: 1 as const },
  { label: 'BUILT BY FORGEOS', x: 84, y: 80, side: 'left' as const, depth: 2 as const },
]

/* ContractForge's real brand — visibly NOT the Night Forge.
   Proof that ForgeOS products get their own identity. */
const CF_GREEN = '#3E5F44'
const CF_SAND = '#DDD6B9'

/* Pixel-faithful static recreation of the live contractforge.co.in hero,
   ~70% scale. Not an iframe — a crisp visual recreation. */
function ContractForgeHero() {
  return (
    <div
      className="group relative overflow-hidden"
      style={{
        background: CF_GREEN,
        borderRadius: 8,
        fontFamily:
          'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
      }}
    >
      {/* screen-glare sweep on hover */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-y-0 w-1/3 -translate-x-[150%] opacity-0 transition-all duration-1000 ease-out group-hover:translate-x-[350%] group-hover:opacity-100"
        style={{
          background:
            'linear-gradient(105deg, transparent 0%, rgba(255,255,255,0.13) 50%, transparent 100%)',
        }}
      />

      {/* mini nav */}
      <div className="flex items-center justify-between px-6 pt-5 md:px-10">
        <span className="text-[13px] font-bold" style={{ color: CF_SAND }}>
          ContractForge ⚡
        </span>
        <span className="flex items-center gap-4 text-[11px]" style={{ color: CF_SAND }}>
          <span className="opacity-80">Sign in</span>
          <span
            className="rounded px-2.5 py-1 font-semibold"
            style={{ background: CF_SAND, color: CF_GREEN, borderRadius: 6 }}
          >
            Start free
          </span>
        </span>
      </div>

      {/* hero copy — centered vertical stack, like the live site */}
      <div className="flex flex-col items-center px-6 pb-12 pt-10 text-center md:px-12 md:pb-16 md:pt-14">
        <h3
          className="max-w-md font-bold leading-tight"
          style={{ color: CF_SAND, fontSize: 'clamp(22px, 3.4vw, 34px)' }}
        >
          Your next client contract. Done in 30 seconds.
        </h3>
        <p
          className="mt-4 max-w-md text-[12px] leading-relaxed md:text-[13px]"
          style={{ color: CF_SAND, opacity: 0.82 }}
        >
          GST-compliant. PDF export. Mumbai jurisdiction. Indian Contract Act.
          Professional contracts without a lawyer.
        </p>
        <span
          className="mt-6 inline-block px-5 py-2.5 text-[12px] font-bold md:text-[13px]"
          style={{ background: CF_SAND, color: CF_GREEN, borderRadius: 8 }}
        >
          Generate your first contract — free
        </span>
        <p className="mt-4 text-[10.5px]" style={{ color: CF_SAND, opacity: 0.6 }}>
          No credit card. No lawyer. 30 seconds.
        </p>
      </div>
    </div>
  )
}

export default function S11_Proof() {
  return (
    <section
      id="proof"
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden py-32"
    >
      <PortalScene variant="garden" />
      <HUD notes={PROOF_NOTES} />
      <div className="relative z-10 w-full max-w-4xl px-6 md:px-10">
        <motion.p
          className="eyebrow"
          style={{ color: 'var(--cel)' }}
          initial={{ opacity: 0, x: -28 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: '0px 0px -15% 0px' }}
          transition={{ duration: 0.8, ease: EASE }}
        >
          {'// 03 — not a demo'}
        </motion.p>

        <div className="mt-5 overflow-hidden">
          <motion.h2
            className="type-chapter"
            initial={{ y: '105%' }}
            whileInView={{ y: 0 }}
            viewport={{ once: true, margin: '0px 0px -15% 0px' }}
            transition={{ duration: 0.9, ease: EASE }}
          >
            We didn&rsquo;t describe it. We built it.
          </motion.h2>
        </div>
      </div>

      <div className="relative z-10 mt-14 w-full max-w-3xl px-6 md:px-10">
        <Glow
          color="rgba(62,180,137,0.09)"
          size={620}
          style={{ top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}
        />
        <motion.div
          className="glass relative p-4 md:p-6"
          initial={{ opacity: 0, y: 80 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '0px 0px -10% 0px' }}
          transition={{ duration: 1, delay: 0.15, ease: EASE }}
        >
          <ContractForgeHero />
        </motion.div>

        <motion.p
          className="mt-6 text-center text-[13px]"
          style={{ color: 'var(--w-dim)', letterSpacing: '0.08em' }}
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.4, ease: EASE }}
        >
          <a
            href="https://contractforge.co.in"
            target="_blank"
            rel="noopener noreferrer"
            className="underline-offset-4 transition-colors duration-300 hover:underline"
            style={{ color: 'var(--cel)' }}
          >
            contractforge.co.in
          </a>
          {' · live · ₹2,499/mo'}
        </motion.p>
      </div>
    </section>
  )
}
