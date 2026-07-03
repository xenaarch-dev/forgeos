'use client'

import { useEffect, useRef, useState } from 'react'
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from 'framer-motion'
import Ember from '@/components/fx/Ember'
import PortalScene from '@/components/portal/PortalScene'
import HudPanel from '@/components/portal/HudPanel'
import useScrollOpacity from '@/components/fx/useScrollOpacity'
import { useMetrics } from '@/hooks/useMetrics'

const EASE = [0.22, 1, 0.36, 1] as const
const LINE1 = 'One sentence in.'
const LINE2 = 'Full SaaS out.'

// Computed once on load — no network needed for these two
const DAY_NUMBER = Math.floor((Date.now() - new Date('2026-01-10').getTime()) / 86_400_000) + 1
const YC_DAYS = Math.max(0, Math.ceil((new Date('2026-07-27').getTime() - Date.now()) / 86_400_000))

function buildHudLeft(outreachStatus: string): string {
  // "7 DEPLOYED" is honest: agents exist and are built, but none are
  // currently running a live build — ContractForge is operated, not building.
  // OutreachForge has drafted leads queued for human approval.
  const outreachLine =
    outreachStatus === 'queued_awaiting_approval'
      ? 'OUTREACH: QUEUED'
      : outreachStatus === 'live'
        ? 'OUTREACH: LIVE'
        : 'OUTREACH: IDLE'
  return `FORGE CORE // ONLINE\nPIPELINE: 18 STAGES\nAGENTS: 7 DEPLOYED\n${outreachLine}`
}

function buildHudRight(dayNum: number, ycDays: number, mrr: number): string {
  const mrrStr = mrr === 0 ? '₹0' : `₹${mrr.toLocaleString('en-IN')}`
  return `DAY ${dayNum} — MUMBAI, INDIA\nYC: ${ycDays} DAYS\nCONTRACTFORGE: LIVE\nMRR: ${mrrStr}`
}

