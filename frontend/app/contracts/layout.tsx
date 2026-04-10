import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Contratos',
  description: 'Gestión de contratos de préstamos y firma digital',
}

export default function ContractsLayout({ children }: { children: React.ReactNode }) {
  return children
}
