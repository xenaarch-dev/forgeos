// web/app/app/products/page.tsx
import Link from 'next/link'

export default function ProductsPage() {
  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 40 }}>
        <div>
          <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', letterSpacing: '-0.03em' }}>
            Products
          </h1>
          <p style={{ font: '400 14px var(--font-body)', color: 'rgba(236,235,230,0.45)', marginTop: 8 }}>
            All products built and managed by ForgeOS.
          </p>
        </div>
        <Link
          href="/app/command"
          className="glass"
          data-magnetic
          style={{ padding: '10px 18px', borderRadius: 3, font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.10em' }}
        >
          + BUILD NEW PRODUCT
        </Link>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20 }}>
        <Link
          href="/app/products/contractforge"
          className="glass"
          style={{ display: 'block', padding: 24, borderRadius: 4, borderTop: '2px solid #A4D8FF' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <span style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.10em' }}>• LIVE</span>
            <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.30)' }}>JAN 11, 2026</span>
          </div>
          <h2 style={{ font: '900 32px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 10 }}>
            ContractForge
          </h2>
          <p style={{ font: '300 13px var(--font-body)', color: 'rgba(236,235,230,0.45)', marginBottom: 20 }}>
            AI contracts for Indian freelancers. GST-compliant.
          </p>
          <div style={{ display: 'flex', gap: 20, marginBottom: 20, font: '400 10px var(--font-mono)', color: 'rgba(236,235,230,0.45)' }}>
            <span>₹0 MRR</span>
            <span>276 TESTS ✓</span>
            <span>7 AGENTS</span>
          </div>
          <span style={{ font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.08em' }}>VIEW DETAILS →</span>
        </Link>

        <Link
          href="/app/command"
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 180,
            border: '1px dashed rgba(164,216,255,0.15)', borderRadius: 4,
          }}
        >
          <span style={{ font: '400 9px var(--font-mono)', color: 'rgba(164,216,255,0.45)', letterSpacing: '0.10em' }}>
            + BUILD WITH FORGEOS
          </span>
        </Link>
      </div>
    </div>
  )
}
