import { useSearchParams } from '@/lib/navigation';
import { ArrowLeft, ShieldX } from 'lucide-react';
import Link from '@/lib/navigation/link';

/** Sólo rutas internas: `/algo`, nunca `//host`, `/\host` ni URLs absolutas. */
function rutaInterna(url: string | null): string {
  return url && /^\/(?![/\\])/.test(url) ? url : '/dashboard';
}

export default function AccessDeniedPage() {
  const searchParams = useSearchParams();
  const reason = searchParams.get('reason') || 'No tienes permisos para acceder a esta página.';
  const requiredPermission = searchParams.get('permission');
  const returnUrl = rutaInterna(searchParams.get('returnUrl'));

  return (
    <main className="cf-root min-h-[calc(100dvh-56px)] bg-cream px-4 py-10 sm:px-8">
      <div className="mx-auto grid max-w-[1100px] gap-12 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <div className="mb-4 flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-flame-700">
            <ShieldX className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Error 403</span>
          </div>
          <h1 className="font-display text-[38px] font-black leading-none tracking-tight text-forest-900">
            No tienes permiso para esto
          </h1>
          <p className="mt-4 max-w-[52ch] text-[15px] leading-relaxed text-sage-600">{reason}</p>

          {requiredPermission && (
            <dl className="mt-8 border-t border-forest-900/10">
              <div className="flex items-baseline justify-between gap-6 border-b border-forest-900/10 py-3">
                <dt className="text-[13px] text-sage-600">Permiso requerido</dt>
                <dd className="font-mono text-[13px] text-forest-900">{requiredPermission}</dd>
              </div>
            </dl>
          )}

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href={returnUrl} className="cf-btn cf-btn--primary h-11">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Volver
            </Link>
            <Link href="/dashboard" className="cf-btn cf-btn--secondary h-11">
              Ir al dashboard
            </Link>
          </div>
        </div>

        <aside className="lg:col-span-5">
          <h2 className="mb-4 font-mono text-[10px] uppercase tracking-widest text-sage-600">¿Qué puedes hacer?</h2>
          <ol className="space-y-4 border-t border-forest-900/10 pt-4 text-[14px] text-forest-900">
            <li>1. Pide el permiso al administrador de tu financiera.</li>
            <li>2. Revisa que entraste con la cuenta correcta.</li>
            <li>3. Vuelve a una página donde sí tengas acceso.</li>
          </ol>
        </aside>
      </div>
    </main>
  );
}
