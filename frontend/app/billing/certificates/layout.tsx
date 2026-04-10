import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Certificados',
  description: 'Certificados digitales para firma de e-CF',
}

export default function CertificatesLayout({ children }: { children: React.ReactNode }) {
  return children
}
