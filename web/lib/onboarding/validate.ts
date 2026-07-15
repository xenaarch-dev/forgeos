// web/lib/onboarding/validate.ts
export type OnboardingStep = 'name' | 'company' | 'idea'

export function validateStep(step: OnboardingStep, value: string): string | null {
  if (step === 'idea') return null
  const trimmed = value.trim()
  if (trimmed.length === 0) return 'This field is required.'
  if (trimmed.length > 120) return 'Keep it under 120 characters.'
  return null
}
