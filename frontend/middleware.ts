import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Middleware to handle multi-tenant subdomain routing
 *
 * Blocks access to localhost:3000 (without subdomain) and redirects to
 * a tenant selection page or shows an error.
 */
export function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';

  // Allow localhost:3000 only for the tenant selector page and login
  if (hostname === 'localhost:3000' || hostname === 'localhost') {
    const pathname = request.nextUrl.pathname;

    // Allow access to tenant selector and public pages
    if (pathname === '/select-tenant' ||
        pathname === '/api' ||
        pathname.startsWith('/_next') ||
        pathname.startsWith('/static')) {
      return NextResponse.next();
    }

    // Redirect all other requests to tenant selector
    return NextResponse.redirect(new URL('/select-tenant', request.url));
  }

  // Allow all subdomain access (democompany.localhost, caproinsa.localhost, etc.)
  return NextResponse.next();
}

// Configure which routes the middleware runs on
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (public folder)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.svg|.*\\.png|.*\\.jpg).*)',
  ],
};
