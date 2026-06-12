'use client'

import { useEffect, useState } from 'react'

/**
 * Chapter progress rail — 13 nodes down the left edge. Desktop only
 * (hidden < 1200px), fades in once the hero exits (scroll > 80vh).
 * Pending: ghost · Active: gold, glowing · Complete: teal.
 */

const SECTIONS = [
  { id: 'hero', label: 'the garden' },
  { id: 'problem', label: 'the burden' },
  { id: 'pipeline', label: 'the machine' },
  { id: 'agents', label: 'maya' },
  { id: 'aria', label: 'aria' },
  { id: 'rex', label: 'rex' },
  { id: 'zen', label: 'zen' },
  { id: 'marcus', label: 'marcus' },
  { id: 'lexi', label: 'lexi' },
  { id: 'kira', label: 'kira' },
  { id: 'proof', label: 'proof' },
  { id: 'loop', label: 'the loop' },
  { id: 'cta', label: 'build it' },
]

export default function ProgressRail() {
  const [activeIdx, setActiveIdx] = useState(0)
  const [shown, setShown] = useState(false)

  useEffect(() => {
    let raf = 0
    const onScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        setShown(window.scrollY > window.innerHeight * 0.8)
        const probe = window.scrollY + window.innerHeight * 0.5
        let idx = 0
        for (let i = 0; i < SECTIONS.length; i++) {
          const el = document.getElementById(SECTIONS[i].id)
          if (el && el.offsetTop <= probe) idx = i
        }
        setActiveIdx(idx)
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  return (
    <nav
      aria-label="Chapter progress"
      className="fixed left-5 top-1/2 z-40 hidden -translate-y-1/2 min-[1200px]:block"
      style={{
        opacity: shown ? 1 : 0,
        pointerEvents: shown ? 'auto' : 'none',
        transition: 'opacity 0.5s ease',
      }}
    >
      <div className="relative flex flex-col items-center gap-4">
        {/* the 1px track */}
        <span
          aria-hidden
          className="absolute bottom-2 top-2 w-px"
          style={{ background: 'var(--w-ghost)' }}
        />
        {SECTIONS.map((s, i) => {
          const state =
            i === activeIdx ? 'active' : i < activeIdx ? 'complete' : 'pending'
          return (
            <button
              key={s.id}
              type="button"
              aria-label={`Go to ${s.label}`}
              aria-current={state === 'active' ? 'true' : undefined}
              onClick={() =>
                document
                  .getElementById(s.id)
                  ?.scrollIntoView({ behavior: 'smooth' })
              }
              className="relative flex h-3 w-3 items-center justify-center"
            >
              <span
                aria-hidden
                className="block rounded-full transition-all duration-300"
                style={{
                  width: state === 'active' ? 8 : 5,
                  height: state === 'active' ? 8 : 5,
                  background:
                    state === 'active'
                      ? 'var(--gold)'
                      : state === 'complete'
                        ? 'var(--teal)'
                        : 'var(--w-ghost)',
                  boxShadow:
                    state === 'active' ? '0 0 12px var(--gold)' : 'none',
                }}
              />
              {state === 'active' && (
                <span
                  aria-hidden
                  className="absolute left-5 text-[9px]"
                  style={{
                    color: 'var(--w-dim)',
                    writingMode: 'vertical-rl',
                    letterSpacing: '0.15em',
                    fontFamily: 'var(--font-body)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {s.label}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
