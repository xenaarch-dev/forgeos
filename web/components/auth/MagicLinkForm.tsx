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
      <div style={{ color: 'var(--warm-white)', font: '400 14px var(--font-body)', lineHeight: 1.6 }}>
        Check <strong>{email}</strong> for a sign-in link.
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <label style={{ display: 'block', font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.40)', letterSpacing: '0.16em', marginBottom: 8 }}>
          EMAIL
        </label>
        <input
          type="email"
          required
          placeholder="x@xenarch.in"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{
            width: '100%', background: 'var(--glass-bg)', border: '0.5px solid rgba(164,216,255,0.25)',
            borderRadius: 2, padding: '12px 14px', color: 'var(--warm-white)', font: '400 12px var(--font-mono)',
          }}
        />
      </div>
      <button
        type="submit"
        disabled={status === 'sending'}
        data-magnetic
        style={{
          width: '100%', background: '#A4D8FF', color: '#0C0E10', borderRadius: 2, padding: '13px 14px',
          font: '400 12px var(--font-mono)', letterSpacing: '0.20em', opacity: status === 'sending' ? 0.6 : 1,
        }}
      >
        {status === 'sending' ? 'SENDING…' : mode === 'login' ? 'SEND LOGIN LINK →' : 'SEND SIGNUP LINK →'}
      </button>
      {status === 'error' && (
        <div style={{ color: 'var(--error)', font: '400 12px var(--font-body)' }}>
          Something went wrong sending the link. Try again.
        </div>
      )}
    </form>
  )
}
