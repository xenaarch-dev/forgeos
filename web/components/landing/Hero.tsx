'use client'

import { useMetrics } from '@/hooks/useMetrics'
import { getDayNumber, getYcDaysRemaining } from '@/lib/forge/dates'
import { SignalBloom } from '@/components/canvas/SignalBloom'

const STAGGER = [0.2, 0.35, 0.5, 0.65, 0.8]

export function Hero() {
  const metrics = useMetrics()
  const dayNumber = metrics?.day_number ?? getDayNumber()
  const ycDays = metrics?.yc_days_remaining ?? getYcDaysRemaining()
  const leadsSent = metrics?.leads?.sent ?? 9
  const leadsApproved = metrics?.leads?.approved ?? 2
  const outreachStatus = metrics?.agent_status?.outreach ?? 'queued_awaiting_approval'
  const contractStatus = metrics?.agent_status?.contractforge ?? 'live'

  return (
    <section id="hero" style={{ position: 'relative', height: '100vh', minHeight: 640, background: '#0C0E10', overflow: 'hidden' }}>
      {/* background gradient */}
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, transparent 0%, rgba(12,14,16,0.4) 100%)', zIndex: 1 }} />

      {/* sculpture — right side */}
      <div style={{ position: 'absolute', right: 0, top: 0, height: '100%', width: '48%', overflow: 'hidden', zIndex: 2 }}>
        <img
          src="/art/hero-sculpture.jpg"
          alt=""
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'left center', filter: 'grayscale(100%) brightness(0.75) contrast(1.1)' }}
          onError={(e) => { e.currentTarget.style.display = 'none' }}
        />
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to right, #0C0E10 0%, rgba(12,14,16,0.55) 45%, transparent 100%)' }} />
        <div style={{ position: 'absolute', inset: 0, background: 'rgba(164,216,255,0.08)', mixBlendMode: 'luminosity' }} />
      </div>

      <SignalBloom />

      {/* left HUD panel */}
      <div
        className="glass"
        style={{
          position: 'absolute', left: '4%', top: '17%', width: 196, zIndex: 5, padding: 16, borderRadius: 4,
          animation: 'fg-breathe 4.5s ease-in-out infinite',
        }}
      >
        <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.65)', letterSpacing: '0.16em', marginBottom: 10 }}>
          OUTREACH METRICS
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 50, marginBottom: 10 }}>
          {[30, 22, 38, 24, 50].map((height, i) => (
            <div
              key={i}
              style={{
                width: 10, height,
                background: i === 4 ? '#A4D8FF' : 'rgba(164,216,255,0.30)',
                boxShadow: i === 4 ? '0 0 10px rgba(164,216,255,0.6)' : 'none',
              }}
            />
          ))}
        </div>
        <div style={{ font: '400 8.5px var(--font-mono)', color: 'var(--warm-white)', marginBottom: 4 }}>
          {leadsSent} LEADS · {leadsApproved} WARM
        </div>
        <div style={{ font: '400 8.5px var(--font-mono)', color: 'rgba(236,235,230,0.45)', marginBottom: 4 }}>
          OUTREACH: DAILY {leadsSent}/20
        </div>
        <div style={{ font: '400 8.5px var(--font-mono)', color: '#A4D8FF' }}>
          ▸ DAY {dayNumber} · LOOP ACTIVE
        </div>
      </div>

      {/* right HUD panel */}
      <div
        className="glass"
        style={{
          position: 'absolute', right: '4%', top: '15%', width: 196, zIndex: 5, padding: 16, borderRadius: 4,
          animation: 'fg-breathe 5s ease-in-out 1.5s infinite',
        }}
      >
        <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.65)', letterSpacing: '0.16em', marginBottom: 10 }}>
          AGENT MESH
        </div>
        {[
          { name: 'OutreachForge', status: outreachStatus === 'live' ? 'RUNNING' : outreachStatus === 'idle' ? 'IDLE' : 'RUNNING' },
          { name: 'ContractForge', status: contractStatus === 'live' ? 'LIVE · 276/276 ✓' : 'OFFLINE' },
          { name: 'GBrain', status: 'ACTIVE' },
        ].map((row) => (
          <div key={row.name} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 7 }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#A4D8FF', animation: 'fg-pulse 2.2s ease-in-out infinite', flexShrink: 0 }} />
            <span style={{ font: '400 9px var(--font-mono)', color: 'var(--warm-white)', flexShrink: 0 }}>{row.name}</span>
            <span style={{ font: '400 7px var(--font-mono)', color: '#A4D8FF', marginLeft: 'auto', whiteSpace: 'nowrap' }}>{row.status}</span>
          </div>
        ))}
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '0.5px solid rgba(164,216,255,0.12)', font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.45)' }}>
          YC DEADLINE: {ycDays} DAYS
        </div>
      </div>

      {/* hero text block */}
      <div style={{ position: 'absolute', bottom: '15%', left: '8%', maxWidth: 680, zIndex: 6 }}>
        <div
          className="glass"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderRadius: 20, marginBottom: 20,
            opacity: 0, animation: `fg-fadein 0.8s ease ${STAGGER[0]}s forwards`,
          }}
        >
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#A4D8FF', animation: 'fg-pulse 2.4s ease-in-out infinite' }} />
          <span style={{ font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.10em' }}>
            PRODUCT 001: CONTRACTFORGE — LIVE
          </span>
        </div>

        <h1
          style={{
            font: '900 clamp(56px,7.6vw,118px)/0.94 var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal',
            opacity: 0, animation: `fg-fadein 0.8s ease ${STAGGER[1]}s forwards`,
          }}
        >
          The autonomous business OS
        </h1>
        <h1
          style={{
            font: '900 clamp(56px,7.6vw,118px)/0.94 var(--font-display)', letterSpacing: '-0.053em', color: 'rgba(236,235,230,0.20)', fontStyle: 'normal',
            opacity: 0, animation: `fg-fadein 0.8s ease ${STAGGER[2]}s forwards`,
          }}
        >
          built for solo founders.
        </h1>

        <div
          style={{
            font: '400 12px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.22em', margin: '22px 0 28px',
            opacity: 0, animation: `fg-fadein 0.8s ease ${STAGGER[3]}s forwards`,
          }}
        >
          AGENTS RUNNING. FOUNDER THINKING.
        </div>

        <div style={{ display: 'flex', gap: 14, opacity: 0, animation: `fg-fadein 0.8s ease ${STAGGER[4]}s forwards` }}>
          <a href="/signup" data-magnetic style={{ background: '#A4D8FF', color: '#0C0E10', font: '700 9.5px var(--font-mono)', letterSpacing: '0.08em', padding: '14px 28px' }}>
            START BUILDING →
          </a>
          <a href="#agents" data-magnetic style={{ border: '0.5px solid rgba(236,235,230,0.20)', color: '#ECEBE6', font: '400 9.5px var(--font-mono)', letterSpacing: '0.08em', padding: '14px 28px' }}>
            MEET THE AGENTS ↓
          </a>
        </div>
      </div>

      <div style={{ position: 'absolute', bottom: 32, left: '50%', transform: 'translateX(-50%)', font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.25)', letterSpacing: '0.14em', zIndex: 6 }}>
        ↓ SCROLL
      </div>
    </section>
  )
}
