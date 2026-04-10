import { getRequestConfig } from 'next-intl/server'
import { cookies } from 'next/headers'

/**
 * next-intl request config — runs on the server for every request.
 *
 * IMPORTANT: this dashboard does NOT use a locale URL prefix (no /es/...
 * or /en/...). The subdomain-based multi-tenant middleware stays intact.
 * Locale is resolved from:
 *   1. `locale` cookie (set client-side after login based on
 *      user.preferred_language)
 *   2. fallback 'es' (Spanish is the default for all tenants in RD)
 */

const SUPPORTED_LOCALES = ['es', 'en'] as const
type Locale = (typeof SUPPORTED_LOCALES)[number]

export default getRequestConfig(async () => {
  const cookieStore = await cookies()
  const cookieLocale = cookieStore.get('locale')?.value as Locale | undefined

  const locale: Locale =
    cookieLocale && SUPPORTED_LOCALES.includes(cookieLocale) ? cookieLocale : 'es'

  return {
    locale,
    messages: (await import(`../messages/${locale}/common.json`)).default,
  }
})
