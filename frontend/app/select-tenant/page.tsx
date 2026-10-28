import { useState } from 'react';
import { ArrowRight, Building2 } from 'lucide-react';
import { AuthShell } from '@/components/auth/AuthShell';
import { recentTenants } from '@/lib/recent-tenants';
import { esSubdominioValido, tenantUrl } from '@/lib/tenant-url';

/**
 * Host general: se escribe la dirección de la financiera (sin lista, por
 * privacidad) y se va a su login. Recuerda las usadas en este equipo.
 */
export default function SelectTenantPage() {
  const [sub, setSub] = useState('');
  const [error, setError] = useState('');
  const [recientes] = useState(recentTenants.read);
  const sufijo = import.meta.env.VITE_TENANT_BASE_DOMAIN || window.location.host;

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const s = sub.trim().toLowerCase();
    if (!esSubdominioValido(s)) {
      setError('Escribe sólo la primera parte de la dirección: sólo letras, números y guiones.');
      return;
    }
    recentTenants.add(s);
    window.location.assign(tenantUrl(s));
  };

  return (
    <AuthShell
      eyebrow="Acceso"
      title="¿A qué financiera entras?"
      description="Cada financiera tiene su propia dirección. Escríbela y te llevamos a su pantalla de acceso."
    >
      <form onSubmit={onSubmit} noValidate className="space-y-7">
        <div className="cf-field">
          <label className="cf-label" htmlFor="tenant">Dirección de tu financiera</label>
          <div className="flex items-center gap-2">
            <input
              id="tenant"
              className="cf-input cf-input--mono flex-1"
              placeholder="mi-financiera"
              autoComplete="off"
              autoCapitalize="none"
              spellCheck={false}
              value={sub}
              onChange={(e) => {
                setSub(e.target.value);
                setError('');
              }}
              aria-invalid={!!error}
              aria-describedby={error ? 'tenant-error' : undefined}
            />
            <span className="font-mono text-[12px] text-sage-500">.{sufijo}</span>
          </div>
          {error && <p id="tenant-error" className="mt-1.5 text-[12px] text-flame-700">{error}</p>}
        </div>
        <button type="submit" className="cf-btn cf-btn--primary h-11 w-full">
          Continuar
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </button>
      </form>

      {recientes.length > 0 && (
        <section className="mt-10" aria-labelledby="recientes">
          <h2 id="recientes" className="mb-3 font-mono text-[10px] uppercase tracking-widest text-sage-600">
            Usadas en este equipo
          </h2>
          <ul className="border-t border-forest-900/10">
            {recientes.map((r) => (
              <li key={r}>
                <a href={tenantUrl(r)} className="flex items-center gap-3 border-b border-forest-900/10 py-3 text-[14px] text-forest-900 hover:bg-forest-900/[0.03]">
                  <Building2 className="h-4 w-4 text-sage-500" aria-hidden="true" />
                  <span className="font-mono text-[13px]">{r}</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="mt-8 border-t border-forest-900/10 pt-6 text-[12px] leading-relaxed text-sage-600">
        ¿No sabes la dirección? Te la da el administrador de tu financiera. No mostramos la lista de financieras por
        privacidad.
      </p>
    </AuthShell>
  );
}
