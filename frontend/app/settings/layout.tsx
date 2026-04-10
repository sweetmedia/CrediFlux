import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Configuración',
  description: 'Ajustes del tenant, usuarios y módulos',
}

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return children
}
