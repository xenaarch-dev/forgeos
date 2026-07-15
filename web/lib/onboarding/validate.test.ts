// web/lib/onboarding/validate.test.ts
import { describe, expect, it } from 'vitest'
import { validateStep } from './validate'

describe('validateStep', () => {
  it('rejects an empty name', () => {
    expect(validateStep('name', '  ')).toBe('This field is required.')
  })

  it('accepts a normal name', () => {
    expect(validateStep('name', 'Xena')).toBeNull()
  })

  it('rejects a name over 120 characters', () => {
    expect(validateStep('name', 'a'.repeat(121))).toBe('Keep it under 120 characters.')
  })

  it('never rejects the idea step, including empty (skip covers it)', () => {
    expect(validateStep('idea', '')).toBeNull()
  })
})
