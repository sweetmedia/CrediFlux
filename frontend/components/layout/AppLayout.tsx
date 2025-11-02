'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from '@/lib/contexts/AuthContext';
import { Sidebar } from './Sidebar';
import { Loader2 } from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
}

// Pages that should not show the sidebar (public pages)
const PUBLIC_PAGES = ['/', '/login', '/register', '/forgot-password', '/select-tenant', '/reset-password'];

export function AppLayout({ children }: AppLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();

  const isPublicPage = PUBLIC_PAGES.includes(pathname);

  // Redirect to login if not authenticated and trying to access protected page
  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isPublicPage) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, isPublicPage, router]);

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-slate-50">
        <Image
          src="/logo.svg"
          alt="CrediFlux"
          width={200}
          height={50}
          className="h-12 w-auto"
          priority
        />
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  // If it's a public page, don't show sidebar
  if (isPublicPage) {
    return <>{children}</>;
  }

  // If authenticated, show sidebar with content
  if (isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-50">
        <Sidebar />
        <div className="ml-64">
          {children}
        </div>
      </div>
    );
  }

  // If not authenticated and not a public page, show nothing (will redirect)
  return null;
}
