import { useState } from 'react';
import { AlertTriangle, ChevronLeft, Loader2 } from 'lucide-react';
import { OtpInput } from './OtpInput';

interface TwoFactorVerifyProps {
  onVerify: (code: string, isBackupCode: boolean) => Promise<void>;
  onCancel: () => void;
  isLoading: boolean;
  error: string | null;
}

/** Paso 2 del login (login.html, estado 2fa): seis dígitos o un código de respaldo de 8. */
export function TwoFactorVerify({ onVerify, onCancel, isLoading, error }: TwoFactorVerifyProps) {
  const [code, setCode] = useState('');
  const [useBackupCode, setUseBackupCode] = useState(false);

  const completo = useBackupCode ? code.length === 8 : code.length === 6;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!completo) return;
    await onVerify(code, useBackupCode);
  };

  const toggleMode = () => {
    setUseBackupCode(!useBackupCode);
    setCode('');
  };

  return (
    <div>
      <button type="button" onClick={onCancel} className="mb-6 inline-flex items-center gap-1.5 text-[13px] text-sage-600 hover:text-forest-900">
        <ChevronLeft className="h-3 w-3" aria-hidden="true" />
        Volver
      </button>
      <div className="mb-4 flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-sage-600">
        <span>Paso 2 de 2</span>
        <span className="h-px w-6 bg-forest-900/20" aria-hidden="true" />
        <span>Verificación</span>
      </div>
      <h1 className="font-display text-[38px] font-black leading-none tracking-tight text-forest-900">Código de acceso</h1>
      <p className="mt-3 text-[14px] leading-relaxed text-sage-600">
        {useBackupCode
          ? 'Escribe uno de tus códigos de respaldo de 8 caracteres.'
          : 'Abre tu app autenticadora y escribe el código de 6 dígitos.'}
      </p>

      {error && (
        <div role="alert" className="mt-7 flex gap-2.5 rounded border border-flame-500/30 bg-flame-100 p-3 text-[13px] text-forest-900">
          <AlertTriangle className="mt-0.5 h-[15px] w-[15px] shrink-0 text-flame-600" aria-hidden="true" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-9">
        {useBackupCode ? (
          <div className="cf-field">
            <label className="cf-label" htmlFor="2fa-backup">Código de respaldo</label>
            <input
              id="2fa-backup"
              type="text"
              className="cf-input cf-input--mono tracking-widest"
              placeholder="XXXXXXXX"
              autoComplete="one-time-code"
              autoFocus
              value={code}
              disabled={isLoading}
              onChange={(e) => setCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8))}
            />
          </div>
        ) : (
          <div>
            <div className="cf-label mb-2">Código</div>
            <OtpInput value={code} onChange={setCode} disabled={isLoading} autoFocus />
            <div className="mt-3 text-right font-mono text-[11px] tabular-nums text-sage-600">{code.length} / 6</div>
          </div>
        )}

        <button type="submit" className="cf-btn cf-btn--primary mt-7 h-11 w-full" disabled={isLoading || !completo}>
          {isLoading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          Verificar y entrar
        </button>
      </form>

      <div className="mt-8 border-t border-forest-900/10 pt-6 text-[12px] text-sage-600">
        {useBackupCode ? '¿Tienes tu app a mano? ' : '¿Perdiste el acceso a tu app? '}
        <button type="button" onClick={toggleMode} className="text-forest-900 underline decoration-forest-900/25 underline-offset-4">
          {useBackupCode ? 'Usar el código de la app' : 'Usar un código de respaldo'}
        </button>
      </div>
    </div>
  );
}
