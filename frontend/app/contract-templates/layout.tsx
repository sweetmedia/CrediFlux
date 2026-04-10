import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Plantillas de Contratos',
  description: 'Plantillas reutilizables para generación de contratos',
}

export default function ContractTemplatesLayout({ children }: { children: React.ReactNode }) {
  return children
}
