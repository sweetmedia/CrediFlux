'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Shield, KeyRound, AlertTriangle } from 'lucide-react';

interface TwoFactorVerifyProps {
  onVerify: (code: string, isBackupCode: boolean) => Promise<void>;
  onCancel: () => void;
  isLoading: boolean;
  error: string | null;
}

export function TwoFactorVerify({ onVerify, onCancel, isLoading, error }: TwoFactorVerifyProps) {
  const [code, setCode] = useState('');
  const [useBackupCode, setUseBackupCode] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [useBackupCode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length < 6) return;
    await onVerify(code, useBackupCode);
  };

  const handleCodeChange = (value: string) => {
    // Allow alphanumeric for backup codes, only digits for TOTP
    if (useBackupCode) {
      setCode(value.toUpperCase().replace(/[^A-Z0-9]/g, ''));
    } else {
      setCode(value.replace(/\D/g, ''));
    }
  };

  const toggleMode = () => {
    setUseBackupCode(!useBackupCode);
    setCode('');
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
          <Shield className="h-6 w-6 text-blue-600" />
        </div>
        <h2 className="text-xl font-semibold text-slate-900">
          Verificacion de Dos Factores
        </h2>
        <p className="text-sm text-slate-600 mt-1">
          {useBackupCode
            ? 'Ingresa uno de tus codigos de respaldo'
            : 'Ingresa el codigo de tu aplicacion de autenticacion'}
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="2fa-code">
            {useBackupCode ? 'Codigo de respaldo' : 'Codigo de verificacion'}
          </Label>
          <Input
            ref={inputRef}
            id="2fa-code"
            type="text"
            inputMode={useBackupCode ? 'text' : 'numeric'}
            maxLength={useBackupCode ? 8 : 6}
            placeholder={useBackupCode ? 'XXXXXXXX' : '000000'}
            value={code}
            onChange={(e) => handleCodeChange(e.target.value)}
            className="text-center text-2xl tracking-widest font-mono"
            autoComplete="one-time-code"
            disabled={isLoading}
          />
        </div>

        <Button
          type="submit"
          className="w-full"
          disabled={isLoading || (useBackupCode ? code.length < 8 : code.length !== 6)}
        >
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Verificar
        </Button>

        <div className="flex items-center justify-between">
          <Button
            type="button"
            variant="link"
            onClick={toggleMode}
            className="text-sm px-0"
          >
            <KeyRound className="h-4 w-4 mr-1" />
            {useBackupCode ? 'Usar codigo de autenticacion' : 'Usar codigo de respaldo'}
          </Button>

          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            className="text-sm"
          >
            Cancelar
          </Button>
        </div>
      </form>
    </div>
  );
}
