// web/components/auth/MagicLinkForm.tsx
'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'

export function MagicLinkForm({ mode }: { mode: 'login' | 'signup' }) {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setStatus('sending')
    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    })
    setStatus(error ? 'error' : 'sent')
  }

  if (status === 'sent') {
    return (
      <div style={{ color: 'var(--w)', font: '400 14px var(--font-body)' }}>
        Check {email} for a sign-in link.
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <input
        type="email"
        required
        placeholder="you@company.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        style={{
          background: 'var(--glass-fill)',
          border: '0.5px solid rgba(0,229,204,0.3)',
          borderRadius: 4,
          padding: '12px 14px',
          color: 'var(--w)',
          font: '400 14px var(--font-body)',
        }}
      />
      <button
        type="submit"
        disabled={status === 'sending'}
        style={{
          background: 'var(--teal)',
          color: 'var(--void)',
          borderRadius: 4,
          padding: '12px 14px',
          font: '700 12px var(--font-body)',
          letterSpacing: '0.08em',
        }}
      >
        {status === 'sending' ? 'SENDING…' : mode === 'login' ? 'SEND LOGIN LINK →' : 'SEND SIGNUP LINK →'}
      </button>
      {status === 'error' && (
        <div style={{ color: 'var(--gold)', font: '400 12px var(--font-body)' }}>
          Something went wrong sending the link. Try again.
        </div>
      )}
    </form>
  )
}
