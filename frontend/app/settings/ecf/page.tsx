'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { toast } from 'sonner';
import {
  ArrowLeft,
  CheckCircle2,
  KeyRound,
  Loader2,
  PlugZap,
  Save,
  Trash2,
  XCircle,
} from 'lucide-react';

import { useAuth } from '@/lib/contexts/AuthContext';
import { billingAPI } from '@/lib/api/billing';
import { getApiErrorMessage } from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { NativeSelect } from '@/components/ui/native-select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Field } from '@/components/ui/field';
import { ErrorState } from '@/components/ui/error-state';
import { useConfirm } from '@/components/ui/confirm-dialog';
import {
  DGIIEnvironment,
  ECFProviderConfig,
  ECFProviderConfigUpdate,
  ECFProviderKey,
  ECFProviderStatus,
} from '@/types/billing';

export default function ECFSettingsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [askConfirm, confirmDialog] = useConfirm();

  const [config, setConfig] = useState<ECFProviderConfig | null>(null);
  const [loadError, setLoadError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const [provider, setProvider] = useState<ECFProviderKey>('nexconnect');
  const [environment, setEnvironment] = useState<DGIIEnvironment>('testecf');
  const [apiKey, setApiKey] = useState('');
  const [apiKeyError, setApiKeyError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ECFProviderStatus | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) loadConfig();
  }, [isAuthenticated]);

  const applyConfig = (data: ECFProviderConfig) => {
    setConfig(data);
    setProvider(data.ecf_provider);
    setEnvironment(data.dgii_environment);
  };

  const loadConfig = async () => {
    try {
      setIsLoading(true);
      setLoadError('');
      applyConfig(await billingAPI.getProviderConfig());
    } catch (err) {
      setLoadError(getApiErrorMessage(err, 'No pudimos cargar la configuración de facturación electrónica'));
    } finally {
      setIsLoading(false);
    }
  };

  const isNexConnect = provider === 'nexconnect';
  const trimmedKey = apiKey.trim();
  const isDirty =
    !!config && (provider !== config.ecf_provider || environment !== config.dgii_environment || !!trimmedKey);

  const save = async (update: ECFProviderConfigUpdate, message: string) => {
    try {
      setSaving(true);
      setSaveError('');
      applyConfig(await billingAPI.updateProviderConfig(update));
      setApiKey('');
      setTestResult(null);
      toast.success(message);
    } catch (err) {
      setSaveError(getApiErrorMessage(err, 'No se pudo guardar la configuración'));
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setApiKeyError('');
    if (trimmedKey && !/^nxc_(test|live)_/.test(trimmedKey)) {
      setApiKeyError('La API key de NexConnect empieza por nxc_test_ o nxc_live_.');
      return;
    }

    const update: ECFProviderConfigUpdate = {};
    if (provider !== config.ecf_provider) update.ecf_provider = provider;
    if (environment !== config.dgii_environment) update.dgii_environment = environment;
    if (trimmedKey) update.api_key = trimmedKey;

    if (update.ecf_provider) {
      const label = config.ecf_provider_choices.find((c) => c.value === provider)?.label ?? provider;
      const confirmed = await askConfirm({
        title: '¿Cambiar el proveedor de facturación electrónica?',
        description: `Las facturas nuevas se emitirán con ${label}. Las que ya se emitieron siguen en el flujo con el que salieron.`,
        confirmLabel: 'Cambiar proveedor',
      });
      if (!confirmed) return;
    }
    await save(update, 'Configuración de facturación electrónica guardada');
  };

  const handleClearKey = async () => {
    const confirmed = await askConfirm({
      title: '¿Quitar la API key de NexConnect?',
      description: 'Sin key, CrediFlux no podrá emitir ni consultar e-CF en NexConnect hasta que guardes una nueva.',
      confirmLabel: 'Quitar API key',
      variant: 'destructive',
    });
    if (!confirmed) return;
    await save({ clear_api_key: true }, 'API key eliminada');
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      setTestResult(await billingAPI.testProviderConnection());
    } catch (err) {
      setTestResult({ status: 'error', error: getApiErrorMessage(err, 'No se pudo probar la conexión') });
    } finally {
      setTesting(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F8FAF7]">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAF7] p-6 lg:p-8">
      {confirmDialog}
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="space-y-4">
          <Link
            href="/settings"
            className="inline-flex items-center text-sm text-slate-600 transition hover:text-slate-900"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a Configuración
          </Link>
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Facturación electrónica (e-CF)</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Elige cómo se emiten tus comprobantes electrónicos ante la DGII.
            </p>
          </div>
        </div>

        {!config ? (
          <ErrorState variant="page" message={loadError} onRetry={loadConfig} />
        ) : (
          <>
            <form onSubmit={handleSave}>
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="border-b border-slate-200">
                  <CardTitle className="text-base font-semibold text-slate-900">Proveedor</CardTitle>
                  <CardDescription>
                    Con NexConnect no necesitas certificado ni secuencias propias: NexConnect asigna el e-NCF,
                    firma y envía a la DGII.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5 pt-5">
                  <Field label="Proveedor e-CF" required>
                    <NativeSelect
                      value={provider}
                      onChange={(e) => setProvider(e.target.value as ECFProviderKey)}
                    >
                      {config.ecf_provider_choices.map((choice) => (
                        <option key={choice.value} value={choice.value}>
                          {choice.label}
                        </option>
                      ))}
                    </NativeSelect>
                  </Field>

                  {provider === 'direct' && (
                    <Alert>
                      <AlertDescription className="text-sm">
                        Con DGII directo necesitas un certificado digital y secuencias e-NCF propias, en{' '}
                        <Link href="/billing" className="font-medium underline">Facturación</Link>.
                      </AlertDescription>
                    </Alert>
                  )}

                  {provider !== 'none' && (
                    <Field
                      label="Ambiente DGII"
                      required
                      hint={
                        environment === 'ecf' && config.is_test_key
                          ? 'La API key guardada es de pruebas: no puede emitir en Producción.'
                          : undefined
                      }
                    >
                      <NativeSelect
                        value={environment}
                        onChange={(e) => setEnvironment(e.target.value as DGIIEnvironment)}
                      >
                        {config.dgii_environment_choices.map((choice) => (
                          <option key={choice.value} value={choice.value}>
                            {choice.label}
                          </option>
                        ))}
                      </NativeSelect>
                    </Field>
                  )}

                  {isNexConnect && (
                    <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50/70 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                          <KeyRound className="h-4 w-4 text-slate-500" aria-hidden />
                          API key de NexConnect
                        </div>
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            config.has_api_key ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {config.has_api_key
                            ? config.is_test_key
                              ? 'Guardada · pruebas'
                              : 'Guardada'
                            : 'Sin configurar'}
                        </span>
                      </div>
                      <Field
                        label={config.has_api_key ? 'Reemplazar API key' : 'API key'}
                        error={apiKeyError}
                        hint="Por seguridad nunca se vuelve a mostrar. Se guarda cifrada; deja el campo vacío para conservar la actual."
                      >
                        <Input
                          type="password"
                          autoComplete="off"
                          spellCheck={false}
                          placeholder="nxc_test_… o nxc_live_…"
                          value={apiKey}
                          onChange={(e) => {
                            setApiKey(e.target.value);
                            setApiKeyError('');
                          }}
                          className="font-mono"
                        />
                      </Field>
                      {config.has_api_key && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:text-red-700"
                          onClick={handleClearKey}
                          disabled={saving}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Quitar API key
                        </Button>
                      )}
                      <p className="text-xs text-slate-500">
                        Notificaciones automáticas de estado (webhook):{' '}
                        {config.webhook_registered ? 'registradas' : 'sin registrar; los estados se consultan periódicamente'}.
                      </p>
                    </div>
                  )}

                  {saveError && <ErrorState message={saveError} />}

                  <div className="flex justify-end">
                    <Button type="submit" disabled={!isDirty || saving}>
                      {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                      Guardar
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </form>

            {config.ecf_provider !== 'none' && (
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="border-b border-slate-200">
                  <CardTitle className="text-base font-semibold text-slate-900">Probar conexión</CardTitle>
                  <CardDescription>Usa la configuración guardada.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 pt-5">
                  <div className="flex flex-wrap items-center gap-3">
                    <Button variant="outline" onClick={handleTest} disabled={testing || isDirty}>
                      {testing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlugZap className="mr-2 h-4 w-4" />}
                      Probar conexión
                    </Button>
                    {isDirty && <p className="text-xs text-slate-500">Guarda los cambios antes de probar.</p>}
                  </div>
                  {testResult && <ConnectionResult result={testResult} />}
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const ENVIRONMENT_LABELS: Record<string, string> = {
  testecf: 'Pre-Certificación',
  certecf: 'Certificación',
  ecf: 'Producción',
};

function ConnectionResult({ result }: { result: ECFProviderStatus }) {
  if (result.status === 'online') {
    return (
      <div role="status" className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3">
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-700" aria-hidden />
        <div className="text-sm text-green-900">
          <p className="font-medium">Conectado a {result.provider || 'el proveedor'}</p>
          <p className="mt-0.5 text-green-800">
            {[
              result.organization && `Emisor: ${result.organization}`,
              result.environment && `Ambiente: ${ENVIRONMENT_LABELS[result.environment] || result.environment}`,
              result.test_key && 'clave de pruebas',
            ]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
      </div>
    );
  }

  const message =
    result.status === 'not_configured'
      ? result.error || 'Falta configurar el proveedor.'
      : result.status === 'offline'
        ? 'No se pudo contactar al proveedor. Intenta de nuevo en unos minutos.'
        : result.http_code === 401 || result.http_code === 403
          ? 'El proveedor rechazó la API key. Revisa que sea correcta y esté activa.'
          : result.error || 'El proveedor respondió con un error.';

  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
      <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-700" aria-hidden />
      <div className="text-sm text-red-900">
        <p className="font-medium">
          {result.status === 'not_configured' ? 'Sin configurar' : 'Sin conexión'}
          {result.http_code ? ` (HTTP ${result.http_code})` : ''}
        </p>
        <p className="mt-0.5 text-red-800">{message}</p>
      </div>
    </div>
  );
}
