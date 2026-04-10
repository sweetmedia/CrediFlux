'use client'

import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface ReportProps {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
}

/**
 * Stub for the PDF report component.
 *
 * F2 renders a simple styled container. F4 will wire this up to a PDF
 * generation pipeline (likely react-pdf or a backend render endpoint)
 * and expand the API with headers, footers, page breaks, and data
 * sections.
 *
 * See DESIGN_SYSTEM.md §Reports for the target contract.
 */
export function Report({ title, subtitle, children, className }: ReportProps) {
  return (
    <div
      className={cn(
        'cf-report rounded-lg border bg-card p-8 print:border-0 print:p-0',
        className
      )}
    >
      <header className="mb-6 border-b pb-4">
        <h1 className="cf-font-display text-2xl font-bold text-foreground">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        )}
      </header>
      <div className="space-y-4">{children}</div>
    </div>
  )
}
