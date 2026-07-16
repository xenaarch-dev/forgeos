import { FilamentForge } from '@/components/canvas/FilamentForge'

export function Mission() {
  return (
    <section id="mission" style={{ minHeight: '100vh', background: '#0C0E10', padding: '120px 56px', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: '44%', overflow: 'hidden', zIndex: 1 }}>
        <img
          src="/art/mission-sculpture.jpg"
          alt=""
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'right center', filter: 'grayscale(100%) brightness(0.65) contrast(1.1)' }}
          onError={(e) => { e.currentTarget.style.display = 'none' }}
        />
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to left, #0C0E10 0%, rgba(12,14,16,0.70) 45%, transparent 100%)' }} />
      </div>

      <FilamentForge />

      <div style={{ position: 'relative', zIndex: 2, marginLeft: '52%', paddingLeft: '8%' }}>
        <div style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.20em', marginBottom: 20 }}>
          THE MISSION
        </div>
        <h2 style={{ font: '900 52px/1.05 var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal' }}>
          Indian founders spend 80%
        </h2>
        <h2 style={{ font: '900 52px/1.05 var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal' }}>
          of their time on operations.
        </h2>
        <h2 style={{ font: '900 52px/1.05 var(--font-display)', letterSpacing: '-0.053em', color: '#A4D8FF', fontStyle: 'normal', marginBottom: 28 }}>
          ForgeOS makes that 0%.
        </h2>
        <p style={{ font: '400 17px var(--font-body)', color: 'rgba(236,235,230,0.55)', lineHeight: 1.7, maxWidth: 480 }}>
          Every product ForgeOS builds goes back into the loop.
          Every contract generated teaches ContractForge how to write better contracts.
          Every lead converted teaches OutreachForge how to find better leads.
          The system compounds. The founder thinks.
        </p>
        <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.25)', letterSpacing: '0.10em', marginTop: 28 }}>
          — XENARCH · MUMBAI · 2026
        </div>
      </div>
    </section>
  )
}
