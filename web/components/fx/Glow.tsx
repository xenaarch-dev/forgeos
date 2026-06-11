import { CSSProperties } from 'react'

/**
 * Ambient radial glow blob. Sits BEHIND every glass panel so the
 * backdrop blur has content to refract — glass over flat black is dead glass.
 */
export default function Glow({
  color = 'rgba(62,180,137,0.08)',
  size = 480,
  style,
}: {
  color?: string
  size?: number
  style?: CSSProperties
}) {
  return (
    <div
      aria-hidden
      style={{
        position: 'absolute',
        width: size,
        height: size,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
        filter: 'blur(90px)',
        pointerEvents: 'none',
        ...style,
      }}
    />
  )
}
