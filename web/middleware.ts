// web/middleware.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'
import { getRedirectPath } from '@/lib/auth/redirect'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          response = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  let onboarded = false
  if (user) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('onboarded_at')
      .eq('id', user.id)
      .maybeSingle()
    onboarded = Boolean(profile?.onboarded_at)
  }

  const redirect = getRedirectPath({
    session: Boolean(user),
    onboarded,
    pathname: request.nextUrl.pathname,
  })

  if (redirect) {
    const url = request.nextUrl.clone()
    url.pathname = redirect
    return NextResponse.redirect(url)
  }

  return response
}

export const config = {
  matcher: ['/app/:path*', '/onboarding/:path*', '/login', '/signup'],
}
