'use client'

import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'cf_nav_expanded'
const DEFAULT_EXPANDED = ['overview', 'operation']

/**
 * Tracks which sidebar groups are expanded, persisting across reloads
 * via localStorage. Defaults match the most common layout: overview
 * and operation open, everything else collapsed.
 */
export function useNavigationState() {
  const [expandedGroups, setExpandedGroups] = useState<string[]>(DEFAULT_EXPANDED)
  const [hydrated, setHydrated] = useState(false)

  // Load from localStorage once on mount (avoiding SSR/hydration mismatch).
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored) as string[]
        if (Array.isArray(parsed)) setExpandedGroups(parsed)
      }
    } catch {
      // localStorage may be unavailable (private mode, SSR fallback, etc.)
    }
    setHydrated(true)
  }, [])

  const toggleGroup = useCallback((groupId: string) => {
    setExpandedGroups((prev) => {
      const next = prev.includes(groupId)
        ? prev.filter((g) => g !== groupId)
        : [...prev, groupId]
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      } catch {
        // ignore
      }
      return next
    })
  }, [])

  const isExpanded = useCallback(
    (groupId: string) => expandedGroups.includes(groupId),
    [expandedGroups]
  )

  return { expandedGroups, toggleGroup, isExpanded, hydrated }
}
