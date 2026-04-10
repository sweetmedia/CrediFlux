import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Registrarse',
  description: 'Crear una cuenta nueva en CrediFlux',
}

export default function RegisterLayout({ children }: { children: React.ReactNode }) {
  return children
}
