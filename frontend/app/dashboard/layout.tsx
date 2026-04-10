import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Dashboard',
  description: 'Panel principal con KPIs de cartera, cobranza y operación',
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return children
}
