import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Reportes DGII',
  description: 'Reportes 606 y 607 para presentación a la DGII',
}

export default function DgiiReportsLayout({ children }: { children: React.ReactNode }) {
  return children
}
