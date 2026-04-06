import type { Metadata } from 'next';
import { Inter, Space_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { AppLayout } from '@/components/layout/AppLayout';
import { NavigationProgress } from '@/components/NavigationProgress';
import { Suspense } from 'react';
import { Toaster } from '@/components/ui/sonner';

const inter = Inter({ subsets: ['latin'] });
const spaceMono = Space_Mono({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-space-mono',
});

export const metadata: Metadata = {
  title: {
    default: 'CrediFlux - Loan Management System',
    template: '%s | CrediFlux',
  },
  description: 'Multi-module SaaS platform for financial institutions',
  applicationName: 'CrediFlux',
  keywords: ['loan management', 'financial management', 'lending platform', 'SaaS'],
  authors: [{ name: 'CrediFlux Team' }],
  creator: 'CrediFlux',
  publisher: 'CrediFlux',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  openGraph: {
    title: 'CrediFlux - Loan Management System',
    description: 'Multi-module SaaS platform for financial institutions',
    siteName: 'CrediFlux',
    locale: 'es_ES',
    type: 'website',
  },
  twitter: {
    card: 'summary',
    title: 'CrediFlux - Loan Management System',
    description: 'Multi-module SaaS platform for financial institutions',
  },
  icons: {
    icon: [
      { url: '/icon.svg', type: 'image/svg+xml' },
      { url: '/icon.png', type: 'image/png' },
    ],
    apple: '/apple-icon.png',
  },
  manifest: '/manifest.json',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} ${spaceMono.variable}`}>
        <Providers>
          <Suspense fallback={null}>
            <NavigationProgress />
          </Suspense>
          <AppLayout>{children}</AppLayout>
          <Toaster position="top-right" richColors closeButton duration={4000} />
        </Providers>
      </body>
    </html>
  );
}
