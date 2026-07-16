'use client'

import { useMetrics } from '@/hooks/useMetrics'
import { getDayNumber } from '@/lib/forge/dates'

export function Proof() {
  const metrics = useMetrics()
  const dayNumber = metrics?.day_number ?? getDayNumber()
  const mrr = metrics?.mrr_inr ?? 0

  const stats = [
    { value: String(dayNumber), label: 'DAYS IN PRODUCTION' },
    { value: '276', label: 'TESTS GREEN' },
    { value: '7', label: 'LIVE AGENTS' },
    { value: '1', label: 'SOLO FOUNDER' },
  ]

  return (
    <section id="proof" style={{ minHeight: '100vh', background: '#0C0E10', padding: '120px 56px', textAlign: 'center' }}>
      <div className="glass" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderRadius: 20, marginBottom: 32 }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#A4D8FF', animation: 'fg-pulse 2.4s ease-in-out infinite' }} />
        <span style={{ font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.10em' }}>PROOF OF WORK</span>
      </div>

      <h2 style={{ font: '900 clamp(48px,6vw,96px)/1.0 var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal' }}>
        Built by ForgeOS.
        <br />
        Running on ForgeOS.
      </h2>

      <p style={{ font: '400 18px var(--font-body)', color: 'rgba(236,235,230,0.55)', lineHeight: 1.65, maxWidth: 640, margin: '28px auto 0' }}>
        ContractForge is not a case study. It is Product 001 — the first thing the factory
        built, running on the same agent mesh that created it.
      </p>

      <div style={{ display: 'flex', justifyContent: 'center', gap: 0, maxWidth: 720, margin: '64px auto 0', flexWrap: 'wrap' }}>
        {stats.map((s, i) => (
          <div
            key={s.label}
            style={{
              flex: '1 1 150px', padding: '0 24px',
              borderLeft: i > 0 ? '0.5px solid rgba(236,235,230,0.12)' : 'none',
            }}
          >
            <div style={{ font: '900 72px var(--font-display)', color: '#A4D8FF', fontStyle: 'normal' }}>{s.value}</div>
            <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.30)', letterSpacing: '0.16em', marginTop: 6 }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div className="glass" style={{ maxWidth: 860, margin: '56px auto 0', borderRadius: 6, textAlign: 'left', overflow: 'hidden' }}>
        <div style={{ display: 'flex' }}>
          <div style={{ width: 160, flexShrink: 0, borderRight: '0.5px solid rgba(164,216,255,0.12)', padding: 20 }}>
            <div style={{ font: '900 14px var(--font-display)', color: '#ECEBE6', marginBottom: 16, fontStyle: 'normal' }}>ForgeOS</div>
            <div style={{ font: '400 9px var(--font-mono)', color: '#A4D8FF' }}>▸ Dashboard</div>
          </div>
          <div style={{ flex: 1, padding: 20, display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
            {[
              { tag: 'MATCH ✓', text: '@priya_fintech — score 0.94 → warm' },
              { tag: 'CONTRACT', text: 'NDA generated — Indian Contract Act 1872' },
              { tag: 'GBRAIN', text: 'Nightly loop complete · +3 lessons written' },
              { tag: 'OUTREACH', text: 'Daily quota: 9/20 messages sent' },
            ].map((row) => (
              <div key={row.tag} style={{ display: 'flex', gap: 12, font: '400 10px var(--font-mono)' }}>
                <span style={{ color: '#A4D8FF', flexShrink: 0, minWidth: 76 }}>[{row.tag}]</span>
                <span style={{ color: 'rgba(236,235,230,0.55)' }}>{row.text}</span>
              </div>
            ))}
          </div>
        </div>
        <div style={{ borderTop: '0.5px solid rgba(164,216,255,0.12)', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)' }}>
          {[
            { v: `₹${mrr.toLocaleString('en-IN')}`, l: 'MRR' },
            { v: String(metrics?.leads?.sent ?? 9), l: 'LEADS' },
            { v: '276 ✓', l: 'TESTS' },
            { v: '• LIVE', l: 'CONTRACTFORGE' },
          ].map((c) => (
            <div key={c.l} style={{ padding: '14px 16px', textAlign: 'center' }}>
              <div style={{ font: '700 18px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal' }}>{c.v}</div>
              <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(236,235,230,0.30)', letterSpacing: '0.12em', marginTop: 3 }}>{c.l}</div>
            </div>
          ))}
        </div>
      </div>

      <a href="/app" data-magnetic style={{ display: 'inline-block', marginTop: 40, font: '700 10px var(--font-mono)', letterSpacing: '0.10em', color: '#A4D8FF' }}>
        OPEN WAR ROOM →
      </a>
    </section>
  )
}
