import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Cobrador Móvil',
  description: 'Panel del cobrador en campo con ubicaciones y visitas',
}

export default function CollectorLayout({ children }: { children: React.ReactNode }) {
  return children
}
