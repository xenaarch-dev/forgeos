'use client'

import { useState } from 'react'
import { MissionBar } from '@/components/global/MissionBar'
import { completeOnboarding, skipOnboarding } from './actions'

const STEPS = [
  { key: 'name', label: "What's your name?", field: 'fullName', placeholder: 'Xena Arch', required: true, textarea: false },
  { key: 'company', label: 'Name your company.', field: 'companyName', placeholder: 'Xenarch (optional)', required: false, textarea: false },
  { key: 'idea', label: 'Your first product idea.', field: 'idea', placeholder: 'e.g. AI contract generator for Indian freelancers', required: false, textarea: true },
] as const

export default function OnboardingPage({
  searchParams,
}: {
  searchParams: { error?: string }
}) {
  const [step, setStep] = useState(0)
  const progress = ((step + 1) / STEPS.length) * 100
  const current = STEPS[step]

  return (
    <main style={{ minHeight: '100vh', background: '#0C0E10', display: 'grid', placeItems: 'center', paddingTop: 26 }}>
      <MissionBar chapter="CH.00 // ONBOARDING" />

      <div style={{ position: 'fixed', top: 26, left: 0, right: 0, height: 2, background: 'rgba(164,216,255,0.15)', zIndex: 210 }}>
        <div style={{ height: '100%', width: `${progress}%`, background: '#A4D8FF', boxShadow: '0 0 8px rgba(164,216,255,0.6)', transition: 'width 0.4s var(--ease)' }} />
      </div>

      <form action={completeOnboarding} style={{ width: 440 }}>
        {searchParams.error && (
          <div style={{ color: 'var(--error)', font: '400 12px var(--font-mono)', marginBottom: 16 }}>
            {searchParams.error}
          </div>
        )}

        <div style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.20em', marginBottom: 12 }}>
          STEP {step + 1} / {STEPS.length}
        </div>

        {STEPS.map((s, i) => (
          <div key={s.key} className="glass" style={{ padding: 24, borderRadius: 6, marginBottom: 16, display: i === step ? 'block' : 'none' }}>
            <h2 style={{ font: '700 26px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', letterSpacing: '-0.03em', marginBottom: 16 }}>
              {s.label}
            </h2>
            <label style={{ display: 'block', font: '400 10px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.14em', marginBottom: 10 }}>
              {s.field.toUpperCase()}{!s.required && ' (OPTIONAL)'}
            </label>
            {s.textarea ? (
              <textarea
                name={s.field}
                rows={3}
                placeholder={s.placeholder}
                style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '1px solid rgba(164,216,255,0.30)', color: 'var(--warm-white)', font: '400 15px var(--font-body)', padding: '6px 0', resize: 'none' }}
              />
            ) : (
              <input
                name={s.field}
                required={s.required}
                maxLength={120}
                placeholder={s.placeholder}
                style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '1px solid rgba(164,216,255,0.30)', color: 'var(--warm-white)', font: '400 18px var(--font-body)', padding: '6px 0' }}
              />
            )}
          </div>
        ))}

        <div style={{ display: 'flex', gap: 12 }}>
          {step < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={() => setStep((s) => Math.min(s + 1, STEPS.length - 1))}
              data-magnetic
              style={{ flex: 1, background: '#A4D8FF', color: '#0C0E10', borderRadius: 2, padding: 14, font: '400 12px var(--font-mono)', letterSpacing: '0.14em' }}
            >
              NEXT →
            </button>
          ) : (
            <button
              type="submit"
              data-magnetic
              style={{ flex: 1, background: '#A4D8FF', color: '#0C0E10', borderRadius: 2, padding: 14, font: '400 12px var(--font-mono)', letterSpacing: '0.14em' }}
            >
              ENTER THE WAR ROOM →
            </button>
          )}
          <button
            formAction={skipOnboarding}
            style={{ background: 'transparent', border: '0.5px solid rgba(236,235,230,0.20)', color: 'rgba(236,235,230,0.55)', borderRadius: 2, padding: 14, font: '400 12px var(--font-mono)' }}
          >
            SKIP
          </button>
        </div>
      </form>
    </main>
  )
}
