import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token')
  const { pathname } = request.nextUrl

  // Define paths
  const isAuthPage = pathname.startsWith('/auth/')
  const isProtectedPage = pathname.startsWith('/dashboard')

  // 1. If user is on an auth page and has a token -> Allow access (don't redirect)
  // This allows users to switch accounts or re-login if they want
  // if (isAuthPage && token) {
  //   return NextResponse.redirect(new URL('/dashboard', request.url))
  // }

  // 2. If user is on a protected page (dashboard) and has NO token -> Redirect to Home
  if (isProtectedPage && !token) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  // Allow request to proceed (home page is public, dashboard requires auth)
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
