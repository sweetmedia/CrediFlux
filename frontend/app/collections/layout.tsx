import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Cobranza',
  description: 'Seguimiento de cobranza, recordatorios y reportes',
}

export default function CollectionsLayout({ children }: { children: React.ReactNode }) {
  return children
}
