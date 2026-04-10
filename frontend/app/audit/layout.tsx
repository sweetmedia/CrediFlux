import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Auditoría',
  description: 'Registro de auditoría y trazabilidad del sistema',
}

export default function AuditLayout({ children }: { children: React.ReactNode }) {
  return children
}
