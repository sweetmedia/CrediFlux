import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Caja',
  description: 'Gestión de efectivo, apertura y cierre diario',
}

export default function CashboxLayout({ children }: { children: React.ReactNode }) {
  return children
}
