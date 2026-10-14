// A little ForgeOS agent: visor helmet, coloured work suit, and a prop in hand.
// Pure SVG + CSS classes (globals.css: .fg-sprite-*), so it renders on the
// server, costs nothing per frame, and stops moving under reduced motion.

export type SpriteProp =
  | 'wrench' | 'clipboard' | 'shield' | 'megaphone'
  | 'scroll' | 'magnifier' | 'rocket' | 'brain'

export type SpriteMode = 'idle' | 'walking' | 'working' | 'asleep'

const INK = '#0C0E10'
const VISOR = '#A4D8FF'

function PropGlyph({ prop, color }: { prop: SpriteProp; color: string }) {
  // Drawn in a 14x14 box whose origin sits in the right hand.
  switch (prop) {
    case 'wrench':
      return (
        <g>
          <rect x="5.5" y="2" width="3" height="12" rx="1.2" fill="#C9CED4" />
          <path d="M3 2.5a4 4 0 0 1 8 0l-2.2 2.4H5.2Z" fill="#C9CED4" />
        </g>
      )
    case 'clipboard':
      return (
        <g>
          <rect x="1.5" y="1.5" width="11" height="13" rx="1.5" fill="#ECEBE6" stroke={INK} strokeWidth="0.8" />
          <rect x="4.5" y="0.4" width="5" height="2.4" rx="0.8" fill={color} />
          <path d="M4 6.5h6M4 9h6M4 11.5h4" stroke={INK} strokeWidth="0.9" strokeLinecap="round" />
        </g>
      )
    case 'shield':
      return <path d="M7 1 12.5 3v4.5c0 3.4-2.4 5.6-5.5 6.8C3.9 13.1 1.5 10.9 1.5 7.5V3Z" fill={VISOR} stroke={INK} strokeWidth="0.8" />
    case 'megaphone':
      return (
        <g>
          <path d="M2 5.5h3l6-3.5v11l-6-3.5H2Z" fill="#ECEBE6" stroke={INK} strokeWidth="0.8" strokeLinejoin="round" />
          <path d="M12.5 5.5q1.5 2-0 4" stroke="#ECEBE6" strokeWidth="1" fill="none" strokeLinecap="round" />
        </g>
      )
    case 'scroll':
      return (
        <g>
          <rect x="2" y="2.5" width="10" height="10" rx="1" fill="#ECEBE6" />
          <rect x="1" y="1.5" width="12" height="2.4" rx="1.2" fill="#C9B98F" />
          <rect x="1" y="11.6" width="12" height="2.4" rx="1.2" fill="#C9B98F" />
          <path d="M4 6.5h6M4 9h5" stroke={INK} strokeWidth="0.8" strokeLinecap="round" />
        </g>
      )
    case 'magnifier':
      return (
        <g>
          <circle cx="6" cy="6" r="4.2" fill="rgba(164,216,255,0.35)" stroke="#ECEBE6" strokeWidth="1.6" />
          <path d="M9 9l4 4.5" stroke="#ECEBE6" strokeWidth="2" strokeLinecap="round" />
        </g>
      )
    case 'rocket':
      return (
        <g>
          <path d="M7 0.8c3 2 3.6 5.6 2.6 9H4.4C3.4 6.4 4 2.8 7 0.8Z" fill="#ECEBE6" stroke={INK} strokeWidth="0.7" />
          <circle cx="7" cy="5" r="1.3" fill={VISOR} />
          <path d="M5 10h4l-2 3.5Z" fill="#F2A65A" />
        </g>
      )
    case 'brain':
      return (
        <g>
          <path d="M7 2.2c-1-1.3-4-1-4.3 1.2C1 4 1 6.6 2.4 7.4 1.6 9.6 3.4 11.6 5.4 11c.6 1 1 1.2 1.6 1.2V2.2Z" fill="#F2B8CC" stroke={INK} strokeWidth="0.7" />
          <path d="M7 2.2c1-1.3 4-1 4.3 1.2C13 4 13 6.6 11.6 7.4c.8 2.2-1 4.2-3 3.6-.6 1-1 1.2-1.6 1.2V2.2Z" fill="#F2B8CC" stroke={INK} strokeWidth="0.7" />
        </g>
      )
  }
}

