import type { CSSProperties, ReactNode } from 'react'

export function GlassPanel({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <div className="glass" style={{ borderRadius: 4, overflow: 'hidden', ...style }}>
      {children}
    </div>
  )
}
