import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Facturación',
  description: 'Facturación electrónica e-CF y reportes DGII',
}

export default function BillingLayout({ children }: { children: React.ReactNode }) {
  return children
}
