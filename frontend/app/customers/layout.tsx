import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Clientes',
  description: 'Base de clientes con historial de préstamos y contactos',
}

export default function CustomersLayout({ children }: { children: React.ReactNode }) {
  return children
}
