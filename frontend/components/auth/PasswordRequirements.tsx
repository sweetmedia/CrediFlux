/**
 * Requisitos de contraseña en vivo. Son las reglas de AUTH_PASSWORD_VALIDATORS
 * del backend (config/settings/base.py): largo mínimo 8, no sólo números y no
 * parecida al correo o al nombre. «No es común» sólo se puede comprobar en el
 * servidor: se muestra sin marca y su error llega al campo si la rechaza.
 */
import { Check, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';

export type PasswordCheckId = 'length' | 'not_numeric' | 'not_similar';

export interface PasswordCheck {
  id: PasswordCheckId;
  label: string;
  ok: boolean;
}

export interface PasswordContext {
  email?: string;
  names?: string[];
}

const plano = (s: string) =>
  s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

export function passwordChecks(password: string, ctx: PasswordContext): PasswordCheck[] {
  const pw = plano(password);
  const pistas = [ctx.email?.split('@')[0] ?? '', ...(ctx.names ?? [])]
    .map(plano)
    .filter((p) => p.length >= 3);
  return [
    { id: 'length', label: 'Al menos 8 caracteres', ok: password.length >= 8 },
    { id: 'not_numeric', label: 'No sólo números', ok: password.length > 0 && !/^\d+$/.test(password) },
    {
      id: 'not_similar',
      label: 'Que no se parezca a tu correo ni a tu nombre',
      ok: password.length > 0 && !pistas.some((p) => pw.includes(p)),
    },
  ];
}

export function PasswordRequirements({ password, ctx }: { password: string; ctx: PasswordContext }) {
  return (
    <ul aria-live="polite" className="mt-3 space-y-1.5 text-[12px]">
      {passwordChecks(password, ctx).map((c) => (
        <li key={c.id} data-ok={c.ok || undefined} className={cn('flex items-center gap-2', c.ok ? 'text-forest-700' : 'text-sage-600')}>
          {c.ok ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Circle className="h-3 w-3" aria-hidden="true" />}
          <span>{c.label}</span>
          <span className="sr-only">{c.ok ? '(cumplido)' : '(pendiente)'}</span>
        </li>
      ))}
      <li className="flex items-center gap-2 text-sage-600">
        <Circle className="h-3 w-3 opacity-40" aria-hidden="true" />
        <span>Que no sea una contraseña común</span>
      </li>
    </ul>
  );
}
