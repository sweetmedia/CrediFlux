import { Outlet, ScrollRestoration } from 'react-router';
import { Providers } from './providers';
import { AppLayout } from '@/components/layout/AppLayout';
import { TenantHostGuard } from '@/components/layout/TenantHostGuard';
import { Toaster } from '@/components/ui/sonner';

/**
 * Layout raíz de todas las rutas. Los metadatos y el script de apariencia
 * (antes `metadata` y `<AppearanceScript />`) están en `index.html`; las
 * fuentes en `app/fonts.css`.
 */
export default function RootLayout() {
  return (
    <Providers>
      <TenantHostGuard>
        <AppLayout>
          <Outlet />
        </AppLayout>
      </TenantHostGuard>
      <Toaster position="top-right" richColors closeButton duration={4000} />
      <ScrollRestoration />
    </Providers>
  );
}
