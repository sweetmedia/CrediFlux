import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Asistente AI',
  description: 'Asistente inteligente para consultas y análisis',
}

export default function AILayout({ children }: { children: React.ReactNode }) {
  return children
}
