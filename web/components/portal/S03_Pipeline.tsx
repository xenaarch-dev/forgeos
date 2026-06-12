'use client'

import { useEffect, useRef, useState } from 'react'
import {
  motion,
  MotionValue,
  useReducedMotion,
  useScroll,
  useTransform,
} from 'framer-motion'
import PortalScene from '@/components/portal/PortalScene'

const STAGES = [
  'office_hours',
  'ceo_review',
  'architect',
  'eng_review',
  'design',
  'scaffold',
  'mission_work',
  'review',
  'adversarial',
  'score',
  'security',
  'cso',
  'qa',
  'validator',
  'deploy',
  'browser_setup',
  'launch',
  'operate',
]

const SVG_W = 1840
const SVG_H = 170
const LINE_Y = 64
const X0 = 32
const GAP = 100

function Node({
  i,
  progress,
  reduced,
}: {
  i: number
  progress: MotionValue<number>
  reduced: boolean
}) {
  const x = X0 + i * GAP
  const t = x / SVG_W
  // node snaps on as the line reaches it
  const opacity = useTransform(progress, [t, t + 0.012], [0, 1])
  const scale = useTransform(progress, [t, t + 0.018], [0.2, 1])
  // teal completion ring follows a beat later
  const ringOpacity = useTransform(progress, [t + 0.045, t + 0.065], [0, 1])

  return (
    <motion.g style={reduced ? undefined : { opacity }}>
      <motion.circle
        cx={x}
        cy={LINE_Y}
        r={4}
        fill="var(--gold)"
        style={
          reduced
            ? undefined
            : { scale, transformOrigin: `${x}px ${LINE_Y}px` }
        }
      />
      <motion.circle
        cx={x}
        cy={LINE_Y}
        r={8}
        fill="none"
        stroke="var(--teal)"
        strokeWidth={1}
        style={reduced ? undefined : { opacity: ringOpacity }}
      />
      <text
        x={x}
        y={LINE_Y + 34}
        textAnchor="middle"
        fill="rgba(240,237,232,0.55)"
        style={{ fontFamily: 'var(--font-body)', fontSize: 11 }}
      >
        {STAGES[i]}
      </text>
    </motion.g>
  )
}

/* small ember travelling the drawn path forever — the machine keeps going */
function Traveller({
  pathRef,
  progress,
}: {
  pathRef: React.RefObject<SVGPathElement>
  progress: MotionValue<number>
}) {
  const dotRef = useRef<SVGGElement>(null)

  useEffect(() => {
    const path = pathRef.current
    const dot = dotRef.current
    if (!path || !dot) return
    const L = path.getTotalLength()
    let len = 0
    let raf = 0
    let visible = true
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting
    })
    io.observe(path)

    const tick = () => {
      raf = requestAnimationFrame(tick)
      if (!visible || document.hidden) return
      const drawn = progress.get() * L
      if (drawn < 60) {
        dot.setAttribute('opacity', '0')
        return
      }
      len += 2.4
      if (len > drawn) len = 0
      const p = path.getPointAtLength(len)
      dot.setAttribute('transform', `translate(${p.x}, ${p.y})`)
      dot.setAttribute('opacity', '1')
    }
    tick()
    return () => {
      cancelAnimationFrame(raf)
      io.disconnect()
    }
  }, [pathRef, progress])

  return (
    <g ref={dotRef} opacity={0}>
      <circle r={6} fill="rgba(232,150,31,0.30)" />
      <circle r={2.5} fill="var(--gold)" />
    </g>
  )
}

export default function S03_Pipeline() {
  const reduced = useReducedMotion() ?? false
  const outerRef = useRef<HTMLElement>(null)
  const pathRef = useRef<SVGPathElement>(null)
  const [vw, setVw] = useState(1280)

  useEffect(() => {
    const onResize = () => setVw(window.innerWidth)
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const { scrollYProgress } = useScroll({
    target: outerRef,
    offset: ['start start', 'end end'],
  })
  // the line draws across the middle 80% of the scroll
  const pathLength = useTransform(scrollYProgress, [0.06, 0.92], [0, 1])
  // pan so the draw head stays in view; the line still exits the right edge
  const panMax = Math.min(0, -(SVG_W - vw + 48))
  const x = useTransform(scrollYProgress, [0.12, 0.92], [0, panMax])

  return (
    <section
      id="pipeline"
      ref={outerRef}
      className="relative"
      style={{ height: reduced ? 'auto' : '260vh' }}
    >
      <div
        className={`${
          reduced ? 'relative py-32' : 'sticky top-0 h-screen'
        } flex flex-col justify-center overflow-hidden`}
      >
        {/* particle ambient over pure void */}
        <PortalScene variant="field" density={0.25} />

        <motion.p
          className="eyebrow relative mb-20 px-6 md:px-16"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          {'// 02 — the machine'}
        </motion.p>

        <motion.div
          style={reduced ? undefined : { x }}
          className="relative will-change-transform"
        >
          <svg
            width={SVG_W}
            height={SVG_H}
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            fill="none"
            aria-label="The ForgeOS pipeline — 18 stages from office_hours to operate"
            role="img"
          >
            {/* ghost of the full route */}
            <path
              d={`M 0 ${LINE_Y} H ${SVG_W}`}
              stroke="rgba(240,237,232,0.08)"
              strokeWidth={1}
            />
            <motion.path
              ref={pathRef}
              d={`M 0 ${LINE_Y} H ${SVG_W}`}
              stroke="var(--gold)"
              strokeWidth={2}
              style={reduced ? undefined : { pathLength }}
              initial={reduced ? undefined : { pathLength: 0 }}
            />
            {STAGES.map((_, i) => (
              <Node
                key={STAGES[i]}
                i={i}
                progress={pathLength}
                reduced={reduced}
              />
            ))}
            {!reduced && <Traveller pathRef={pathRef} progress={pathLength} />}
          </svg>
        </motion.div>
      </div>
    </section>
  )
}
