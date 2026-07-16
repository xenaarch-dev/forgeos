const ITEMS = [
  {
    n: '01', title: 'You text. Agents build.',
    body: 'Message ForgeOS from Discord or the War Room. Architecture, code, security, deploy — seven agents orchestrate the full build. No meetings. No project managers.',
  },
  {
    n: '02', title: 'India-native by default.',
    body: 'GST at 18%. Mumbai jurisdiction. DPDP Act 2023 compliance. Indian Contract Act 1872. Not a configuration option — baked into every artifact the system produces.',
  },
  {
    n: '03', title: 'The loop never stops.',
    body: 'At 02:00 IST every night, a reasoning agent reads 30 days of agent logs, finds patterns, and proposes updates to its own rules. The company gets smarter while the founder sleeps.',
  },
]

export function HowItWorks() {
  return (
    <section id="how" style={{ minHeight: '100vh', background: '#0C0E10', padding: '120px 56px', display: 'flex', gap: '8%', flexWrap: 'wrap' }}>
      <div style={{ flex: '0 0 40%', minWidth: 280, position: 'sticky', top: 120, alignSelf: 'flex-start' }}>
        <div style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.16em', marginBottom: 20 }}>
          HOW IT WORKS
        </div>
        <h2 style={{ font: '900 56px/1.0 var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal' }}>
          One prompt. Full business.
        </h2>
      </div>

      <div style={{ flex: '1 1 52%', minWidth: 280, display: 'flex', flexDirection: 'column', gap: 56 }}>
        {ITEMS.map((item) => (
          <div key={item.n} style={{ borderTop: '0.5px solid rgba(164,216,255,0.12)', paddingTop: 28 }}>
            <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.50)', letterSpacing: '0.20em', marginBottom: 12 }}>
              {item.n}
            </div>
            <h3 style={{ font: '700 32px var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', marginBottom: 14, fontStyle: 'normal' }}>
              {item.title}
            </h3>
            <p style={{ font: '400 16px var(--font-body)', color: 'rgba(236,235,230,0.55)', lineHeight: 1.7, maxWidth: 520 }}>
              {item.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
