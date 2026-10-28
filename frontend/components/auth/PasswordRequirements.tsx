/**
 * Requisitos de contraseña en vivo. De las reglas de AUTH_PASSWORD_VALIDATORS
 * del backend (config/settings/base.py) sólo se marcan en vivo las que el
 * navegador comprueba igual que el servidor: largo mínimo 8 (en caracteres,
 * como Django) y no sólo números. «No es común» y «no se parece a tu correo ni
 * a tu nombre» se muestran sin marca: las decide el servidor y su error llega
 * al campo.
 */
import { Check, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';

export type PasswordCheckId = 'length' | 'not_numeric';

export interface PasswordCheck {
  id: PasswordCheckId;
  label: string;
  ok: boolean;
}

const SOLO_SERVIDOR = ['Que no sea una contraseña común', 'Que no se parezca a tu correo ni a tu nombre'];

export function passwordChecks(password: string): PasswordCheck[] {
  const largo = Array.from(password).length;
  return [
    { id: 'length', label: 'Al menos 8 caracteres', ok: largo >= 8 },
    { id: 'not_numeric', label: 'No sólo números', ok: largo > 0 && !/^\d+$/.test(password) },
  ];
}

export function PasswordRequirements({ password, id }: { password: string; id?: string }) {
  const checks = passwordChecks(password);
  const cumplidas = checks.filter((c) => c.ok).length;
  return (
    <div id={id}>
      <ul className="mt-3 space-y-1.5 text-[12px]">
        {checks.map((c) => (
          <li key={c.id} data-ok={c.ok || undefined} className={cn('flex items-center gap-2', c.ok ? 'text-forest-700' : 'text-sage-600')}>
            {c.ok ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Circle className="h-3 w-3" aria-hidden="true" />}
            <span>{c.label}</span>
            <span className="sr-only">{c.ok ? '(cumplido)' : '(pendiente)'}</span>
          </li>
        ))}
        {SOLO_SERVIDOR.map((label) => (
          <li key={label} className="flex items-center gap-2 text-sage-600">
            <Circle className="h-3 w-3 opacity-40" aria-hidden="true" />
            <span>{label}</span>
          </li>
        ))}
      </ul>
      <p className="sr-only" aria-live="polite">
        {password ? `${cumplidas} de ${checks.length} requisitos cumplidos` : ''}
      </p>
    </div>
  );
}
