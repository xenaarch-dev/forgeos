// web/components/app-shell/Nav.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Sigil } from './Sigil'

const NAV_ITEMS = [
  { href: '/app', label: 'Dashboard' },
  { href: '/app/products', label: 'Products' },
  { href: '/app/agents', label: 'Agents' },
  { href: '/app/artifacts', label: 'Artifacts' },
  { href: '/app/command', label: 'Command' },
  { href: '/app/billing', label: 'Billing' },
  { href: '/app/settings', label: 'Settings' },
]

export function Nav() {
  const pathname = usePathname()
  return (
    <nav style={{ width: 220, flexShrink: 0, background: 'var(--deep)', borderRight: '0.5px solid rgba(0,229,204,0.14)', display: 'flex', flexDirection: 'column', padding: '16px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBottom: 14, borderBottom: '0.5px solid rgba(0,229,204,0.12)', marginBottom: 14 }}>
        <Sigil size={28} />
        <span style={{ font: '900 15px var(--font-serif)', color: 'var(--w)' }}>ForgeOS</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {NAV_ITEMS.map((item) => {
          const active = item.href === '/app' ? pathname === '/app' : pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                padding: '9px 10px',
                borderRadius: 4,
                font: '500 12px var(--font-body)',
                color: active ? 'var(--teal)' : 'var(--w-dim)',
                background: active ? 'rgba(0,229,204,0.08)' : 'transparent',
                borderLeft: active ? '2px solid var(--teal)' : '2px solid transparent',
              }}
            >
              {item.label}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
