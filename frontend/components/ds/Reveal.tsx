'use client'

import { useEffect, useRef, type ReactNode } from 'react'

type AnimationType = 'fadeIn' | 'fadeInUp' | 'fadeInLeft' | 'fadeInRight' | 'scaleIn'

interface RevealProps {
  children: ReactNode
  animation?: AnimationType
  delay?: number
  duration?: number
  stagger?: boolean
  staggerAmount?: number
  className?: string
}

const animationConfigs: Record<AnimationType, { from: object; to: object }> = {
  fadeIn: {
    from: { opacity: 0 },
    to: { opacity: 1 },
  },
  fadeInUp: {
    from: { opacity: 0, y: 20 },
    to: { opacity: 1, y: 0 },
  },
  fadeInLeft: {
    from: { opacity: 0, x: -20 },
    to: { opacity: 1, x: 0 },
  },
  fadeInRight: {
    from: { opacity: 0, x: 20 },
    to: { opacity: 1, x: 0 },
  },
  scaleIn: {
    from: { opacity: 0, scale: 0.95 },
    to: { opacity: 1, scale: 1 },
  },
}

/**
 * Declarative GSAP reveal wrapper.
 *
 * Honors prefers-reduced-motion. When stagger is true, each direct child
 * animates in sequence. Durations come from DESIGN_SYSTEM §10 defaults.
 */
export function Reveal({
  children,
  animation = 'fadeInUp',
  delay = 0,
  duration = 0.3,
  stagger = false,
  staggerAmount = 0.08,
  className,
}: RevealProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return

    // Honor prefers-reduced-motion — skip animation entirely.
    if (
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return
    }

    const config = animationConfigs[animation]

    import('gsap').then(({ default: gsap }) => {
      if (!ref.current) return
      const target = stagger ? ref.current.children : ref.current
      gsap.fromTo(target, config.from, {
        ...config.to,
        duration,
        delay,
        ease: 'power3.out',
        ...(stagger ? { stagger: staggerAmount } : {}),
      })
    })
  }, [animation, delay, duration, stagger, staggerAmount])

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  )
}
