// web/components/app-shell/GlassPanel.tsx
import type { CSSProperties, ReactNode } from 'react'

export function GlassPanel({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <div
      style={{
        borderRadius: 6,
        padding: 1,
        backgroundImage:
          'linear-gradient(#0000,#0000), linear-gradient(160deg, rgba(0,229,204,.5), rgba(240,237,232,.3) 50%, rgba(124,58,237,.3))',
        backgroundOrigin: 'border-box',
        backgroundClip: 'padding-box, border-box',
        ...style,
      }}
    >
      <div style={{ position: 'relative', borderRadius: 5, overflow: 'hidden', height: '100%' }}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backdropFilter: 'var(--glass-blur)',
            WebkitBackdropFilter: 'var(--glass-blur)',
            background: 'var(--glass-fill)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(160deg, rgba(255,255,255,.06), rgba(0,229,204,.02) 45%, rgba(0,0,0,.24))',
            boxShadow: 'inset 0 1px 1px rgba(255,255,255,.16), inset 0 -12px 20px rgba(0,0,0,.3)',
          }}
        />
        <div style={{ position: 'relative', zIndex: 2, height: '100%' }}>{children}</div>
      </div>
    </div>
  )
}
