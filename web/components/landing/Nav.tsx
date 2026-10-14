'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'

const LINKS = [
  { href: '#agents', label: 'AGENTS' },
  { href: '#how', label: 'HOW IT WORKS' },
  { href: '#proof', label: 'PROOF' },
]

const CTA_HREF = 'https://contractforge.co.in'

// Desktop: logo · section links · dashboard + CTA, all in one row.
// Below 860px (globals.css .fg-nav-*): the links and actions collapse into a
// MENU button that opens a full-width panel under the bar.
export function Nav() {
  const [open, setOpen] = useState(false)

  // Close on Escape, and when the viewport grows back to desktop.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    const mq = window.matchMedia('(min-width: 860px)')
    const onResize = () => { if (mq.matches) setOpen(false) }
    window.addEventListener('keydown', onKey)
    mq.addEventListener('change', onResize)
    return () => {
      window.removeEventListener('keydown', onKey)
      mq.removeEventListener('change', onResize)
    }
  }, [open])

  return (
    <nav
      className="fg-nav"
      style={{
        position: 'fixed', top: 26, left: 0, right: 0, height: 64, zIndex: 200,
        background: 'rgba(12,14,16,0.50)', backdropFilter: 'blur(28px)', WebkitBackdropFilter: 'blur(28px)',
        borderBottom: '0.5px solid rgba(164,216,255,0.10)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 0 }}>
        <span style={{ font: '900 22px var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', flexShrink: 0 }}>
          ForgeOS
        </span>
        <div
          className="glass fg-nav-badge"
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, whiteSpace: 'nowrap' }}
        >
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#A4D8FF', animation: 'fg-pulse 2.4s ease-in-out infinite' }} />
          <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.80)', letterSpacing: '0.14em' }}>
            3 AGENTS LIVE
          </span>
        </div>
      </div>

      <div className="fg-nav-links" style={{ gap: 28 }}>
        {LINKS.map((l) => (
          <a key={l.href} href={l.href} style={{ font: '400 9.5px var(--font-mono)', color: 'rgba(236,235,230,0.42)', letterSpacing: '0.10em', whiteSpace: 'nowrap' }}>
            {l.label}
          </a>
        ))}
      </div>

      <div className="fg-nav-actions" style={{ alignItems: 'center', gap: 20 }}>
        <Link href="/login" style={{ font: '400 9.5px var(--font-mono)', color: 'rgba(236,235,230,0.42)', letterSpacing: '0.10em' }}>
          DASHBOARD
        </Link>
        <a
          href={CTA_HREF}
          target="_blank"
          rel="noopener noreferrer"
          data-magnetic
          style={{
            font: '700 9.5px var(--font-mono)', letterSpacing: '0.10em', whiteSpace: 'nowrap',
            background: '#A4D8FF', color: '#0C0E10', padding: '10px 18px', borderRadius: 2,
          }}
        >
          TRY CONTRACTFORGE →
        </a>
      </div>

      <button
        type="button"
        className="fg-nav-toggle"
        aria-expanded={open}
        aria-controls="fg-nav-menu"
        onClick={() => setOpen((o) => !o)}
        style={{
          alignItems: 'center', gap: 8, padding: '10px 12px', borderRadius: 2,
          border: '0.5px solid rgba(164,216,255,0.30)', color: '#A4D8FF',
          font: '400 9.5px var(--font-mono)', letterSpacing: '0.12em',
        }}
      >
        <span aria-hidden style={{ display: 'grid', gap: 3 }}>
          <span style={{ display: 'block', width: 14, height: 1.5, background: 'currentColor', transition: 'transform 0.25s var(--ease)', transform: open ? 'translateY(4.5px) rotate(45deg)' : 'none' }} />
          <span style={{ display: 'block', width: 14, height: 1.5, background: 'currentColor', transition: 'opacity 0.2s', opacity: open ? 0 : 1 }} />
          <span style={{ display: 'block', width: 14, height: 1.5, background: 'currentColor', transition: 'transform 0.25s var(--ease)', transform: open ? 'translateY(-4.5px) rotate(-45deg)' : 'none' }} />
        </span>
        {open ? 'CLOSE' : 'MENU'}
      </button>

      {open && (
        <div
          id="fg-nav-menu"
          className="fg-nav-menu"
          style={{
            position: 'absolute', top: '100%', left: 0, right: 0,
            background: 'rgba(12,14,16,0.97)', backdropFilter: 'blur(28px)', WebkitBackdropFilter: 'blur(28px)',
            borderBottom: '0.5px solid rgba(164,216,255,0.15)', boxShadow: '0 24px 60px rgba(0,0,0,0.7)',
            display: 'flex', flexDirection: 'column', padding: '8px 20px 20px',
            animation: 'fg-fadein 0.25s var(--ease) both',
          }}
        >
          {[...LINKS, { href: '/login', label: 'DASHBOARD' }].map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              style={{
                font: '400 12px var(--font-mono)', color: '#ECEBE6', letterSpacing: '0.12em',
                padding: '16px 0', borderBottom: '0.5px solid rgba(164,216,255,0.10)',
              }}
            >
              {l.label}
            </a>
          ))}
          <a
            href={CTA_HREF}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
            style={{
              marginTop: 16, textAlign: 'center', font: '700 11px var(--font-mono)', letterSpacing: '0.10em',
              background: '#A4D8FF', color: '#0C0E10', padding: '14px 18px', borderRadius: 2,
            }}
          >
            TRY CONTRACTFORGE →
          </a>
        </div>
      )}
    </nav>
  )
}
