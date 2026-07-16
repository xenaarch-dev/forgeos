'use client'

import Link from 'next/link'

const LINKS = [
  { href: '#agents', label: 'AGENTS' },
  { href: '#how', label: 'HOW IT WORKS' },
  { href: '#proof', label: 'PROOF' },
  { href: '/login', label: 'DASHBOARD' },
]

export function Nav() {
  return (
    <nav
      style={{
        position: 'fixed', top: 26, left: 0, right: 0, height: 64, zIndex: 200,
        background: 'rgba(12,14,16,0.50)', backdropFilter: 'blur(28px)', WebkitBackdropFilter: 'blur(28px)',
        borderBottom: '0.5px solid rgba(164,216,255,0.10)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 32px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <span style={{ font: '900 22px var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6' }}>
          ForgeOS
        </span>
        <div
          className="glass"
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20 }}
        >
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#A4D8FF', animation: 'fg-pulse 2.4s ease-in-out infinite' }} />
          <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.80)', letterSpacing: '0.14em' }}>
            3 AGENTS LIVE
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 28 }}>
        {LINKS.slice(0, 3).map((l) => (
          <a key={l.href} href={l.href} style={{ font: '400 9.5px var(--font-mono)', color: 'rgba(236,235,230,0.42)', letterSpacing: '0.10em' }}>
            {l.label}
          </a>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <Link href="/login" style={{ font: '400 9.5px var(--font-mono)', color: 'rgba(236,235,230,0.42)', letterSpacing: '0.10em' }}>
          DASHBOARD
        </Link>
        <a
          href="https://contractforge.co.in"
          target="_blank"
          rel="noopener noreferrer"
          data-magnetic
          style={{
            font: '700 9.5px var(--font-mono)', letterSpacing: '0.10em',
            background: '#A4D8FF', color: '#0C0E10', padding: '10px 18px', borderRadius: 2,
          }}
        >
          TRY CONTRACTFORGE →
        </a>
      </div>
    </nav>
  )
}
