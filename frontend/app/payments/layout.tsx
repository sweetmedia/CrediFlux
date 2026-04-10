import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Pagos',
  description: 'Registro y consulta de pagos recibidos',
}

export default function PaymentsLayout({ children }: { children: React.ReactNode }) {
  return children
}
