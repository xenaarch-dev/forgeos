import { CSSProperties, ReactNode } from 'react'

/**
 * HUD annotation — wireframe data panel with teal corner brackets.
 * Decorative (aria-hidden), desktop only (hidden < 1200px).
 * Visual recipe lives in globals.css (.hud-panel).
 */
export default function HudPanel({
  children,
  style,
  className = '',
}: {
  children: ReactNode
  style?: CSSProperties
  className?: string
}) {
  return (
    <div
      aria-hidden
      className={`hud-panel hidden min-[1200px]:block ${className}`}
      style={style}
    >
      {children}
    </div>
  )
}
