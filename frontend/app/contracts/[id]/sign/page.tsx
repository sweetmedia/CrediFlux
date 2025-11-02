'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { contractsAPI, Contract } from '@/lib/api/contracts';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  ArrowLeft,
  Upload,
  CheckCircle2,
  XCircle,
  User,
  UserCheck,
  Info,
} from 'lucide-react';

export default function SignContractPage() {
  const router = useRouter();
  const params = useParams();
  const contractId = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [contract, setContract] = useState<Contract | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  const [customerSignature, setCustomerSignature] = useState<File | null>(null);
  const [officerSignature, setOfficerSignature] = useState<File | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load contract
  useEffect(() => {
    if (isAuthenticated && contractId) {
      loadContract();
    }
  }, [isAuthenticated, contractId]);

  const loadContract = async () => {
    try {
      setIsLoading(true);
      setError('');
      const data = await contractsAPI.getContract(contractId);
      setContract(data);
    } catch (err: any) {
      console.error('Error loading contract:', err);
      setError('Error al cargar el contrato');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomerSignature = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setCustomerSignature(file);
    }
  };

  const handleOfficerSignature = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setOfficerSignature(file);
    }
  };

  const handleCustomerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!contract) return;

    try {
      setIsSubmitting(true);
      await contractsAPI.signCustomer(contract.id, customerSignature || undefined);
      setSuccess('Firma del cliente registrada exitosamente');

      // Reload contract data
      setTimeout(() => {
        loadContract();
        setCustomerSignature(null);
        setSuccess('');
      }, 2000);
    } catch (err: any) {
      console.error('Error signing as customer:', err);
      setError(
        err.response?.data?.message ||
          err.message ||
          'Error al firmar como cliente'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOfficerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!contract) return;

    try {
      setIsSubmitting(true);
      await contractsAPI.signOfficer(contract.id, officerSignature || undefined);
      setSuccess('Firma del oficial registrada exitosamente');

      // Reload contract data
      setTimeout(() => {
        loadContract();
        setOfficerSignature(null);
        setSuccess('');
      }, 2000);
    } catch (err: any) {
      console.error('Error signing as officer:', err);
      setError(
        err.response?.data?.message ||
          err.message ||
          'Error al firmar como oficial'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error && !contract) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="container mx-auto max-w-6xl">
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <div className="mt-4">
            <Link href="/contracts">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver a Contratos
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!contract) return null;

  // Check if contract can be signed
  const canSign =
    contract.status === 'pending_signature' || contract.status === 'signed';

  if (!canSign) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="container mx-auto max-w-6xl">
          <Alert className="border-yellow-200 bg-yellow-50">
            <Info className="h-4 w-4 text-yellow-600" />
            <AlertDescription className="text-yellow-800">
              Este contrato no está disponible para firmar. Estado actual:{' '}
              {contract.status}
            </AlertDescription>
          </Alert>
          <div className="mt-4 flex gap-3">
            <Link href={`/contracts/${contract.id}`}>
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Ver Contrato
              </Button>
            </Link>
            <Link href="/contracts">
              <Button variant="outline">Volver a Contratos</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Link href={`/contracts/${contract.id}`}>
              <Button variant="outline" size="sm" className="border-slate-200">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Volver
              </Button>
            </Link>
          </div>

          <div>
            <h1 className="text-2xl font-bold text-slate-900 mb-2">
              Firmar Contrato
            </h1>
            <div className="flex items-center gap-4 text-sm text-slate-600">
              <span>Contrato: {contract.contract_number}</span>
              <span>Préstamo: {contract.loan_number}</span>
              <span>Cliente: {contract.customer_name}</span>
            </div>
          </div>
        </div>

        {/* Success */}
        {success && (
          <Alert className="mb-6 border-green-200 bg-green-50">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              {success}
            </AlertDescription>
          </Alert>
        )}

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Info Alert */}
        <Alert className="mb-6 border-blue-200 bg-blue-50">
          <Info className="h-4 w-4 text-blue-600" />
          <AlertDescription className="text-blue-800 text-sm">
            Para completar el proceso de firma, ambas partes (cliente y oficial de
            crédito) deben firmar el contrato. Las firmas pueden ser registradas
            con o sin imagen.
          </AlertDescription>
        </Alert>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Customer Signature */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="border-b border-slate-200 bg-white">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-green-100 p-2">
                  <User className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <CardTitle className="text-lg font-semibold text-slate-900">
                    Firma del Cliente
                  </CardTitle>
                  <CardDescription className="text-sm text-slate-600">
                    {contract.customer_name}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {contract.customer_signed_at ? (
                <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
                  <CheckCircle2 className="h-12 w-12 text-green-600 mx-auto mb-3" />
                  <p className="text-sm font-semibold text-green-800 mb-1">
                    Cliente ya ha firmado
                  </p>
                  <p className="text-xs text-green-700">
                    {new Date(contract.customer_signed_at).toLocaleDateString(
                      'es-ES',
                      {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      }
                    )}
                  </p>
                </div>
              ) : (
                <form onSubmit={handleCustomerSubmit}>
                  <div className="space-y-4">
                    <div>
                      <Label
                        htmlFor="customer-signature"
                        className="text-sm font-medium text-slate-700"
                      >
                        Imagen de Firma (Opcional)
                      </Label>
                      <div className="mt-1.5">
                        <label
                          htmlFor="customer-signature"
                          className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-300 rounded-lg cursor-pointer bg-slate-50 hover:bg-slate-100 transition-colors"
                        >
                          <div className="flex flex-col items-center justify-center pt-5 pb-6">
                            <Upload className="w-8 h-8 mb-2 text-slate-500" />
                            <p className="mb-1 text-sm text-slate-600">
                              <span className="font-semibold">Click para subir</span>{' '}
                              o arrastra y suelta
                            </p>
                            <p className="text-xs text-slate-500">
                              PNG, JPG (máx. 5MB)
                            </p>
                          </div>
                          <input
                            id="customer-signature"
                            type="file"
                            className="hidden"
                            accept="image/*"
                            onChange={handleCustomerSignature}
                          />
                        </label>
                      </div>
                      {customerSignature && (
                        <p className="text-xs text-green-600 mt-2">
                          Archivo seleccionado: {customerSignature.name}
                        </p>
                      )}
                    </div>

                    <div className="pt-4">
                      <Button
                        type="submit"
                        className="w-full bg-green-600 hover:bg-green-700"
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Registrando Firma...
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="mr-2 h-4 w-4" />
                            Firmar como Cliente
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>

          {/* Officer Signature */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="border-b border-slate-200 bg-white">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-blue-100 p-2">
                  <UserCheck className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <CardTitle className="text-lg font-semibold text-slate-900">
                    Firma del Oficial
                  </CardTitle>
                  <CardDescription className="text-sm text-slate-600">
                    Oficial de Crédito
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {contract.officer_signed_at ? (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
                  <CheckCircle2 className="h-12 w-12 text-blue-600 mx-auto mb-3" />
                  <p className="text-sm font-semibold text-blue-800 mb-1">
                    Oficial ya ha firmado
                  </p>
                  <p className="text-xs text-blue-700">
                    {new Date(contract.officer_signed_at).toLocaleDateString(
                      'es-ES',
                      {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      }
                    )}
                  </p>
                </div>
              ) : (
                <form onSubmit={handleOfficerSubmit}>
                  <div className="space-y-4">
                    <div>
                      <Label
                        htmlFor="officer-signature"
                        className="text-sm font-medium text-slate-700"
                      >
                        Imagen de Firma (Opcional)
                      </Label>
                      <div className="mt-1.5">
                        <label
                          htmlFor="officer-signature"
                          className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-300 rounded-lg cursor-pointer bg-slate-50 hover:bg-slate-100 transition-colors"
                        >
                          <div className="flex flex-col items-center justify-center pt-5 pb-6">
                            <Upload className="w-8 h-8 mb-2 text-slate-500" />
                            <p className="mb-1 text-sm text-slate-600">
                              <span className="font-semibold">Click para subir</span>{' '}
                              o arrastra y suelta
                            </p>
                            <p className="text-xs text-slate-500">
                              PNG, JPG (máx. 5MB)
                            </p>
                          </div>
                          <input
                            id="officer-signature"
                            type="file"
                            className="hidden"
                            accept="image/*"
                            onChange={handleOfficerSignature}
                          />
                        </label>
                      </div>
                      {officerSignature && (
                        <p className="text-xs text-green-600 mt-2">
                          Archivo seleccionado: {officerSignature.name}
                        </p>
                      )}
                    </div>

                    <div className="pt-4">
                      <Button
                        type="submit"
                        className="w-full bg-blue-600 hover:bg-blue-700"
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Registrando Firma...
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="mr-2 h-4 w-4" />
                            Firmar como Oficial
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Status Card */}
        <Card className="border-slate-200 shadow-sm mt-6">
          <CardHeader className="border-b border-slate-200 bg-white">
            <CardTitle className="text-lg font-semibold text-slate-900">
              Estado del Proceso de Firma
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="flex items-center gap-3">
                {contract.customer_signed_at ? (
                  <CheckCircle2 className="h-6 w-6 text-green-600" />
                ) : (
                  <XCircle className="h-6 w-6 text-slate-400" />
                )}
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    Cliente
                  </p>
                  <p className="text-xs text-slate-600">
                    {contract.customer_signed_at ? 'Firmado' : 'Pendiente'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {contract.officer_signed_at ? (
                  <CheckCircle2 className="h-6 w-6 text-blue-600" />
                ) : (
                  <XCircle className="h-6 w-6 text-slate-400" />
                )}
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    Oficial de Crédito
                  </p>
                  <p className="text-xs text-slate-600">
                    {contract.officer_signed_at ? 'Firmado' : 'Pendiente'}
                  </p>
                </div>
              </div>
            </div>

            {contract.is_fully_signed && (
              <div className="mt-6 pt-6 border-t border-slate-200">
                <Alert className="border-green-200 bg-green-50">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <AlertDescription className="text-green-800 text-sm">
                    El contrato ha sido firmado por ambas partes. Ahora puede ser
                    activado desde la página de visualización del contrato.
                  </AlertDescription>
                </Alert>
                <div className="mt-4">
                  <Link href={`/contracts/${contract.id}`}>
                    <Button className="w-full bg-green-600 hover:bg-green-700">
                      Ver Contrato Completo
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
