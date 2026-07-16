export function Sigil({ size = 34, glowIntensity = 0.4 }: { size?: number; glowIntensity?: number }) {
  const glow = Math.max(0, Math.min(1, glowIntensity))
  return (
    <svg
      viewBox="0 0 240 240"
      width={size}
      height={size}
      style={{
        animation: `ringspin ${Math.round(85 - glow * 65)}s linear infinite`,
        filter: `drop-shadow(0 0 ${Math.round(8 + glow * 30)}px rgba(164,216,255,${(0.08 + glow * 0.4).toFixed(2)}))`,
      }}
    >
      <circle cx="120" cy="120" r="104" fill="none" stroke="rgba(164,216,255,0.2)" strokeWidth="4" />
      <circle cx="120" cy="120" r="76" fill="none" stroke="rgba(164,216,255,0.35)" strokeWidth="4" strokeDasharray="6 20" />
      <circle cx="120" cy="120" r="18" fill="#A4D8FF" opacity={(0.45 + glow * 0.5).toFixed(2)} />
    </svg>
  )
}