export default function S01_Hero() {
  const reduced = useReducedMotion() ?? false
  const outerRef = useRef<HTMLElement>(null)
  const titleRef = useRef<HTMLDivElement>(null)
  const subRef = useRef<HTMLParagraphElement>(null)
  const hudLRef = useRef<HTMLDivElement>(null)
  const hudRRef = useRef<HTMLDivElement>(null)
  const cueRef = useRef<HTMLDivElement>(null)
  const [c1, setC1] = useState(0)
  const [c2, setC2] = useState(0)
  const [typingDone, setTypingDone] = useState(false)

  // Live metrics — initial values are honest static fallbacks, API updates them
  const metrics = useMetrics()
  const [hudLeft, setHudLeft] = useState(() => buildHudLeft('queued_awaiting_approval'))
  const [hudRight, setHudRight] = useState(() => buildHudRight(DAY_NUMBER, YC_DAYS, 0))

  useEffect(() => {
    if (!metrics) return
    setHudLeft(buildHudLeft(metrics.agent_status.outreach))
    setHudRight(buildHudRight(metrics.day_number, metrics.yc_days_remaining, metrics.mrr_inr))
  }, [metrics])

  // load sequence: Forge. blurs in (0s) → typewriter (1.6s) → ember (2.8s)
  useEffect(() => {
    if (reduced) {
      setC1(LINE1.length)
      setC2(LINE2.length)
      setTypingDone(true)
      return
    }
    const timers: ReturnType<typeof setTimeout>[] = []
    let i1 = 0
    let i2 = 0
    const t0 = setTimeout(() => {
      const iv1 = setInterval(() => {
        i1 += 1
        setC1(i1)
        if (i1 >= LINE1.length) {
          clearInterval(iv1)
          const tp = setTimeout(() => {
            const iv2 = setInterval(() => {
              i2 += 1
              setC2(i2)
              if (i2 >= LINE2.length) {
                clearInterval(iv2)
                setTypingDone(true)
              }
            }, 42)
            timers.push(iv2 as unknown as ReturnType<typeof setTimeout>)
          }, 600)
          timers.push(tp)
        }
      }, 42)
      timers.push(iv1 as unknown as ReturnType<typeof setTimeout>)
    }, 1600)
    timers.push(t0)
    return () => timers.forEach((t) => clearTimeout(t))
  }, [reduced])

  // 280vh scroll scrub — walking toward the machine
  const { scrollYProgress } = useScroll({
    target: outerRef,
    offset: ['start start', 'end end'],
  })
  const sceneScale = useTransform(scrollYProgress, [0, 1], [1.2, 1])
  const titleY = useTransform(scrollYProgress, [0, 0.6], [0, -120])
  const titleOpacity = useTransform(scrollYProgress, [0, 0.6], [1, 0])
  const subOpacity = useTransform(scrollYProgress, [0, 0.35], [1, 0])
  // HUD panels live at different Z depths — different parallax rates
  const hudLeftY = useTransform(scrollYProgress, [0, 1], [0, -160])
  const hudRightY = useTransform(scrollYProgress, [0, 1], [0, -280])
  const hudOpacity = useTransform(scrollYProgress, [0, 0.45], [1, 0])

  // opacity via direct DOM writes — survives typewriter re-renders
  useScrollOpacity(titleOpacity, titleRef, reduced)
  useScrollOpacity(subOpacity, subRef, reduced)
  useScrollOpacity(hudOpacity, hudLRef, reduced)
  useScrollOpacity(hudOpacity, hudRRef, reduced)
  useScrollOpacity(hudOpacity, cueRef, reduced)

  return (
    <section
      id="hero"
      ref={outerRef}
      data-imagery
      className="relative"
      style={{ height: reduced ? '100svh' : '280vh' }}
    >
      <div
        className={`${
          reduced ? 'relative h-[100svh]' : 'sticky top-0 h-screen'
        } overflow-hidden`}
        style={{ background: 'var(--void)' }}
      >
        <motion.div
          className="absolute inset-0"
          style={reduced ? undefined : { scale: sceneScale }}
        >
          <PortalScene variant="hero" />
        </motion.div>

        {/* HUD panels — wireframe annotations at different Z depths */}
        <motion.div
          ref={hudLRef}
          style={reduced ? undefined : { y: hudLeftY }}
        >
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={typingDone ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.6, delay: 0.6, ease: EASE }}
          >
            <HudPanel style={{ left: '3vw', top: '25vh' }}>{hudLeft}</HudPanel>
          </motion.div>
        </motion.div>
        <motion.div
          ref={hudRRef}
          style={reduced ? undefined : { y: hudRightY }}
        >
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={typingDone ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.6, delay: 0.8, ease: EASE }}
          >
            <HudPanel style={{ right: '3vw', top: '35vh' }}>
              {hudRight}
            </HudPanel>
          </motion.div>
        </motion.div>

        {/* title block — the founder looks up */}
        <div className="flex h-full flex-col items-center justify-center px-6 text-center">
          <motion.div
            ref={titleRef}
            className="flex flex-col items-center"
            style={reduced ? undefined : { y: titleY }}
          >
            <motion.h1
              className="type-hero"
              initial={{ opacity: 0, filter: 'blur(20px)' }}
              animate={{ opacity: 1, filter: 'blur(0px)' }}
              transition={{ duration: 1.4, ease: EASE }}
            >
              Forge.
            </motion.h1>

            <motion.p
              ref={subRef}
              className="mt-8 flex h-7 items-baseline text-lg"
              style={{ color: 'var(--w)', letterSpacing: '0.02em' }}
            >
              <span className="sr-only">{`${LINE1} ${LINE2}`}</span>
              <span aria-hidden>
                {LINE1.slice(0, c1)}
                {c1 >= LINE1.length && <span className="inline-block w-3" />}
                {LINE2.slice(0, c2)}
              </span>
              {!typingDone && !reduced && (
                <motion.span
                  aria-hidden
                  className="ml-1 inline-block h-[18px] w-[9px] self-center"
                  style={{ background: 'rgba(240,237,232,0.7)' }}
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ duration: 0.9, repeat: Infinity }}
                />
              )}
              {typingDone && (
                <motion.span
                  className="ml-3 self-center"
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.6, ease: EASE }}
                >
                  <Ember />
                </motion.span>
              )}
            </motion.p>
          </motion.div>
        </div>

        {/* scroll cue */}
        <motion.div
          ref={cueRef}
          className="absolute bottom-8 left-1/2 flex -translate-x-1/2 flex-col items-center gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: reduced ? 0 : 3.4, duration: 1, ease: EASE }}
        >
          <span
            className="text-[11px] uppercase"
            style={{ color: 'var(--w-dim)', letterSpacing: '0.3em' }}
          >
            walk toward it
          </span>
          <div className="h-12 w-px overflow-hidden">
            <motion.div
              className="h-full w-px"
              style={{ background: 'var(--w)', transformOrigin: 'top' }}
              animate={
                reduced
                  ? { scaleY: 1 }
                  : { scaleY: [0, 1, 1], opacity: [1, 1, 0] }
              }
              transition={{
                duration: 2.2,
                times: [0, 0.65, 1],
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          </div>
        </motion.div>
      </div>
    </section>
  )
}
