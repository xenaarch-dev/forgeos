export function chapterFromRoute(pathname: string): string {
  if (pathname.endsWith('/pipeline')) return 'CH.11 // PIPELINE'
  if (/^\/app\/products\/[^/]+$/.test(pathname)) return 'CH.10 // PRODUCT'
  if (pathname.startsWith('/app/products')) return 'CH.09 // PRODUCTS'
  if (pathname.startsWith('/app/agents')) return 'CH.12 // AGENTS'
  if (pathname.startsWith('/app/artifacts')) return 'CH.13 // ARTIFACTS'
  if (pathname.startsWith('/app/command')) return 'CH.14 // COMMAND'
  if (pathname.startsWith('/app/billing')) return 'CH.15 // BILLING'
  if (pathname.startsWith('/app/settings')) return 'CH.16 // SETTINGS'
  if (pathname === '/app') return 'CH.08 // WAR ROOM'
  return 'CH.08 // WAR ROOM'
}
