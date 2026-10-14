'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, useScroll, useTransform, useReducedMotion } from 'framer-motion'
import { AgentSprite, type SpriteMode } from '@/components/agents/AgentSprite'
import { statusColor } from '@/lib/forge/agents'
import {
  BELT_ITEMS,
  STATIONS,
  STANDBY_CREW,
  WORKING_CREW,
  type CrewMember,
  type StationId,
} from '@/lib/forge/crew'

// ---------------------------------------------------------------------------
// Simulation: each working agent walks between its route's stations, works a
// few seconds at each, says what it is doing, and moves on. Positions are
// written straight to the DOM each frame (no React re-render per frame);
// React state only changes when an agent arrives or leaves a station.
// ---------------------------------------------------------------------------

const WALK_SPEED = 0.075        // floor widths per second
const WORK_MIN_S = 2.6
const WORK_MAX_S = 4.6
const FLOOR_H = 520
const FLOOR_TOP = 0.27          // fraction of floor height where the back lane sits
const FLOOR_DEPTH = 0.42        // how far forward the front lane comes
const SPRITE = 60

type Sim = { x: number; leg: number; until: number; facing: 1 | -1; actionIdx: number }
type View = { mode: SpriteMode; station: StationId | null; text: string | null }

const stationX = (id: StationId) => STATIONS.find((s) => s.id === id)?.x ?? 0.5

// Agents sharing a station fan out diagonally by lane, so nobody stands on anybody.
const LANE_BY_SLUG: Record<string, number> = Object.fromEntries(WORKING_CREW.map((m) => [m.slug, m.lane]))
const slotOffset = (slug: string) => ((LANE_BY_SLUG[slug] ?? 0.5) - 0.5) * 0.1

function initialView(member: CrewMember): View {
  const first = member.route[0]
  return { mode: 'working', station: first, text: member.actions[first]?.[0] ?? null }
}

