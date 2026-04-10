import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Comunicaciones',
  description: 'Centro de mensajería con clientes vía WhatsApp y email',
}

export default function CommunicationsLayout({ children }: { children: React.ReactNode }) {
  return children
}
