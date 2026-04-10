import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Calculadora',
  description: 'Simulador de cuotas, amortización e intereses',
}

export default function CalculatorLayout({ children }: { children: React.ReactNode }) {
  return children
}
