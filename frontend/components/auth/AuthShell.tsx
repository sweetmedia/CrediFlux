/**
 * AuthShell — marco de las pantallas de acceso (login.html del canvas F3):
 * masthead con la financiera a la que se entra y panel de papel con el
 * formulario. Sin switch de tema: estas pantallas siguen el del equipo (D3).
 */
import type { ReactNode } from 'react';
import { Lock } from 'lucide-react';
import Image from '@/components/ui/image';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { esHostGeneral } from '@/lib/hosts';
import './auth.css';

export interface AuthShellProps {
  /** Sin título cuando el contenido trae el suyo (paso 2 del login). */
  title?: string;
  eyebrow?: string;
  /** Línea bajo el título. */
  description?: ReactNode;
  /** Arriba a la derecha del panel (p. ej. «Crear cuenta»). */
  topRight?: ReactNode;
  children: ReactNode;
}

export function AuthShell({ title, eyebrow, description, topRight, children }: AuthShellProps) {
  const { config } = useConfig();
  const general = esHostGeneral();
  const host = window.location.host;

  return (
    <div className="cf-root grid min-h-[100dvh] lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <aside className="cf-auth-masthead masthead flex flex-col px-5 pb-7 pt-6 lg:px-12 lg:py-10">
        <Image src="/logo-white.svg" alt="CrediFlux" width={110} height={22} className="h-[20px] w-auto self-start lg:h-[22px]" priority />
        {general ? (
          <div className="mt-8 lg:mt-auto">
            <div className="font-display text-[26px] font-medium leading-[1.08] tracking-tight lg:text-[34px]">
              Préstamos para financieras
            </div>
            <p className="mt-2 max-w-[34ch] text-[13px] text-white/60">
              Cartera, cobros, caja y facturación electrónica en un solo lugar.
            </p>
          </div>
        ) : (
          <div className="mt-8 lg:mt-auto">
            <div className="mb-3 font-mono text-[10px] uppercase tracking-widest text-white/45">Estás entrando a</div>
            <div className="font-display text-[26px] font-medium leading-[1.08] tracking-tight lg:text-[34px]">
              {config.company_name}
            </div>
            <div className="mt-2 flex items-center gap-2 font-mono text-[11px] tracking-wide text-white/50">
              <Lock className="h-3 w-3" aria-hidden="true" />
              <span>{host}</span>
            </div>
          </div>
        )}
        <div className="mt-10 hidden items-center justify-between font-mono text-[10px] uppercase tracking-widest text-white/30 lg:flex">
          <span>CrediFlux · Santiago, RD</span>
          <span>Conexión cifrada</span>
        </div>
      </aside>

      <main className="cf-paper-bg flex flex-col px-4 py-10 sm:px-8 lg:px-16">
        {topRight && <div className="flex items-center justify-end gap-3 text-[13px] text-sage-600">{topRight}</div>}
        <div className="flex flex-1 items-center">
          <div className="mx-auto w-full max-w-[400px] py-10">
            {eyebrow && <div className="mb-3 font-mono text-[10px] uppercase tracking-widest text-sage-600">{eyebrow}</div>}
            {title && <h1 className="font-display text-[38px] font-black leading-none tracking-tight text-forest-900">{title}</h1>}
            {description && <div className="mt-3 text-[14px] text-sage-600">{description}</div>}
            <div className={title ? 'mt-8' : undefined}>{children}</div>
          </div>
        </div>
      </main>
    </div>
  );
}
