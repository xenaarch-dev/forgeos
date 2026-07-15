import { completeOnboarding, skipOnboarding } from './actions'

export default function OnboardingPage({
  searchParams,
}: {
  searchParams: { error?: string }
}) {
  return (
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--void)' }}>
      <form action={completeOnboarding} style={{ width: 420, display: 'flex', flexDirection: 'column', gap: 20 }}>
        {searchParams.error && (
          <div style={{ color: 'var(--gold)', font: '400 12px var(--font-body)' }}>
            {searchParams.error}
          </div>
        )}
        <div style={{
          background: 'var(--glass-fill)',
          backdropFilter: 'var(--glass-blur)',
          border: '0.5px solid rgba(0,229,204,0.22)',
          borderRadius: 6,
          padding: 24,
        }}>
          <label style={{ display: 'block', font: '400 10px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.14em', marginBottom: 10 }}>
            YOUR NAME
          </label>
          <input
            name="fullName"
            required
            maxLength={120}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid rgba(0,229,204,0.3)',
              color: 'var(--w)',
              font: '400 18px var(--font-body)',
              padding: '6px 0',
            }}
          />
        </div>
        <div style={{
          background: 'var(--glass-fill)',
          backdropFilter: 'var(--glass-blur)',
          border: '0.5px solid rgba(0,229,204,0.22)',
          borderRadius: 6,
          padding: 24,
        }}>
          <label style={{ display: 'block', font: '400 10px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.14em', marginBottom: 10 }}>
            COMPANY NAME
          </label>
          <input
            name="companyName"
            maxLength={120}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid rgba(0,229,204,0.3)',
              color: 'var(--w)',
              font: '400 18px var(--font-body)',
              padding: '6px 0',
            }}
          />
        </div>
        <div style={{
          background: 'var(--glass-fill)',
          backdropFilter: 'var(--glass-blur)',
          border: '0.5px solid rgba(0,229,204,0.22)',
          borderRadius: 6,
          padding: 24,
        }}>
          <label style={{ display: 'block', font: '400 10px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.14em', marginBottom: 10 }}>
            FIRST PRODUCT IDEA (FEEDS SPEC.MD GENERATION)
          </label>
          <textarea
            name="idea"
            rows={3}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid rgba(0,229,204,0.3)',
              color: 'var(--w)',
              font: '400 15px var(--font-body)',
              padding: '6px 0',
              resize: 'none',
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            type="submit"
            style={{ flex: 1, background: 'var(--teal)', color: 'var(--void)', borderRadius: 4, padding: 14, font: '700 12px var(--font-body)', letterSpacing: '0.08em' }}
          >
            CONTINUE →
          </button>
          <button
            formAction={skipOnboarding}
            style={{ background: 'transparent', border: '0.5px solid rgba(240,237,232,0.2)', color: 'var(--w-dim)', borderRadius: 4, padding: 14, font: '400 12px var(--font-body)' }}
          >
            SKIP
          </button>
        </div>
      </form>
    </main>
  )
}
