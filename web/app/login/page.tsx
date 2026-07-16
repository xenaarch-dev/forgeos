// web/app/login/page.tsx
import Link from 'next/link'
import { AuthShell } from '@/components/auth/AuthShell'
import { MagicLinkForm } from '@/components/auth/MagicLinkForm'

export default function LoginPage() {
  return (
    <AuthShell tagline="AGENTS RUNNING. FOUNDER THINKING.">
      <div style={{ font: '400 9px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.20em', marginBottom: 12 }}>
        SIGN IN
      </div>
      <h1 style={{ font: '900 42px var(--font-display)', letterSpacing: '-0.053em', color: '#ECEBE6', fontStyle: 'normal', marginBottom: 10 }}>
        Welcome back.
      </h1>
      <p style={{ font: '300 16px var(--font-body)', color: 'rgba(236,235,230,0.45)', marginBottom: 28 }}>
        Your agents kept running.
      </p>
      <MagicLinkForm mode="login" />
      <div style={{ marginTop: 24, font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.25)', letterSpacing: '0.10em' }}>
        NO ACCOUNT? <Link href="/signup" style={{ color: '#A4D8FF' }}>→ START BUILDING</Link>
      </div>
    </AuthShell>
  )
}
