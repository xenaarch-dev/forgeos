// web/lib/auth/redirect.ts
const PUBLIC_ONLY_PATHS = ['/login', '/signup']
const GATED_PREFIXES = ['/app', '/onboarding']

export type RedirectInput = {
  session: boolean
  onboarded: boolean
  pathname: string
}

export function getRedirectPath({ session, onboarded, pathname }: RedirectInput): string | null {
  const isGated = GATED_PREFIXES.some((p) => pathname.startsWith(p))
  const isPublicOnly = PUBLIC_ONLY_PATHS.some((p) => pathname.startsWith(p))

  if (!session) {
    return isGated ? '/login' : null
  }
  if (isPublicOnly) {
    return '/app'
  }
  if (pathname.startsWith('/app') && !onboarded) {
    return '/onboarding'
  }
  return null
}