export function AgentSprite({
  color,
  prop,
  mode = 'idle',
  size = 56,
  title,
}: {
  color: string
  prop: SpriteProp
  mode?: SpriteMode
  size?: number
  title?: string
}) {
  const dim = mode === 'asleep'
  return (
    <svg
      viewBox="0 0 48 64"
      width={size}
      height={(size * 64) / 48}
      className={`fg-sprite fg-sprite--${mode}`}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      style={{ overflow: 'visible', opacity: dim ? 0.55 : 1 }}
    >
      {/* floor shadow */}
      <ellipse className="fg-sprite-shadow" cx="24" cy="62" rx="12" ry="2.2" fill="rgba(0,0,0,0.55)" />

      <g className="fg-sprite-body">
        {/* legs */}
        <g className="fg-sprite-leg fg-sprite-leg--back">
          <rect x="17.5" y="45" width="5" height="13" rx="2.2" fill={color} />
          <rect x="16.5" y="56" width="7" height="3.6" rx="1.6" fill={INK} />
        </g>
        <g className="fg-sprite-leg fg-sprite-leg--front">
          <rect x="25.5" y="45" width="5" height="13" rx="2.2" fill={color} />
          <rect x="24.5" y="56" width="7" height="3.6" rx="1.6" fill={INK} />
        </g>

        {/* back arm */}
        <rect className="fg-sprite-arm fg-sprite-arm--back" x="11" y="31" width="4.6" height="12" rx="2.3" fill={color} />

        {/* torso: suit, zip, belt, badge */}
        <rect x="14" y="29" width="20" height="18" rx="6" fill={color} />
        <rect x="14" y="29" width="20" height="18" rx="6" fill="url(#fg-suit-shade)" />
        <path d="M24 30v11" stroke="rgba(12,14,16,0.35)" strokeWidth="1" />
        <rect x="14" y="41" width="20" height="2.6" fill="rgba(12,14,16,0.55)" />
        <rect x="22.4" y="40.6" width="3.2" height="3.4" rx="0.6" fill="#C9CED4" />
        <circle cx="29.2" cy="34" r="1.6" fill={VISOR} />

        {/* helmet with visor */}
        <g className="fg-sprite-head">
          <line x1="24" y1="5" x2="24" y2="10" stroke={color} strokeWidth="1.6" />
          <circle className="fg-sprite-antenna" cx="24" cy="4" r="2" fill={VISOR} />
          <rect x="12" y="9.5" width="24" height="20" rx="9" fill="#1A1F24" stroke={color} strokeWidth="1.6" />
          <rect x="15" y="14" width="18" height="10" rx="5" fill={INK} />
          {dim ? (
            <g stroke={VISOR} strokeWidth="1.3" strokeLinecap="round">
              <path d="M18 19.5h3.5M26.5 19.5h3.5" />
            </g>
          ) : (
            <g className="fg-sprite-eyes" fill={VISOR}>
              <rect x="18.2" y="16.6" width="3.4" height="4.8" rx="1.7" />
              <rect x="26.4" y="16.6" width="3.4" height="4.8" rx="1.7" />
            </g>
          )}
        </g>

        {/* front arm holding the prop */}
        <g className="fg-sprite-arm fg-sprite-arm--front">
          <rect x="32.4" y="31" width="4.6" height="12" rx="2.3" fill={color} />
          <g transform="translate(31.5 37) scale(0.95)">
            <PropGlyph prop={prop} color={color} />
          </g>
        </g>
      </g>

      {dim && (
        <g className="fg-sprite-zz" fill="rgba(164,216,255,0.75)" style={{ font: '700 7px var(--font-mono)' }}>
          <text x="36" y="10">z</text>
          <text x="41" y="4" style={{ fontSize: 5 }}>z</text>
        </g>
      )}

      <defs>
        <linearGradient id="fg-suit-shade" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="rgba(255,255,255,0.18)" />
          <stop offset="1" stopColor="rgba(0,0,0,0.28)" />
        </linearGradient>
      </defs>
    </svg>
  )
}
