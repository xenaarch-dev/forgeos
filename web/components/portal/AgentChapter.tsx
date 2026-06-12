'use client'

import { ReactNode, useEffect, useRef, useState } from 'react'
import {
  motion,
  useInView,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useTransform,
} from 'framer-motion'
import PortalScene from '@/components/portal/PortalScene'
import useScrollOpacity from '@/components/fx/useScrollOpacity'

/**
 * AgentChapter — the Image-5 scaffold shared by all seven agents.
 *
 * 200vh scroll container, content sticky. The AGENTS PortalScene fills
 * the upper 55% of the viewport; the glass panel overlaps the scene
 * boundary by 80px so imagery bleeds into the UI. The agent name
 * (Cormorant italic) sits BEHIND the glass top edge — above the scene,
 * below the glass.
 *
 * Scroll choreography (3 beats):
 *   A 0→0.25    name rises (y 80→0, opacity 0→1)
 *   B 0.25→0.55 glass panel rises (y 100→0, opacity 0→1)
 *                sim starts when panel opacity reaches 0.8 (p≈0.49)
 *   C 0.55→1.0  name drifts up −30px, fades to 0.3 — panel is focus
 *
 * Sims trigger at Beat B and run on their own clock — never scrubbed.
 */

const GLOWS = {
  teal: 'glow-teal',
  gold: 'glow-gold',
  violet: 'glow-violet',
  azure: 'glow-azure',
  red: 'glow-red',
} as const

export default function AgentChapter({
  id,
  eyebrow,
  name,
  role,
  glow,
  tint = '',
  caption,
  children,
}: {
  id?: string
  eyebrow: string
  name: string
  role: string
  glow: keyof typeof GLOWS
  tint?: '' | 'glass-cosmic' | 'glass-warm' | 'glass-deep'
  caption?: string
  children: (active: boolean) => ReactNode
}) {
  const reduced = useReducedMotion() ?? false
  const outerRef = useRef<HTMLElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const nameRef = useRef<HTMLDivElement>(null)
  const panelWrapRef = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState(false)

  // reduced-motion fallback: sim plays when panel is half in view
  const inViewStatic = useInView(panelRef, { amount: 0.5 })

  const { scrollYProgress } = useScroll({
    target: outerRef,
    offset: ['start start', 'end end'],
  })

  // Beat A + C — the name
  const nameY = useTransform(scrollYProgress, [0, 0.25, 0.55, 1], [80, 0, 0, -30])
  const nameOpacity = useTransform(
    scrollYProgress,
    [0, 0.25, 0.55, 1],
    [0, 1, 1, 0.3]
  )
  // Beat B — the panel
  const panelY = useTransform(scrollYProgress, [0.25, 0.55], [100, 0])
  const panelOpacity = useTransform(scrollYProgress, [0.25, 0.55], [0, 1])

  // opacity via direct DOM writes — survives mid-scroll re-renders
  useScrollOpacity(nameOpacity, nameRef, reduced)
  useScrollOpacity(panelOpacity, panelWrapRef, reduced)

  // sim trigger: panel opacity ≥ 0.8 → progress ≥ 0.49; replay on re-entry
  useMotionValueEvent(scrollYProgress, 'change', (p) => {
    if (reduced) return
    if (p >= 0.49) setActive(true)
    else if (p < 0.05) setActive(false)
  })

  // glass entry sweep (once) + cursor-reactive glow (--cx --cy)
  useEffect(() => {
    const panel = panelRef.current
    if (!panel) return

    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          panel.classList.add('swept')
          io.disconnect()
        }
      },
      { threshold: 0.35 }
    )
    io.observe(panel)

    const fine = window.matchMedia('(pointer: fine)').matches
    const reducedMq = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches
    let onMove: ((e: MouseEvent) => void) | null = null
    if (fine && !reducedMq) {
      onMove = (e) => {
        const r = panel.getBoundingClientRect()
        panel.style.setProperty('--cx', `${e.clientX - r.left}px`)
        panel.style.setProperty('--cy', `${e.clientY - r.top}px`)
      }
      panel.addEventListener('mousemove', onMove, { passive: true })
    }
    return () => {
      io.disconnect()
      if (onMove) panel.removeEventListener('mousemove', onMove)
    }
  }, [])

  const simActive = reduced ? inViewStatic : active

  return (
    <section
      id={id}
      ref={outerRef}
      data-imagery
      className="relative"
      style={{ height: reduced ? 'auto' : '200vh' }}
    >
      <div
        className={`${
          reduced ? 'relative min-h-screen py-24' : 'sticky top-0 h-screen'
        } overflow-hidden`}
      >
        {/* the machine interior — fills the upper 55%, bleeds behind the glass */}
        <div className="absolute inset-x-0 top-0 h-[55%]">
          <PortalScene variant="agents" />
          <div
            aria-hidden
            className="absolute inset-x-0 bottom-0 h-32"
            style={{
              background: 'linear-gradient(to bottom, transparent, var(--void))',
            }}
          />
        </div>

        {/* content column — name straddles the glass top edge */}
        <div className="absolute inset-x-0 bottom-0 top-0 flex flex-col items-center justify-end pb-[5vh]">
          <div className="relative w-full max-w-[900px] px-4 md:px-6">
            <motion.div
              ref={nameRef}
              className="relative z-[5]"
              style={reduced ? undefined : { y: nameY }}
            >
              <p className="eyebrow">{eyebrow}</p>
              <h2
                className="type-agent -mb-[0.42em] mt-2"
                style={{ textShadow: '0 8px 60px rgba(0,0,8,0.8)' }}
              >
                {name}
              </h2>
            </motion.div>

            <motion.div
              ref={panelWrapRef}
              className="relative"
              style={reduced ? undefined : { y: panelY }}
            >
              {/* ambient glow — always BEHIND the glass, never inside */}
              <div
                aria-hidden
                className={`glow-orb ${GLOWS[glow]}`}
                style={{
                  width: 640,
                  height: 640,
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%,-50%)',
                }}
              />
              <div ref={panelRef} className={`glass ${tint} relative z-10`}>
                {children(simActive)}
              </div>

              <p
                className="relative z-10 mt-5 text-center text-[13px]"
                style={{ color: 'var(--w-dim)', letterSpacing: '0.06em' }}
              >
                {role}
                {caption && (
                  <>
                    <span aria-hidden className="mx-3" style={{ color: 'var(--w-ghost)' }}>
                      ·
                    </span>
                    {caption}
                  </>
                )}
              </p>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
