// web/app/signup/page.tsx
import Link from 'next/link'
import { AuthShell } from '@/components/auth/AuthShell'
import { MagicLinkForm } from '@/components/auth/MagicLinkForm'

export default function SignupPage() {
  return (
    <AuthShell tagline="DAY 01 STARTS NOW.">
      <div style={{ font: '400 9px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.20em', marginBottom: 12 }}>
        JOIN THE MESH
      </div>
      <h1 style={{ font: '900 42px var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 10 }}>
        Start building.
      </h1>
      <p style={{ font: '300 16px var(--font-body)', color: 'rgba(236,235,230,0.45)', marginBottom: 28 }}>
        Day 01 starts now.
      </p>
      <MagicLinkForm mode="signup" />
      <div style={{ marginTop: 24, font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.25)', letterSpacing: '0.10em' }}>
        ALREADY BUILDING? <Link href="/login" style={{ color: '#A4D8FF' }}>→ SIGN IN</Link>
      </div>
    </AuthShell>
  )
}