function useFloorSim(enabled: boolean) {
  const nodes = useRef<Record<string, HTMLDivElement | null>>({})
  const [views, setViews] = useState<Record<string, View>>(() =>
    Object.fromEntries(WORKING_CREW.map((m) => [m.slug, initialView(m)])),
  )

  // A ref mirror of `views` so the RAF loop reads the latest without re-subscribing.
  const viewsRef = useRef(views)
  const commit = useRef((slug: string, view: View) => {
    viewsRef.current = { ...viewsRef.current, [slug]: view }
    setViews(viewsRef.current)
  }).current

  // Kept across pauses, so scrolling away and back resumes instead of teleporting.
  const simsRef = useRef<Record<string, Sim>>({})

  useEffect(() => {
    if (!enabled) return
    const sims = simsRef.current
    const now = performance.now() / 1000
    WORKING_CREW.forEach((m, i) => {
      if (sims[m.slug]) {
        sims[m.slug].until = Math.max(sims[m.slug].until, now + 0.6)
        return
      }
      sims[m.slug] = {
        x: stationX(m.route[0]) + slotOffset(m.slug),
        leg: 0,
        // Stagger first departures so the floor doesn't move in unison.
        until: now + 1.2 + i * 0.9,
        facing: 1,
        actionIdx: 0,
      }
    })

    let raf = 0
    let last = now
    const tick = (ms: number) => {
      const t = ms / 1000
      const dt = Math.min(0.05, t - last)
      last = t
      for (const m of WORKING_CREW) {
        const sim = sims[m.slug]
        const view = viewsRef.current[m.slug]
        if (!sim || !view) continue

        if (view.mode === 'working' && t >= sim.until) {
          // Leave for the next station on the route.
          sim.leg = (sim.leg + 1) % m.route.length
          const next = m.route[sim.leg]
          sim.facing = stationX(next) + slotOffset(m.slug) >= sim.x ? 1 : -1
          commit(m.slug, { mode: 'walking', station: next, text: null })
        } else if (view.mode === 'walking' && view.station) {
          const target = stationX(view.station) + slotOffset(m.slug)
          const step = WALK_SPEED * dt * sim.facing
          if (Math.abs(target - sim.x) <= Math.abs(step)) {
            sim.x = target
            const lines = m.actions[view.station] ?? []
            sim.actionIdx += 1
            sim.until = t + WORK_MIN_S + ((sim.actionIdx * 0.37) % 1) * (WORK_MAX_S - WORK_MIN_S)
            commit(m.slug, {
              mode: 'working',
              station: view.station,
              text: lines.length ? lines[sim.actionIdx % lines.length] : null,
            })
          } else {
            sim.x += step
          }
        }

        const node = nodes.current[m.slug]
        if (node) {
          node.style.left = `${(sim.x * 100).toFixed(3)}%`
          node.dataset.facing = String(sim.facing)
        }
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [enabled, commit])

  return { nodes, views }
}

// ---------------------------------------------------------------------------

export function FactoryFloor() {
  const sectionRef = useRef<HTMLElement>(null)
  const floorRef = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion() ?? false
  const [onScreen, setOnScreen] = useState(false)
  const [focused, setFocused] = useState<string | null>(null)

  // Only simulate while the floor is visible: no work for an off-screen section.
  useEffect(() => {
    const el = floorRef.current
    if (!el) return
    const io = new IntersectionObserver(([entry]) => setOnScreen(entry.isIntersecting), { threshold: 0.15 })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  const { nodes, views } = useFloorSim(onScreen && !reduce)

  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ['start end', 'end start'] })
  const floorTilt = useTransform(scrollYProgress, [0, 0.5, 1], [16, 0, -6])
  const floorRise = useTransform(scrollYProgress, [0, 0.45], [60, 0])
  const glow = useTransform(scrollYProgress, [0.2, 0.5], [0, 1])

  const occupied = useMemo(() => {
    const counts: Partial<Record<StationId, number>> = {}
    for (const v of Object.values(views)) {
      if (v.mode === 'working' && v.station) counts[v.station] = (counts[v.station] ?? 0) + 1
    }
    return counts
  }, [views])

  const focusedMember = [...WORKING_CREW, ...STANDBY_CREW].find((m) => m.slug === focused) ?? null

  return (
    <section
      ref={sectionRef}
      id="agents"
      style={{ minHeight: '100vh', background: '#0C0E10', padding: '120px clamp(16px, 4vw, 56px) 96px', position: 'relative', overflow: 'hidden' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <span style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.22em', flexShrink: 0 }}>
          THE FACTORY FLOOR
        </span>
        <svg width="100%" height="6" style={{ maxWidth: 300 }} aria-hidden>
          <line x1="0" y1="3" x2="300" y2="3" stroke="rgba(164,216,255,0.15)" strokeWidth="1" strokeDasharray="2 6" />
        </svg>
      </div>

      <motion.h2
        initial={reduce ? false : { opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.6 }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        style={{ font: '900 clamp(40px, 6.5vw, 72px)/1.0 var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', textAlign: 'center', fontStyle: 'normal' }}
      >
        Seven agents. One closed loop.
      </motion.h2>
      <motion.p
        initial={reduce ? false : { opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.6 }}
        transition={{ duration: 0.8, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
        style={{ font: '400 18px var(--font-body)', color: 'rgba(236,235,230,0.40)', textAlign: 'center', maxWidth: 620, margin: '24px auto 56px', lineHeight: 1.6 }}
      >
        Every agent clocks in, works its station, logs every action, and feeds a nightly
        reasoning cycle. Hover one to see what it does.
      </motion.p>

      {/* ---------------------------------------------------------------- floor */}
      {/* Below ~900px the floor keeps its width and scrolls sideways instead of crushing the stations. */}
      <motion.div style={{ perspective: 1400, y: reduce ? 0 : floorRise, overflowX: 'auto', overflowY: 'hidden', paddingBottom: 8 }}>
        <motion.div
          ref={floorRef}
          role="group"
          aria-label="Animated factory floor showing ForgeOS agents at work"
          style={{
            position: 'relative',
            height: FLOOR_H,
            maxWidth: 1240,
            minWidth: 880,
            margin: '0 auto',
            borderRadius: 6,
            transformOrigin: '50% 100%',
            rotateX: reduce ? 0 : floorTilt,
            background:
              'radial-gradient(ellipse at 50% 0%, rgba(164,216,255,0.10), transparent 60%), linear-gradient(180deg, #101317 0%, #0A0C0E 100%)',
            border: '0.5px solid rgba(164,216,255,0.12)',
            borderTop: '1px solid rgba(164,216,255,0.35)',
            boxShadow: '0 40px 120px rgba(0,0,0,0.75)',
            overflow: 'hidden',
          }}
        >
          {/* floor grid */}
          <div
            aria-hidden
            style={{
              position: 'absolute', inset: 0,
              backgroundImage:
                'linear-gradient(rgba(164,216,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(164,216,255,0.05) 1px, transparent 1px)',
              backgroundSize: '48px 48px',
              maskImage: 'linear-gradient(180deg, transparent 0%, black 30%, black 100%)',
            }}
          />

          {/* back wall + stations */}
          <div aria-hidden style={{ position: 'absolute', left: 0, right: 0, top: 0, height: '30%', background: 'linear-gradient(180deg, rgba(53,57,60,0.35), rgba(53,57,60,0.05))', borderBottom: '0.5px solid rgba(164,216,255,0.10)' }} />
          {STATIONS.map((s) => {
            const busy = occupied[s.id] ?? 0
            return (
              <div key={s.id} aria-hidden style={{ position: 'absolute', left: `${s.x * 100}%`, top: 22, transform: 'translateX(-50%)', textAlign: 'center', width: 150 }}>
                <motion.div
                  style={{
                    width: 74, height: 54, margin: '0 auto', borderRadius: 6,
                    background: 'linear-gradient(180deg, #1A1F24, #121519)',
                    border: '0.5px solid rgba(164,216,255,0.22)',
                    borderTop: '1px solid rgba(164,216,255,0.55)',
                    boxShadow: busy ? '0 0 32px rgba(164,216,255,0.35), inset 0 0 18px rgba(164,216,255,0.18)' : '0 0 0 rgba(0,0,0,0)',
                    transition: 'box-shadow 0.6s var(--ease)',
                    position: 'relative',
                    opacity: reduce ? 1 : undefined,
                  }}
                >
                  <motion.div style={{ opacity: glow, position: 'absolute', inset: 8, borderRadius: 3, background: 'repeating-linear-gradient(90deg, rgba(164,216,255,0.25) 0 2px, transparent 2px 6px)' }} />
                  <span style={{ position: 'absolute', top: 6, right: 7, width: 5, height: 5, borderRadius: '50%', background: busy ? '#A4D8FF' : 'rgba(164,216,255,0.25)', animation: busy ? 'fg-pulse 1.2s ease-in-out infinite' : 'none' }} />
                  {busy > 0 && !reduce && (
                    <>
                      {[[-14, -10], [12, -14], [0, -18]].map(([sx, sy], i) => (
                        <span key={i} className="fg-floor-spark" style={{ position: 'absolute', left: '50%', bottom: 4, width: 3, height: 3, borderRadius: '50%', background: '#A4D8FF', boxShadow: '0 0 6px #A4D8FF', animationDelay: `${i * 0.23}s`, ['--sx' as string]: `${sx}px`, ['--sy' as string]: `${sy}px` }} />
                      ))}
                    </>
                  )}
                </motion.div>
                <div style={{ font: '400 8px var(--font-mono)', letterSpacing: '0.16em', color: busy ? '#A4D8FF' : 'rgba(164,216,255,0.45)', marginTop: 8, transition: 'color 0.6s' }}>
                  {s.label}
                </div>
              </div>
            )
          })}

          {/* working crew */}
          {WORKING_CREW.map((m) => {
            const view = views[m.slug]
            const depth = FLOOR_TOP + m.lane * FLOOR_DEPTH
            const scale = 0.86 + m.lane * 0.24
            const mode: SpriteMode = reduce ? 'idle' : view.mode
            return (
              <div
                key={m.slug}
                ref={(el) => { nodes.current[m.slug] = el }}
                data-facing="1"
                className="fg-floor-agent"
                style={{
                  position: 'absolute',
                  left: `${(stationX(m.route[0]) + slotOffset(m.slug)) * 100}%`,
                  top: `${depth * 100}%`,
                  zIndex: 10 + Math.round(m.lane * 10),
                  transform: `translate(-50%, 0) scale(${scale})`,
                  transformOrigin: '50% 100%',
                }}
              >
                {view.mode === 'working' && view.text && !reduce && (
                  <div
                    key={view.text}
                    className="fg-floor-bubble glass"
                    style={{ position: 'absolute', bottom: '100%', left: '50%', marginBottom: 4, padding: '4px 8px', borderRadius: 3, whiteSpace: 'nowrap', font: '400 9px var(--font-mono)', color: '#ECEBE6', letterSpacing: '0.04em', boxShadow: '0 8px 24px rgba(0,0,0,0.6)' }}
                  >
                    {view.text}
                  </div>
                )}
                <button
                  type="button"
                  onMouseEnter={() => setFocused(m.slug)}
                  onMouseLeave={() => setFocused((f) => (f === m.slug ? null : f))}
                  onFocus={() => setFocused(m.slug)}
                  onBlur={() => setFocused((f) => (f === m.slug ? null : f))}
                  aria-label={`${m.name}, ${m.status}: ${m.description}`}
                  style={{ display: 'block', background: 'none', padding: 0, cursor: 'pointer' }}
                >
                  <div className="fg-floor-flip">
                    <AgentSprite color={m.suit} prop={m.prop} mode={mode} size={SPRITE} />
                  </div>
                </button>
                <div
                  style={{
                    position: 'absolute', top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: 2,
                    font: '400 8.5px var(--font-mono)', letterSpacing: '0.08em', color: m.suit, whiteSpace: 'nowrap',
                    padding: '1px 5px', background: 'rgba(12,14,16,0.85)', borderRadius: 2, border: `0.5px solid ${m.suit}55`,
                  }}
                >
                  {m.name}
                </div>
              </div>
            )
          })}

          {/* standby bay */}
          <div style={{ position: 'absolute', left: 18, bottom: 70, padding: '10px 12px 8px', borderRadius: 4, border: '0.5px dashed rgba(164,216,255,0.22)', background: 'rgba(12,14,16,0.55)', zIndex: 30 }}>
            <div style={{ font: '400 7px var(--font-mono)', letterSpacing: '0.18em', color: 'rgba(164,216,255,0.5)', marginBottom: 6 }}>STANDBY BAY</div>
            <div style={{ display: 'flex', gap: 14 }}>
              {STANDBY_CREW.map((m) => (
                <button
                  key={m.slug}
                  type="button"
                  onMouseEnter={() => setFocused(m.slug)}
                  onMouseLeave={() => setFocused((f) => (f === m.slug ? null : f))}
                  onFocus={() => setFocused(m.slug)}
                  onBlur={() => setFocused((f) => (f === m.slug ? null : f))}
                  aria-label={`${m.name}, queued: ${m.lastAction ?? m.description}`}
                  style={{ background: 'none', padding: 0, textAlign: 'center', cursor: 'pointer' }}
                >
                  <AgentSprite color={m.suit} prop={m.prop} mode={reduce ? 'idle' : 'asleep'} size={34} />
                  <div style={{ font: '400 6.5px var(--font-mono)', color: 'rgba(236,235,230,0.45)', marginTop: 2 }}>{m.name}</div>
                </button>
              ))}
            </div>
          </div>

          {/* conveyor belt */}
          <div aria-hidden style={{ position: 'absolute', left: 0, right: 0, bottom: 18, height: 34, zIndex: 25 }}>
            <div style={{ position: 'absolute', inset: '8px 0', background: '#15191D', borderTop: '1px solid rgba(164,216,255,0.25)', borderBottom: '0.5px solid rgba(0,0,0,0.8)', backgroundImage: 'repeating-linear-gradient(90deg, rgba(164,216,255,0.07) 0 2px, transparent 2px 20px)', animation: reduce ? 'none' : 'fg-belt-stripes 1.6s linear infinite' }} />
            <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
              <div style={{ display: 'flex', gap: 120, width: 'max-content', height: '100%', alignItems: 'center', animation: reduce ? 'none' : 'fg-belt 26s linear infinite' }}>
                {[...BELT_ITEMS, ...BELT_ITEMS].map((item, i) => (
                  <span key={i} style={{ font: '400 8px var(--font-mono)', letterSpacing: '0.06em', color: '#0C0E10', background: '#A4D8FF', padding: '4px 8px', borderRadius: 2, boxShadow: '0 4px 12px rgba(164,216,255,0.25)' }}>
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* info card for the hovered / focused agent */}
          {focusedMember && (
            <div
              className="glass fg-floor-bubble"
              role="status"
              style={{ position: 'absolute', right: 18, bottom: 70, width: 240, padding: 14, borderRadius: 4, zIndex: 40, borderTop: `2px solid ${focusedMember.suit}`, transform: 'none', animationName: 'fg-fadein' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: statusColor(focusedMember.status) }} />
                <span style={{ font: '400 7px var(--font-mono)', letterSpacing: '0.12em', color: statusColor(focusedMember.status) }}>{focusedMember.status}</span>
              </div>
              <div style={{ font: '700 20px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 6 }}>{focusedMember.name}</div>
              <p style={{ font: '300 12px/1.5 var(--font-body)', color: 'rgba(236,235,230,0.6)' }}>{focusedMember.description}</p>
              {focusedMember.status === 'QUEUED' && focusedMember.lastAction && (
                <p style={{ font: '400 7.5px var(--font-mono)', color: 'rgba(164,216,255,0.55)', marginTop: 8 }}>{focusedMember.lastAction}</p>
              )}
            </div>
          )}
        </motion.div>
      </motion.div>
    </section>
  )
}
