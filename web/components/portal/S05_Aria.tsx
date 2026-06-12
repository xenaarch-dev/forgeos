'use client'

import AgentChapter from '@/components/portal/AgentChapter'
import { DrawPath, Appear } from '@/components/fx/SvgDraw'
import { ariaStack } from '@/data/simulations'

const WHITE = 'rgba(240,237,232,0.85)'
const WHITE_DIM = 'rgba(240,237,232,0.45)'
const BOX_FILL = 'rgba(6,3,24,0.45)'
const FONT = 'var(--font-body)'

function Box({
  x,
  y,
  w,
  h,
  label,
  dim = false,
}: {
  x: number
  y: number
  w: number
  h: number
  label: string
  dim?: boolean
}) {
  return (
    <>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={8}
        fill={BOX_FILL}
        stroke={dim ? WHITE_DIM : WHITE}
        strokeWidth={1}
      />
      <text
        x={x + w / 2}
        y={y + h / 2 + 4}
        textAnchor="middle"
        fill={dim ? 'rgba(240,237,232,0.6)' : '#F0EDE8'}
        style={{ fontFamily: FONT, fontSize: 15 }}
      >
        {label}
      </text>
    </>
  )
}

/* The system diagram drawing itself — edges in teal, boxes after. */
function ArchSim({ active }: { active: boolean }) {
  const [nextjs, fastapi, supabase] = ariaStack.column
  const [lemon, resend, doppler] = ariaStack.rails
  return (
    <div className="overflow-x-auto px-4 py-6 md:px-6">
      <svg
        viewBox="0 0 760 410"
        role="img"
        aria-label="ContractForge architecture: Next.js 14 to FastAPI to Supabase, with Lemon Squeezy, Resend and Doppler rails. Deploys to Vercel and Render."
        style={{ minWidth: 620, width: '100%', display: 'block' }}
      >
        {/* main column */}
        <Appear active={active} delay={0.1}>
          <Box x={300} y={24} w={160} h={44} label={nextjs} />
        </Appear>
        <DrawPath d="M 380 68 V 156" active={active} delay={0.5} />
        <Appear active={active} delay={1.0}>
          <Box x={270} y={156} w={220} h={44} label={fastapi} />
        </Appear>
        <DrawPath d="M 380 200 V 288" active={active} delay={1.4} />
        <Appear active={active} delay={1.9}>
          <Box x={240} y={288} w={280} h={44} label={supabase} />
        </Appear>

        {/* side rails */}
        <DrawPath
          d="M 220 144 H 244 V 168 H 270"
          active={active}
          delay={2.3}
          duration={0.55}
        />
        <Appear active={active} delay={2.6}>
          <Box x={20} y={126} w={200} h={36} label={lemon} dim />
        </Appear>
        <DrawPath
          d="M 220 226 H 244 V 192 H 270"
          active={active}
          delay={2.55}
          duration={0.55}
        />
        <Appear active={active} delay={2.85}>
          <Box x={20} y={208} w={200} h={36} label={resend} dim />
        </Appear>
        <DrawPath
          d="M 558 144 H 516 V 168 H 490"
          active={active}
          delay={2.8}
          duration={0.55}
        />
        <Appear active={active} delay={3.1}>
          <Box x={558} y={126} w={182} h={36} label={doppler} dim />
        </Appear>

        {/* last element — amber deploy annotation */}
        <DrawPath
          d="M 460 332 V 366 H 520"
          active={active}
          delay={3.5}
          duration={0.5}
          stroke="var(--gold)"
          strokeWidth={1}
        />
        <Appear active={active} delay={3.9}>
          <text
            x={530}
            y={370}
            fill="var(--gold)"
            style={{ fontFamily: FONT, fontSize: 12, letterSpacing: '0.08em' }}
          >
            {ariaStack.annotation}
          </text>
        </Appear>
      </svg>
    </div>
  )
}

export default function S05_Aria() {
  return (
    <AgentChapter
      id="aria"
      eyebrow="// Aria → ArchitectAgent"
      name="Aria"
      role="She draws the system before it exists."
      glow="violet"
      tint="glass-deep"
    >
      {(active) => <ArchSim active={active} />}
    </AgentChapter>
  )
}
