import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Equipo',
  description: 'Gestión de usuarios y roles del equipo',
}

export default function UsersLayout({ children }: { children: React.ReactNode }) {
  return children
}
