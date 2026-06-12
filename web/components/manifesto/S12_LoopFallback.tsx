'use client'

/**
 * The constellation — static/CSS-animated SVG version. Always built,
 * always shippable on its own: central amber core (the ember motif,
 * larger), 7 celadon nodes in orbit, thin arcs, pulses travelling the
 * arcs via SMIL. Pulses hide under prefers-reduced-motion.
 */

const CX = 300
const CY = 300

// 7 orbiters — varied radii, evenly fanned
const NODES = [150, 195, 168, 215, 158, 205, 182].map((r, i) => {
  const a = (i / 7) * Math.PI * 2 - Math.PI / 2
  return {
    x: CX + r * Math.cos(a),
    y: CY + r * Math.sin(a),
    r,
  }
})

// quadratic arc from node to core, bowed perpendicular to the chord
function arc(x: number, y: number) {
  const mx = (x + CX) / 2
  const my = (y + CY) / 2
  const dx = CX - x
  const dy = CY - y
  const len = Math.hypot(dx, dy)
  const bow = 0.22
  const cx = mx - (dy / len) * len * bow
  const cy = my + (dx / len) * len * bow
  return `M ${x.toFixed(1)} ${y.toFixed(1)} Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${CX} ${CY}`
}

export default function S12_LoopFallback() {
  return (
    <div className="relative mx-auto w-full max-w-[560px]">
      <svg
        viewBox="0 0 600 600"
        role="img"
        aria-label="The nightly learning loop — seven agents orbiting the ForgeOS core"
        style={{ width: '100%', display: 'block' }}
      >
        <style>{`
          .loop-core { animation: loop-pulse 2.4s ease-in-out infinite; transform-origin: 300px 300px; }
          @keyframes loop-pulse {
            0%, 100% { transform: scale(1); opacity: 0.85; }
            50% { transform: scale(1.12); opacity: 1; }
          }
          @media (prefers-reduced-motion: reduce) {
            .loop-core { animation: none; }
            .loop-traveller { display: none; }
          }
        `}</style>

        {/* faint orbit hints */}
        <circle
          cx={CX}
          cy={CY}
          r={182}
          fill="none"
          stroke="rgba(232,227,210,0.05)"
          strokeWidth={1}
          strokeDasharray="2 7"
        />
        <circle
          cx={CX}
          cy={CY}
          r={232}
          fill="none"
          stroke="rgba(232,227,210,0.04)"
          strokeWidth={1}
          strokeDasharray="2 9"
        />

        {/* arcs */}
        {NODES.map((n, i) => (
          <path
            key={`a${i}`}
            id={`loop-arc-${i}`}
            d={arc(n.x, n.y)}
            fill="none"
            stroke="rgba(62,180,137,0.20)"
            strokeWidth={1}
          />
        ))}

        {/* pulses travelling the arcs (SMIL — zero JS) */}
        {[0, 2, 4, 5].map((i, k) => (
          <circle key={`p${i}`} className="loop-traveller" r={2.4} fill="#E8E3D2">
            <animateMotion
              dur={`${2.6 + k * 0.7}s`}
              begin={`${k * 1.1}s`}
              repeatCount="indefinite"
            >
              <mpath href={`#loop-arc-${i}`} />
            </animateMotion>
            <animate
              attributeName="opacity"
              values="0;0.9;0"
              dur={`${2.6 + k * 0.7}s`}
              begin={`${k * 1.1}s`}
              repeatCount="indefinite"
            />
          </circle>
        ))}

        {/* 7 celadon nodes */}
        {NODES.map((n, i) => (
          <g key={`n${i}`}>
            <circle cx={n.x} cy={n.y} r={11} fill="rgba(62,180,137,0.12)" />
            <circle cx={n.x} cy={n.y} r={4.5} fill="var(--cel)" />
          </g>
        ))}

        {/* central amber core — the ember, larger */}
        <circle cx={CX} cy={CY} r={64} fill="rgba(217,131,42,0.10)" />
        <circle cx={CX} cy={CY} r={34} fill="rgba(217,131,42,0.22)" />
        <g className="loop-core">
          <circle cx={CX} cy={CY} r={15} fill="var(--fire)" />
        </g>
      </svg>
    </div>
  )
}
