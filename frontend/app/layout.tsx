import type { Metadata } from 'next';
import localFont from 'next/font/local';
import './globals.css';
import { Providers } from './providers';
import { AppLayout } from '@/components/layout/AppLayout';
import { Toaster } from '@/components/ui/sonner';
import { AppearanceScript } from '@/lib/design-system/AppearanceProvider';

// Brand faces (branding/fonts). Whyte is a trial license — see branding/fonts/LICENSE.md.
const whyte = localFont({
  src: [
    { path: './fonts/ABCWhyte-Regular-Trial.woff2', weight: '400', style: 'normal' },
    { path: './fonts/ABCWhyte-Medium-Trial.woff2', weight: '500', style: 'normal' },
    { path: './fonts/ABCWhyte-Bold-Trial.woff2', weight: '700', style: 'normal' },
    { path: './fonts/ABCWhyte-Black-Trial.woff2', weight: '900', style: 'normal' },
  ],
  variable: '--font-display',
  display: 'swap',
});
const jakarta = localFont({
  src: [
    { path: './fonts/PlusJakartaSans-normal-latin.woff2', weight: '200 800', style: 'normal' },
    { path: './fonts/PlusJakartaSans-italic-latin.woff2', weight: '200 800', style: 'italic' },
  ],
  variable: '--font-sans',
  display: 'swap',
});
const whyteMono = localFont({
  src: './fonts/ABCWhyteMonoInktrapVariable-Trial.woff2',
  weight: '100 900',
  variable: '--font-mono',
  display: 'swap',
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
    <html lang="es" suppressHydrationWarning>
      <head>
        <AppearanceScript />
      </head>
      <body className={`${whyte.variable} ${jakarta.variable} ${whyteMono.variable} font-sans`}>
        <Providers>
          <AppLayout>{children}</AppLayout>
          <Toaster position="top-right" richColors closeButton duration={4000} />
        </Providers>
      </body>
    </html>
  );
}
