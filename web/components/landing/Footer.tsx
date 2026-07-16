const COLUMNS = [
  { title: 'PRODUCTS', links: [{ label: 'ContractForge', href: 'https://contractforge.co.in' }, { label: 'The Agent Mesh', href: '#agents' }, { label: 'War Room', href: '/app' }] },
  { title: 'COMPANY', links: [{ label: 'Manifesto', href: '#mission' }, { label: 'Build Log', href: '/app/artifacts' }, { label: 'X / Twitter', href: 'https://x.com/xenaarch' }] },
  { title: 'LEGAL', links: [{ label: 'Terms', href: '/terms' }, { label: 'Privacy · DPDP 2023', href: '/privacy' }] },
]

export function Footer() {
  return (
    <footer style={{ background: '#070809', borderTop: '0.5px solid rgba(164,216,255,0.08)', padding: '56px 56px 40px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 48, flexWrap: 'wrap' }}>
        <div>
          <div style={{ font: '900 28px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal' }}>ForgeOS</div>
          <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(236,235,230,0.25)', letterSpacing: '0.20em', marginTop: 8 }}>
            AUTONOMOUS BUSINESS OS
          </div>
          <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(236,235,230,0.18)', letterSpacing: '0.12em', marginTop: 4 }}>
            XENARCH · MUMBAI · INDIA · 2026
          </div>
        </div>
        <div style={{ display: 'flex', gap: 56, flexWrap: 'wrap' }}>
          {COLUMNS.map((col) => (
            <div key={col.title}>
              <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.30)', letterSpacing: '0.16em', marginBottom: 14 }}>
                {col.title}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {col.links.map((l) => (
                  <a key={l.label} href={l.href} style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.30)' }}>
                    {l.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ marginTop: 40, paddingTop: 20, borderTop: '0.5px dashed rgba(164,216,255,0.08)', textAlign: 'center' }}>
        <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(236,235,230,0.18)' }}>
          © 2026 XENARCH. AGENTS RUNNING. FOUNDER THINKING.
        </div>
      </div>
    </footer>
  )
}
