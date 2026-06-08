'use client'

export default function Nav() {
  return (
    <nav
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        background: 'rgba(6,13,8,0.95)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        borderBottom: '1px solid var(--bd)',
        padding: '16px 40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div
          style={{
            width: 18,
            height: 18,
            border: '1px solid var(--cel)',
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            fontSize: '9px',
            letterSpacing: '0.20em',
            color: 'var(--cel)',
          }}
        >
          FORGEOS
        </span>
      </div>

      {/* Nav links — hidden below sm (640px) */}
      <div className="hidden sm:flex items-center gap-6">
        {['Docs', 'Agents', 'GBrain', 'Products'].map((link) => (
          <a key={link} href="#" className="label" style={{ cursor: 'pointer' }}>
            {link}
          </a>
        ))}
      </div>

      {/* Right side */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <a
          href="https://github.com/xenaarch-dev/forgeos"
          target="_blank"
          rel="noopener noreferrer"
          className="label"
          style={{ cursor: 'pointer' }}
        >
          ↗ GitHub
        </a>
        <button
          style={{
            background: 'var(--cel)',
            color: 'var(--bg)',
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            fontWeight: 700,
            padding: '6px 14px',
            letterSpacing: '0.10em',
          }}
        >
          Install →
        </button>
      </div>
    </nav>
  )
}
