import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Secuencias e-NCF',
  description: 'Gestión de secuencias de comprobantes fiscales electrónicos',
}

export default function SequencesLayout({ children }: { children: React.ReactNode }) {
  return children
}
