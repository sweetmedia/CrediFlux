'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import { useAuth } from '@/lib/contexts/AuthContext';
import { Sidebar } from './Sidebar';
import { Loader2, Menu, X } from 'lucide-react';
import { PageTransition } from '@/components/ds';
import { useLocaleSync } from '@/i18n/client';

// Lazy-load the AI chat bubble so it's not in the initial bundle.
// It's only shown on authenticated pages and doesn't need SSR.
const AIChatBubble = dynamic(
  () => import('@/components/AIChatBubble').then((m) => m.AIChatBubble),
  { ssr: false }
);

interface AppLayoutProps {
  children: React.ReactNode;
}

// Pages that should not show the sidebar (public pages)
const PUBLIC_PAGES = ['/', '/login', '/register', '/forgot-password', '/select-tenant', '/reset-password'];

export function AppLayout({ children }: AppLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Keep the `locale` cookie in sync with the authenticated user's
  // preferred_language. next-intl reads it on the next SSR pass.
  useLocaleSync();

  const isPublicPage = PUBLIC_PAGES.includes(pathname);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  // Redirect to login if not authenticated and trying to access protected page
  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isPublicPage) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, isPublicPage, router]);

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-background">
        <Image
          src="/logo.svg"
          alt="CrediFlux"
          width={200}
          height={50}
          className="h-12 w-auto"
          priority
        />
        <Loader2 className="h-7 w-7 animate-spin text-primary" />
      </div>
    );
  }

  // If it's a public page, don't show sidebar
  if (isPublicPage) {
    return (
      <PageTransition>
        {children}
      </PageTransition>
    );
  }

  // If authenticated, show sidebar with content
  if (isAuthenticated) {
    return (
      <div className="min-h-screen bg-background">
        {/* Mobile hamburger header */}
        <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center gap-3 px-4 py-3 border-b bg-[var(--color-tenant-primary)]">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-md text-white/80 hover:text-white hover:bg-white/10 transition-colors"
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <Image
            src="/logo.svg"
            alt="CrediFlux"
            width={100}
            height={24}
            className="h-5 w-auto brightness-0 invert"
            priority
          />
        </div>

        {/* Backdrop overlay (mobile) */}
        {sidebarOpen && (
          <div
            className="lg:hidden fixed inset-0 z-40 bg-black/50 transition-opacity"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        {/* Content area */}
        <div className="lg:ml-[240px] pt-14 lg:pt-0">
          <PageTransition>
            {children}
          </PageTransition>
        </div>

        {/* AI Chat Bubble */}
        <AIChatBubble />
      </div>
    );
  }

  // If not authenticated and not a public page, show nothing (will redirect)
  return null;
}
