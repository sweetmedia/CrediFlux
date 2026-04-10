'use client'

import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'
import { Reveal } from './Reveal'

interface Breadcrumb {
  label: string
  href?: string
}

interface PageHeaderProps {
  title: string
  description?: string
  breadcrumbs?: Breadcrumb[]
  actions?: ReactNode
  className?: string
}

/**
 * Canonical page header for dashboard pages.
 *
 * Title uses the display font (ABC Whyte). Actions slot is right-aligned
 * for primary CTAs. Animates in via <Reveal fadeInUp> on mount.
 */
export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <Reveal animation="fadeInUp" duration={0.4}>
      <div
        className={cn(
          'flex flex-col gap-3 pb-6 border-b border-border/50',
          className
        )}
      >
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav
            aria-label="Breadcrumb"
            className="flex items-center gap-1.5 text-xs text-muted-foreground"
          >
            {breadcrumbs.map((crumb, idx) => (
              <span key={idx} className="flex items-center gap-1.5">
                {idx > 0 && <ChevronRight className="h-3 w-3" />}
                {crumb.href ? (
                  <Link
                    href={crumb.href}
                    className="hover:text-foreground transition-colors"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span className={idx === breadcrumbs.length - 1 ? 'text-foreground' : ''}>
                    {crumb.label}
                  </span>
                )}
              </span>
            ))}
          </nav>
        )}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h1 className="cf-font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              {title}
            </h1>
            {description && (
              <p className="mt-1 text-sm text-muted-foreground">{description}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      </div>
    </Reveal>
  )
}
