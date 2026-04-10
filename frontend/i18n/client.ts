'use client'

import { useEffect } from 'react'

import { useAuth } from '@/lib/contexts/AuthContext'

/**
 * Client-side helper that syncs the `locale` cookie with the authenticated
 * user's preferred_language.
 *
 * Drop this into the AppShell once per session — it writes the cookie
 * when the user's preference changes so the next navigation's SSR picks
 * it up. The actual render locale is resolved on the server in
 * `i18n/request.ts`.
 */
export function useLocaleSync() {
  const { user } = useAuth()

  useEffect(() => {
    if (typeof document === 'undefined') return
    const preferred = user?.preferred_language ?? 'es'
    const current = document.cookie
      .split('; ')
      .find((row) => row.startsWith('locale='))
      ?.split('=')[1]

    if (current !== preferred) {
      // 1 year, subdomain-wide
      document.cookie = `locale=${preferred}; path=/; max-age=${60 * 60 * 24 * 365}; SameSite=Lax`
    }
  }, [user?.preferred_language])
}

/**
 * Read the current user's preferred language synchronously from the auth
 * context. Useful for locale-dependent client utilities (date formatters,
 * number formatters) that don't need next-intl's server-resolved locale.
 */
export function useLocale(): 'es' | 'en' {
  const { user } = useAuth()
  return (user?.preferred_language as 'es' | 'en') ?? 'es'
}
