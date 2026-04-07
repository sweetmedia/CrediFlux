'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { authAPI } from '@/lib/api/auth';
import { TwoFactorSetupResponse } from '@/types';
import { Loader2, Shield, Copy, Check, AlertTriangle } from 'lucide-react';
import { BackupCodesDisplay } from './BackupCodesDisplay';

interface TwoFactorSetupProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type SetupStep = 'intro' | 'qrcode' | 'verify' | 'backup' | 'complete';

export function TwoFactorSetup({ isOpen, onClose, onSuccess }: TwoFactorSetupProps) {
  const [step, setStep] = useState<SetupStep>('intro');
  const [setupData, setSetupData] = useState<TwoFactorSetupResponse | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleStartSetup = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await authAPI.setup2FA();
      setSetupData(response);
      setStep('qrcode');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error al iniciar la configuracion de 2FA');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async () => {
    if (verificationCode.length !== 6) {
      setError('El codigo debe tener 6 digitos');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await authAPI.verify2FA(verificationCode);
      setBackupCodes(response.backup_codes);
      setStep('backup');
    } catch (err: any) {
      setError(err.response?.data?.code?.[0] || 'Codigo incorrecto. Por favor intenta de nuevo.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopySecret = () => {
    if (setupData?.secret) {
      navigator.clipboard.writeText(setupData.secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleComplete = () => {
    onSuccess();
    onClose();
    // Reset state
    setStep('intro');
    setSetupData(null);
    setVerificationCode('');
    setBackupCodes([]);
  };

  const handleClose = () => {
    if (step !== 'backup') {
      onClose();
      // Reset state
      setStep('intro');
      setSetupData(null);
      setVerificationCode('');
      setBackupCodes([]);
      setError(null);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            Configurar Autenticacion de Dos Factores
          </DialogTitle>
          <DialogDescription>
            {step === 'intro' && 'Protege tu cuenta con una capa adicional de seguridad'}
            {step === 'qrcode' && 'Escanea el codigo QR con tu aplicacion de autenticacion'}
            {step === 'verify' && 'Ingresa el codigo de verificacion'}
            {step === 'backup' && 'Guarda tus codigos de respaldo'}
            {step === 'complete' && 'Configuracion completada'}
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Step: Intro */}
        {step === 'intro' && (
          <div className="space-y-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Como funciona:</h4>
              <ol className="list-decimal list-inside text-sm text-blue-800 space-y-1">
                <li>Descarga una app de autenticacion (Google Authenticator, Authy, etc.)</li>
                <li>Escanea el codigo QR o ingresa la clave manualmente</li>
                <li>Ingresa el codigo de 6 digitos para verificar</li>
                <li>Guarda tus codigos de respaldo en un lugar seguro</li>
              </ol>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Cancelar
              </Button>
              <Button onClick={handleStartSetup} disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Comenzar
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Step: QR Code */}
        {step === 'qrcode' && setupData && (
          <div className="space-y-4">
            <div className="flex justify-center">
              <div className="bg-white p-2 rounded-lg border">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={setupData.qr_code}
                  alt="QR Code for 2FA"
                  className="w-48 h-48"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-sm text-slate-600">
                No puedes escanear? Ingresa esta clave manualmente:
              </Label>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-slate-100 px-3 py-2 rounded text-sm font-mono break-all">
                  {setupData.secret}
                </code>
                <Button variant="outline" size="sm" onClick={handleCopySecret}>
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Cancelar
              </Button>
              <Button onClick={() => setStep('verify')}>
                Siguiente
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Step: Verify */}
        {step === 'verify' && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="verification-code">
                Codigo de verificacion
              </Label>
              <Input
                id="verification-code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder="000000"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                className="text-center text-2xl tracking-widest font-mono"
                autoFocus
              />
              <p className="text-sm text-slate-500">
                Ingresa el codigo de 6 digitos de tu aplicacion de autenticacion
              </p>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setStep('qrcode')}>
                Atras
              </Button>
              <Button
                onClick={handleVerify}
                disabled={isLoading || verificationCode.length !== 6}
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Verificar
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Step: Backup Codes */}
        {step === 'backup' && (
          <div className="space-y-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Guarda estos codigos en un lugar seguro. Los necesitaras si pierdes acceso a tu dispositivo.
              </AlertDescription>
            </Alert>

            <BackupCodesDisplay codes={backupCodes} />

            <DialogFooter>
              <Button onClick={handleComplete}>
                Listo, he guardado mis codigos
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
