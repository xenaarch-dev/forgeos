// web/app/app/products/[id]/page.tsx
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { TEST_COUNT_PASSING } from '@/lib/forge/testCount'

const PRODUCTS: Record<string, { name: string; tagline: string; version: string; date: string }> = {
  contractforge: { name: 'ContractForge', tagline: 'AI contracts for Indian freelancers.', version: 'v2.1', date: 'JAN 11, 2026' },
}

export default function ProductDetailPage({ params }: { params: { id: string } }) {
  const product = PRODUCTS[params.id]
  if (!product) notFound()

  return (
    <div style={{ padding: 32, display: 'grid', gridTemplateColumns: '60% 1fr', gap: 40 }}>
      <div>
        <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.30)', marginBottom: 20 }}>
          <Link href="/app/products" style={{ color: 'rgba(236,235,230,0.30)' }}>Products</Link> / {product.name}
        </div>
        <h1 style={{ font: '900 48px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', letterSpacing: '-0.03em' }}>
          {product.name}
        </h1>
        <p style={{ font: '400 18px var(--font-body)', color: 'rgba(236,235,230,0.45)', marginTop: 10 }}>
          {product.tagline}
        </p>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 16, font: '400 9px var(--font-mono)' }}>
          <span style={{ color: '#A4D8FF' }}>• LIVE</span>
          <span style={{ color: 'rgba(236,235,230,0.35)' }}>{product.version}</span>
          <span style={{ color: 'rgba(236,235,230,0.35)' }}>{product.date}</span>
        </div>

        <div style={{ marginTop: 40 }}>
          <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.16em', marginBottom: 14 }}>
            AGENT ACTIVITY
          </div>
          <div className="glass" style={{ borderRadius: 4, padding: 18, font: '300 13px var(--font-body)', color: 'rgba(236,235,230,0.45)' }}>
            No recent activity logged for this product yet.
          </div>
        </div>

        <Link
          href={`/app/products/${params.id}/pipeline`}
          data-magnetic
          style={{ display: 'inline-block', marginTop: 32, background: '#A4D8FF', color: '#0C0E10', font: '400 9px var(--font-mono)', letterSpacing: '0.10em', padding: '14px 26px' }}
        >
          VIEW PIPELINE →
        </Link>
      </div>

      <div className="glass" style={{ borderRadius: 4, padding: 20, alignSelf: 'start' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {[
            { v: '₹0', l: 'MRR' },
            { v: `${TEST_COUNT_PASSING} ✓`, l: 'TESTS' },
            { v: '9', l: 'LEADS' },
            { v: '7', l: 'AGENTS' },
          ].map((m) => (
            <div key={m.l}>
              <div style={{ font: '700 24px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal' }}>{m.v}</div>
              <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(236,235,230,0.30)', letterSpacing: '0.12em', marginTop: 4 }}>{m.l}</div>
            </div>
          ))}
        </div>
        <div style={{ borderTop: '0.5px solid rgba(164,216,255,0.12)', marginTop: 20, paddingTop: 16, font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.45)' }}>
          NIGHTLY LOOP: NEXT RUN 02:00 IST
        </div>
      </div>
    </div>
  )
}
