'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { getYcDaysRemaining } from '@/lib/forge/dates'

const NAV_ITEMS = [
  { href: '/app', label: 'Dashboard', icon: '◉' },
  { href: '/app/products', label: 'Products', icon: '▣' },
  { href: '/app/agents', label: 'Agents', icon: '◈' },
  { href: '/app/artifacts', label: 'Artifacts', icon: '▤' },
  { href: '/app/command', label: 'Command', icon: '⌘' },
  { href: '/app/billing', label: 'Billing', icon: '$' },
  { href: '/app/settings', label: 'Settings', icon: '⚙' },
]

export function Sidebar({ collapsed = false }: { collapsed?: boolean }) {
  const pathname = usePathname()
  const ycDays = getYcDaysRemaining()
  const progressPct = Math.max(0, Math.min(100, (ycDays / 27) * 100))

  return (
    <nav
      style={{
        width: collapsed ? 48 : 220, flexShrink: 0, height: '100%', background: 'rgba(7,8,10,0.99)',
        borderRight: '0.5px solid rgba(164,216,255,0.08)', display: 'flex', flexDirection: 'column',
        padding: '18px 12px', transition: 'width 0.2s var(--ease)', overflow: 'hidden',
      }}
    >
      <div style={{ marginBottom: 20 }}>
        {!collapsed && (
          <>
            <div style={{ font: '900 20px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal' }}>ForgeOS</div>
            <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(236,235,230,0.25)', letterSpacing: '0.14em', marginTop: 4 }}>
              CORE V1.0
            </div>
          </>
        )}
        {collapsed && (
          <div style={{ font: '900 18px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', textAlign: 'center' }}>F</div>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
        {NAV_ITEMS.map((item) => {
          const active = item.href === '/app' ? pathname === '/app' : pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px',
                background: active ? 'rgba(164,216,255,0.08)' : 'transparent',
                borderLeft: active ? '2px solid #A4D8FF' : '2px solid transparent',
                color: active ? '#A4D8FF' : 'rgba(236,235,230,0.35)',
                font: '400 12px var(--font-mono)',
              }}
            >
              <span style={{ width: 16, textAlign: 'center', flexShrink: 0 }}>{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </div>

      {!collapsed && (
        <div style={{ marginTop: 'auto', paddingTop: 16 }}>
          <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(164,216,255,0.45)', letterSpacing: '0.14em' }}>
            YC DEADLINE
          </div>
          <div style={{ font: '900 28px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', margin: '4px 0 10px' }}>
            {ycDays} days
          </div>
          <div style={{ height: 2, background: 'rgba(164,216,255,0.15)' }}>
            <div style={{ height: '100%', width: `${progressPct}%`, background: '#A4D8FF' }} />
          </div>
        </div>
      )}
    </nav>
  )
}
