// web/lib/auth/redirect.test.ts
import { describe, expect, it } from 'vitest'
import { getRedirectPath } from './redirect'

describe('getRedirectPath', () => {
  it('sends unauthenticated users hitting /app to /login', () => {
    expect(getRedirectPath({ session: false, onboarded: false, pathname: '/app' })).toBe('/login')
  })

  it('sends unauthenticated users hitting /onboarding to /login', () => {
    expect(getRedirectPath({ session: false, onboarded: false, pathname: '/onboarding' })).toBe('/login')
  })

  it('does not redirect unauthenticated users on public marketing pages', () => {
    expect(getRedirectPath({ session: false, onboarded: false, pathname: '/' })).toBeNull()
  })

  it('sends authenticated, un-onboarded users hitting /app to /onboarding', () => {
    expect(getRedirectPath({ session: true, onboarded: false, pathname: '/app/products' })).toBe('/onboarding')
  })

  it('sends authenticated, onboarded users away from /login to /app', () => {
    expect(getRedirectPath({ session: true, onboarded: true, pathname: '/login' })).toBe('/app')
  })

  it('does not redirect authenticated, onboarded users already inside /app', () => {
    expect(getRedirectPath({ session: true, onboarded: true, pathname: '/app/agents' })).toBeNull()
  })

  it('sends authenticated, onboarded users away from /onboarding to /app', () => {
    expect(getRedirectPath({ session: true, onboarded: true, pathname: '/onboarding' })).toBe('/app')
  })

  it('does not redirect authenticated, un-onboarded users away from /onboarding', () => {
    expect(getRedirectPath({ session: true, onboarded: false, pathname: '/onboarding' })).toBeNull()
  })
})
