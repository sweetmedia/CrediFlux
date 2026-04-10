'use client'

import { useEffect, useRef, useState } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'

/**
 * Top-of-page progress bar that animates in on every route change.
 * Uses tenant primary + sage tokens so it follows brand theming.
 */
export function NavigationProgress() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const progressRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [, setIsNavigating] = useState(false)

  useEffect(() => {
    if (!progressRef.current || !containerRef.current) return

    import('gsap').then((gsapModule) => {
      const gsap = gsapModule.default

      setIsNavigating(true)

      gsap.set(containerRef.current, { opacity: 1 })
      gsap.set(progressRef.current, { width: '0%' })

      gsap.to(progressRef.current, {
        width: '90%',
        duration: 0.5,
        ease: 'power3.out',
      })

      setTimeout(() => {
        gsap.to(progressRef.current, {
          width: '100%',
          duration: 0.2,
          ease: 'power1.in',
          onComplete: () => {
            gsap.to(containerRef.current, {
              opacity: 0,
              duration: 0.3,
              delay: 0.1,
              onComplete: () => {
                setIsNavigating(false)
              },
            })
          },
        })
      }, 300)
    })
  }, [pathname, searchParams])

  return (
    <div
      ref={containerRef}
      className="fixed top-0 left-0 right-0 z-[9999] h-1 bg-transparent pointer-events-none"
      style={{ opacity: 0 }}
    >
      <div
        ref={progressRef}
        className="h-full"
        style={{
          width: '0%',
          background:
            'linear-gradient(to right, var(--color-tenant-primary), var(--color-sage-500), var(--color-tenant-primary))',
          boxShadow: '0 0 12px rgba(22, 51, 0, 0.3)',
        }}
      />
    </div>
  )
}
