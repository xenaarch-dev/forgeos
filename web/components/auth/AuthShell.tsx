import type { ReactNode } from 'react'
import { MissionBar } from '@/components/global/MissionBar'
import { BootSequence } from '@/components/global/BootSequence'
import { SignalBloom } from '@/components/canvas/SignalBloom'

export function AuthShell({ tagline, children }: { tagline: string; children: ReactNode }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: '#0C0E10' }}>
      <BootSequence />
      <MissionBar chapter="CH.00 // AUTH" />

      <div style={{ flex: '0 0 60%', position: 'relative', display: 'grid', placeItems: 'center', paddingTop: 26, overflow: 'hidden' }}>
        <SignalBloom />
        <div style={{ position: 'relative', zIndex: 2, textAlign: 'center' }}>
          <div style={{ font: '900 72px var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal' }}>
            ForgeOS
          </div>
          <div style={{ font: '400 11px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.20em', marginTop: 14 }}>
            {tagline}
          </div>
        </div>
      </div>

      <div style={{ flex: '0 0 40%', display: 'grid', placeItems: 'center', paddingTop: 26, borderLeft: '0.5px solid rgba(164,216,255,0.10)' }}>
        <div className="glass" style={{ width: 360, padding: 48, borderRadius: 6 }}>
          {children}
        </div>
      </div>
    </div>
  )
}
