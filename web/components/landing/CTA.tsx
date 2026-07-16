import { GlyphTide } from '@/components/canvas/GlyphTide'

export function CTA() {
  return (
    <section id="cta" style={{ minHeight: '80vh', background: '#0C0E10', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden', textAlign: 'center' }}>
      <GlyphTide />
      <div style={{ position: 'relative', zIndex: 2, padding: '0 24px' }}>
        <div style={{ font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.20em', marginBottom: 20 }}>
          CONTRACTFORGE IS LIVE. FREE FOR 3 CONTRACTS.
        </div>
        <h2 style={{ font: '900 clamp(48px,6vw,88px)/1.05 var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal' }}>
          Start with one prompt.
        </h2>
        <h2 style={{ font: '900 clamp(48px,6vw,88px)/1.05 var(--font-display)', letterSpacing: '-0.053em', color: 'rgba(236,235,230,0.25)', fontStyle: 'normal', marginBottom: 40 }}>
          Build everything else.
        </h2>
        <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
          <a
            href="https://contractforge.co.in"
            target="_blank"
            rel="noopener noreferrer"
            data-magnetic
            style={{ background: '#A4D8FF', color: '#0C0E10', font: '700 10px var(--font-mono)', letterSpacing: '0.08em', padding: '16px 30px' }}
          >
            GENERATE YOUR FIRST CONTRACT →
          </a>
          <a href="/signup" data-magnetic style={{ border: '0.5px solid rgba(236,235,230,0.20)', color: '#ECEBE6', font: '400 10px var(--font-mono)', letterSpacing: '0.08em', padding: '16px 30px' }}>
            REQUEST EARLY ACCESS
          </a>
        </div>
      </div>
    </section>
  )
}
