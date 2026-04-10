'use client'

import { useEffect, useRef, type ReactNode } from 'react'
import { usePathname } from 'next/navigation'

interface PageTransitionProps {
  children: ReactNode
  variant?: 'slide' | 'fade'
}

/**
 * Unified GSAP page transition.
 *
 * Replaces the four variants from the old PageTransition.tsx with a single
 * component. Checks prefers-reduced-motion via gsap.matchMedia — when
 * reduced, it swaps content instantly with no animation.
 *
 * Durations follow DESIGN_SYSTEM.md §Motion: fast 150ms for exit,
 * base 300ms for entry.
 */
export function PageTransition({ children, variant = 'slide' }: PageTransitionProps) {
  const pathname = usePathname()
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    import('gsap').then(({ default: gsap }) => {
      if (!containerRef.current) return

      const mm = gsap.matchMedia()

      mm.add(
        {
          reduced: '(prefers-reduced-motion: reduce)',
          full: '(prefers-reduced-motion: no-preference)',
        },
        (ctx) => {
          if (ctx.conditions?.reduced) {
            // Instant swap for reduced motion
            gsap.set(containerRef.current, { opacity: 1, y: 0 })
            return
          }

          if (variant === 'fade') {
            gsap.fromTo(
              containerRef.current,
              { opacity: 0 },
              { opacity: 1, duration: 0.3, ease: 'power3.out' }
            )
          } else {
            gsap.fromTo(
              containerRef.current,
              { opacity: 0, y: 15 },
              { opacity: 1, y: 0, duration: 0.3, ease: 'power3.out' }
            )
          }
        }
      )

      return () => mm.revert()
    })
  }, [pathname, variant])

  return <div ref={containerRef}>{children}</div>
}
