// web/app/signup/page.tsx
import { MagicLinkForm } from '@/components/auth/MagicLinkForm'

export default function SignupPage() {
  return (
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--void)' }}>
      <div style={{ width: 360 }}>
        <h1 style={{ font: '900 28px var(--font-serif)', color: 'var(--w)', marginBottom: 24 }}>
          Start forging.
        </h1>
        <MagicLinkForm mode="signup" />
      </div>
    </main>
  )
}
