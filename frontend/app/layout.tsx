import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages } from 'next-intl/server';
import './globals.css';
import { Providers } from './providers';
import { AppLayout } from '@/components/layout/AppLayout';
import { NavigationProgress } from '@/components/NavigationProgress';
import { Suspense } from 'react';
import { Toaster } from '@/components/ui/sonner';

export const metadata: Metadata = {
  title: {
    default: 'CrediFlux — Gestión de préstamos',
    template: '%s | CrediFlux',
  },
  description: 'Sistema para gestionar préstamos, cobranza y facturación electrónica en financieras, cooperativas y casas de préstamo.',
  applicationName: 'CrediFlux',
  keywords: ['gestión de préstamos', 'cobranza', 'facturación electrónica', 'cooperativas', 'microfinancieras'],
  authors: [{ name: 'CrediFlux' }],
  creator: 'CrediFlux',
  publisher: 'CrediFlux',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  openGraph: {
    title: 'CrediFlux — Gestión de préstamos',
    description: 'Sistema para gestionar préstamos, cobranza y facturación electrónica.',
    siteName: 'CrediFlux',
    locale: 'es_DO',
    type: 'website',
  },
  twitter: {
    card: 'summary',
    title: 'CrediFlux — Gestión de préstamos',
    description: 'Sistema para gestionar préstamos, cobranza y facturación electrónica.',
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

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="font-sans antialiased">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <Providers>
            <Suspense fallback={null}>
              <NavigationProgress />
            </Suspense>
            <AppLayout>{children}</AppLayout>
            <Toaster position="top-right" richColors closeButton duration={4000} />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
