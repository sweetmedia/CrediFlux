import { useEffect, useState } from 'react';
import { useRouter, usePathname } from '@/lib/navigation';
import Image from '@/components/ui/image';
import { useAuth } from '@/lib/contexts/AuthContext';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { MobileNav, MobileTopBar } from './MobileNav';
import { useIsMobile } from './useIsMobile';
import { Loader2 } from 'lucide-react';
import { SimplePageTransition } from '@/components/PageTransition';
import { AIChatBubble } from '@/components/AIChatBubble';
import { useCan } from '@/lib/permissions';
import { esPaginaPublica } from './public-pages';
import './shell.css';

// Páginas con su propia barra fija abajo: sin barra inferior (D8).
const SIN_BARRA_INFERIOR = ['/payments/new', '/loans/new', '/collector'];

function esCampoDeTexto(el: EventTarget | null) {
  return el instanceof HTMLElement && el.matches('input:not([type=checkbox]):not([type=radio]):not([type=button]):not([type=submit]), textarea, select, [contenteditable=true]');
}

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const can = useCan();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const isMobile = useIsMobile();
  // Con el teclado abierto la barra inferior taparía el botón del formulario.
  const [escribiendo, setEscribiendo] = useState(false);

  const isPublicPage = esPaginaPublica(pathname);

  // Close sidebar on route change (mobile). Al enviar un formulario el campo
  // puede desmontarse sin blur (iOS): la barra inferior vuelve con la página nueva.
  useEffect(() => {
    setSidebarOpen(false);
    setEscribiendo(false);
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

  if (isAuthenticated) {
    const conBarraInferior = isMobile && !escribiendo && !SIN_BARRA_INFERIOR.includes(pathname);
    return (
      <div
        className="min-h-[100dvh] bg-background"
        data-bottom-nav={conBarraInferior || undefined}
        onFocus={(e) => esCampoDeTexto(e.target) && setEscribiendo(true)}
        onBlur={(e) => esCampoDeTexto(e.target) && setEscribiendo(false)}
      >
        {isMobile && (
          <div
            aria-hidden="true"
            className={`fixed inset-0 z-40 bg-black/40 transition-opacity duration-slow ease-out ${
              sidebarOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
            }`}
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <Sidebar drawer={isMobile} isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        <div className={isMobile ? (conBarraInferior ? 'm-content' : undefined) : 'ml-[240px]'}>
          {isMobile ? <MobileTopBar onMenu={() => setSidebarOpen(true)} /> : <Header />}
          <SimplePageTransition>{children}</SimplePageTransition>
        </div>

        {conBarraInferior && <MobileNav onMore={() => setSidebarOpen(true)} />}

        {/* El backend exige ai.access en el chat; sin él, ni se ofrece. */}
        {can('ai.access') && <AIChatBubble />}
      </div>
    );
  }

  // If not authenticated and not a public page, show nothing (will redirect)
  return null;
}
