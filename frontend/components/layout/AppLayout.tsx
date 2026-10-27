import { useEffect, useState } from 'react';
import { useRouter, usePathname } from '@/lib/navigation';
import Image from '@/components/ui/image';
import { useAuth } from '@/lib/contexts/AuthContext';
import { Sidebar } from './Sidebar';
import { Loader2, Menu, X } from 'lucide-react';
import { SimplePageTransition } from '@/components/PageTransition';
import { AIChatBubble } from '@/components/AIChatBubble';
import { esPaginaPublica } from './public-pages';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isPublicPage = esPaginaPublica(pathname);

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
      <SimplePageTransition>
        {children}
      </SimplePageTransition>
    );
  }

  // If authenticated, show sidebar with content
  if (isAuthenticated) {
    return (
      <div className="min-h-[100dvh] bg-background">
        {/* Mobile hamburger header */}
        <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center gap-3 px-4 py-3 border-b bg-tenant">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label={sidebarOpen ? 'Cerrar menú' : 'Abrir menú'}
            aria-expanded={sidebarOpen}
            aria-controls="app-sidebar"
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
        <div
          aria-hidden="true"
          className={`lg:hidden fixed inset-0 z-40 bg-black/40 transition-opacity duration-slow ease-out ${
            sidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
          onClick={() => setSidebarOpen(false)}
        />

        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        {/* Content area */}
        <div className="lg:ml-[240px] pt-14 lg:pt-0">
          <SimplePageTransition>
            {children}
          </SimplePageTransition>
        </div>

        {/* AI Chat Bubble */}
        <AIChatBubble />
      </div>
    );
  }

  // If not authenticated and not a public page, show nothing (will redirect)
  return null;
}
