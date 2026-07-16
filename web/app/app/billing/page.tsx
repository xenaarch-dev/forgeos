export default function BillingPage() {
  return (
    <div style={{ padding: 32, maxWidth: 1100 }}>
      <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', letterSpacing: '-0.03em', marginBottom: 32 }}>
        Billing
      </h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div className="glass" style={{ borderRadius: 4, padding: 28, borderTop: '2px solid #A4D8FF' }}>
          <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.16em', marginBottom: 14 }}>
            CURRENT PLAN
          </div>
          <div style={{ font: '900 38px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal' }}>FOUNDER SOLO</div>
          <div style={{ font: '900 56px var(--font-display)', color: '#A4D8FF', fontStyle: 'normal', marginTop: 6 }}>₹2,499/mo</div>
          <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.35)', letterSpacing: '0.08em', marginTop: 10 }}>
            RENEWS JULY 27, 2026
          </div>

          <div style={{ marginTop: 28 }}>
            <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.40)', letterSpacing: '0.10em', marginBottom: 8 }}>
              CONTRACTS GENERATED
            </div>
            <div style={{ height: 2, background: 'rgba(164,216,255,0.15)' }}>
              <div style={{ height: '100%', width: '2%', background: '#A4D8FF' }} />
            </div>
            <div style={{ font: '400 9px var(--font-mono)', color: 'rgba(236,235,230,0.45)', marginTop: 6 }}>0 / —</div>
          </div>

          <button className="glass" style={{ marginTop: 24, width: '100%', padding: '12px 0', borderRadius: 3, font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.08em' }}>
            MANAGE SUBSCRIPTION →
          </button>
        </div>

        <div className="glass" style={{ borderRadius: 4, padding: 28, opacity: 0.6 }}>
          <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.45)', letterSpacing: '0.16em', marginBottom: 14 }}>
            COMING SOON
          </div>
          <div style={{ font: '900 28px var(--font-display)', color: 'rgba(236,235,230,0.55)', fontStyle: 'normal' }}>FORGEOS AGENCY</div>
          <div style={{ font: '900 38px var(--font-display)', color: 'rgba(164,216,255,0.45)', fontStyle: 'normal', marginTop: 6 }}>₹9,999/mo</div>
          <p style={{ font: '300 13px var(--font-body)', color: 'rgba(236,235,230,0.40)', marginTop: 16, lineHeight: 1.6 }}>
            Multi-workspace · 10 client seats · White-label artifacts · Priority mesh
          </p>
          <button className="glass" style={{ marginTop: 24, width: '100%', padding: '12px 0', borderRadius: 3, font: '400 9px var(--font-mono)', color: 'rgba(236,235,230,0.55)', letterSpacing: '0.08em' }}>
            JOIN WAITLIST
          </button>
        </div>
      </div>

      <div style={{ marginTop: 40 }}>
        <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.16em', marginBottom: 16 }}>
          INVOICE HISTORY
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '0.5px solid rgba(164,216,255,0.12)' }}>
              {['DATE', 'AMOUNT', 'STATUS', 'INVOICE'].map((h) => (
                <th key={h} style={{ textAlign: 'left', padding: '10px 0', font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.16em' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
        </table>
        <div style={{ textAlign: 'center', padding: '40px 0', font: '400 9px var(--font-mono)', color: 'rgba(236,235,230,0.20)' }}>
          NO INVOICES YET. FIRST CUSTOMER INCOMING.
        </div>
      </div>
    </div>
  )
}
