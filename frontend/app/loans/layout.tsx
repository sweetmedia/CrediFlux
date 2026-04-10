import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Préstamos',
  description: 'Gestión de préstamos activos, pendientes y en mora',
}

export default function LoansLayout({ children }: { children: React.ReactNode }) {
  return children
}
