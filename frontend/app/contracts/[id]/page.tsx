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
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Loader2,
  ArrowLeft,
  PenTool,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Download,
  FileCheck,
  FileClock,
  FileEdit,
  FileX,
  User,
  UserCheck,
  Calendar,
  Eye,
  FileDown,
  Mail,
  Send,
  Archive,
} from 'lucide-react';

const STATUS_LABELS: Record<string, string> = {
  draft: 'Borrador',
  pending_signature: 'Pendiente Firma',
  signed: 'Firmado',
  active: 'Activo',
  completed: 'Completado',
  cancelled: 'Cancelado',
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-800',
  pending_signature: 'bg-yellow-100 text-yellow-800',
  signed: 'bg-blue-100 text-blue-800',
  active: 'bg-green-100 text-green-800',
  completed: 'bg-purple-100 text-purple-800',
  cancelled: 'bg-red-100 text-red-800',
};

export default function ViewContractPage() {
  const router = useRouter();
  const params = useParams();
  const contractId = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [contract, setContract] = useState<Contract | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [sendDialogOpen, setSendDialogOpen] = useState(false);
  const [sendEmail, setSendEmail] = useState('');
  const [sendDaysValid, setSendDaysValid] = useState(7);
  const [sendSuccess, setSendSuccess] = useState(false);
  const [sendError, setSendError] = useState('');

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

  const handleRegenerate = async () => {
    if (!contract) return;
    try {
      setIsActionLoading(true);
      setError('');
      await contractsAPI.regenerate(contract.id);
      loadContract();
    } catch (err: any) {
      console.error('Error regenerating contract:', err);
      setError('Error al regenerar el contrato');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!contract) return;
    try {
      setIsActionLoading(true);
      setError('');
      await contractsAPI.activate(contract.id);
      loadContract();
    } catch (err: any) {
      console.error('Error activating contract:', err);
      setError('Error al activar el contrato');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!contract) return;
    try {
      setIsActionLoading(true);
      setError('');
      await contractsAPI.cancel(contract.id);
      setCancelDialogOpen(false);
      loadContract();
    } catch (err: any) {
      console.error('Error cancelling contract:', err);
      setError('Error al cancelar el contrato');
      setCancelDialogOpen(false);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleArchive = async () => {
    if (!contract) return;
    try {
      setIsActionLoading(true);
      setError('');
      await contractsAPI.archive(contract.id);
      setArchiveDialogOpen(false);
      loadContract();
    } catch (err: any) {
      console.error('Error archiving contract:', err);
      setError('Error al archivar el contrato');
      setArchiveDialogOpen(false);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleSendForSignature = async () => {
    if (!contract) return;
    if (!sendEmail || !sendEmail.includes('@')) {
      setSendError('Por favor ingrese un email válido');
      return;
    }

    try {
      setIsActionLoading(true);
      setSendError('');
      setSendSuccess(false);

      const result = await contractsAPI.sendForSignature(
        contract.id,
        sendEmail,
        sendDaysValid
      );

      setSendSuccess(true);
      setSendError('');

      // Reset form and close after 2 seconds
      setTimeout(() => {
        setSendDialogOpen(false);
        setSendEmail('');
        setSendDaysValid(7);
        setSendSuccess(false);
      }, 2000);
    } catch (err: any) {
      console.error('Error sending for signature:', err);
      setSendError(err.message || 'Error al enviar el contrato');
      setSendSuccess(false);
    } finally {
      setIsActionLoading(false);
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
        <div className="container mx-auto max-w-7xl">
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

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Link href="/contracts">
              <Button variant="outline" size="sm" className="border-slate-200">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Volver
              </Button>
            </Link>
          </div>

          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <h1 className="text-2xl font-bold text-slate-900">
                  {contract.contract_number}
                </h1>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                    STATUS_COLORS[contract.status]
                  }`}
                >
                  {STATUS_LABELS[contract.status]}
                </span>
                {contract.is_fully_signed && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <CheckCircle2 className="h-3 w-3" />
                    Firmado Completamente
                  </span>
                )}
              </div>
              <div className="flex items-center gap-4 text-sm text-slate-600">
                <span>Préstamo: {contract.loan_number}</span>
                <span>Cliente: {contract.customer_name}</span>
              </div>
            </div>

            <div className="flex items-center gap-2 ml-4">
              {(contract.status === 'draft' ||
                contract.status === 'pending_signature' ||
                contract.status === 'signed') && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSendDialogOpen(true)}
                    className="border-purple-200 text-purple-600 hover:bg-purple-50"
                  >
                    <Mail className="h-4 w-4 mr-1" />
                    Enviar para Firma
                  </Button>
                  <Link href={`/contracts/${contract.id}/sign`}>
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-blue-200 text-blue-600 hover:bg-blue-50"
                    >
                      <PenTool className="h-4 w-4 mr-1" />
                      Firmar
                    </Button>
                  </Link>
                  {contract.status === 'draft' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleRegenerate}
                      disabled={isActionLoading}
                      className="border-slate-200"
                    >
                      <RefreshCw className="h-4 w-4 mr-1" />
                      Regenerar
                    </Button>
                  )}
                </>
              )}
              {contract.status === 'signed' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleActivate}
                  disabled={isActionLoading}
                  className="border-green-200 text-green-600 hover:bg-green-50"
                >
                  <CheckCircle2 className="h-4 w-4 mr-1" />
                  Activar
                </Button>
              )}
              {(contract.status === 'draft' ||
                contract.status === 'pending_signature') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCancelDialogOpen(true)}
                  disabled={isActionLoading}
                  className="border-red-200 text-red-600 hover:bg-red-50"
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  Cancelar
                </Button>
              )}
              {contract.status === 'cancelled' && !contract.is_archived && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setArchiveDialogOpen(true)}
                  disabled={isActionLoading}
                  className="border-slate-400 text-slate-700 hover:bg-slate-100"
                >
                  <Archive className="h-4 w-4 mr-1" />
                  Archivar
                </Button>
              )}

              {/* PDF Actions */}
              {contract.content && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      try {
                        const baseUrl = typeof window !== 'undefined'
                          ? (window.location.hostname.includes('.localhost')
                              ? `http://${window.location.hostname}:8000`
                              : 'http://localhost:8000')
                          : 'http://localhost:8000';

                        const url = baseUrl + contractsAPI.getPdfViewUrl(contract.id);
                        const token = localStorage.getItem('access_token');

                        const response = await fetch(url, {
                          headers: {
                            'Authorization': `Bearer ${token}`,
                          },
                        });

                        if (!response.ok) {
                          const errorText = await response.text();
                          console.error('Error response:', errorText);
                          throw new Error(`Error ${response.status}: No se pudo obtener el PDF`);
                        }

                        const blob = await response.blob();
                        const blobUrl = window.URL.createObjectURL(blob);
                        window.open(blobUrl, '_blank');
                        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 100);
                      } catch (err) {
                        console.error('Error viewing PDF:', err);
                        alert('Error al ver el PDF: ' + (err instanceof Error ? err.message : 'Error desconocido'));
                      }
                    }}
                    className="border-slate-200"
                  >
                    <Eye className="h-4 w-4 mr-1" />
                    Ver PDF
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      try {
                        const baseUrl = typeof window !== 'undefined'
                          ? (window.location.hostname.includes('.localhost')
                              ? `http://${window.location.hostname}:8000`
                              : 'http://localhost:8000')
                          : 'http://localhost:8000';

                        const url = baseUrl + contractsAPI.getPdfDownloadUrl(contract.id);
                        const token = localStorage.getItem('access_token');

                        const response = await fetch(url, {
                          headers: {
                            'Authorization': `Bearer ${token}`,
                          },
                        });

                        if (!response.ok) {
                          const errorText = await response.text();
                          console.error('Download error response:', errorText);
                          throw new Error(`Error ${response.status}: No se pudo descargar el PDF`);
                        }

                        const blob = await response.blob();
                        const blobUrl = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = blobUrl;
                        a.download = `${contract.contract_number}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(blobUrl);
                      } catch (err) {
                        console.error('Error downloading PDF:', err);
                        alert('Error al descargar el PDF: ' + (err instanceof Error ? err.message : 'Error desconocido'));
                      }
                    }}
                    className="border-slate-200"
                  >
                    <FileDown className="h-4 w-4 mr-1" />
                    Descargar PDF
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Contract Content */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Contenido del Contrato
                </CardTitle>
                <CardDescription className="text-sm text-slate-600">
                  Documento generado desde plantilla
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <div className="bg-white border border-slate-200 rounded-lg p-8">
                  <div
                    className="prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{
                      __html: contract.content.replace(/\n/g, '<br />'),
                    }}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Special Terms */}
            {contract.special_terms && (
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="border-b border-slate-200 bg-white">
                  <CardTitle className="text-lg font-semibold text-slate-900">
                    Términos Especiales
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">
                    {contract.special_terms}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Notes */}
            {contract.notes && (
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="border-b border-slate-200 bg-white">
                  <CardTitle className="text-lg font-semibold text-slate-900">
                    Notas Internas
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">
                    {contract.notes}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Status & Info */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Información
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                    Estado
                  </p>
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                      STATUS_COLORS[contract.status]
                    }`}
                  >
                    {STATUS_LABELS[contract.status]}
                  </span>
                </div>

                {contract.template_name && (
                  <div className="pt-4 border-t border-slate-200">
                    <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                      Plantilla
                    </p>
                    <p className="text-sm text-slate-700">
                      {contract.template_name}
                    </p>
                  </div>
                )}

                <div className="pt-4 border-t border-slate-200">
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                    Generado
                  </p>
                  <p className="text-sm text-slate-700">
                    {new Date(contract.generated_at).toLocaleDateString('es-ES', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </p>
                  {contract.generated_by_name && (
                    <p className="text-xs text-slate-600 mt-1">
                      Por: {contract.generated_by_name}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Signatures */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Firmas
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                {/* Customer Signature */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <User className="h-4 w-4 text-slate-600" />
                    <p className="text-sm font-semibold text-slate-700">Cliente</p>
                  </div>
                  {contract.customer_signed_at ? (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                        <p className="text-xs font-medium text-green-800">
                          Firmado
                        </p>
                      </div>
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
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                      <div className="flex items-center gap-2">
                        <XCircle className="h-4 w-4 text-slate-400" />
                        <p className="text-xs text-slate-600">Pendiente</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Officer Signature */}
                <div className="pt-4 border-t border-slate-200">
                  <div className="flex items-center gap-2 mb-2">
                    <UserCheck className="h-4 w-4 text-slate-600" />
                    <p className="text-sm font-semibold text-slate-700">
                      Oficial de Crédito
                    </p>
                  </div>
                  {contract.officer_signed_at ? (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <CheckCircle2 className="h-4 w-4 text-blue-600" />
                        <p className="text-xs font-medium text-blue-800">
                          Firmado
                        </p>
                      </div>
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
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                      <div className="flex items-center gap-2">
                        <XCircle className="h-4 w-4 text-slate-400" />
                        <p className="text-xs text-slate-600">Pendiente</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Witness */}
                {contract.witness_name && (
                  <div className="pt-4 border-t border-slate-200">
                    <div className="flex items-center gap-2 mb-2">
                      <User className="h-4 w-4 text-slate-600" />
                      <p className="text-sm font-semibold text-slate-700">
                        Testigo
                      </p>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                      <p className="text-xs font-medium text-slate-700">
                        {contract.witness_name}
                      </p>
                      {contract.witness_id && (
                        <p className="text-xs text-slate-600 mt-1">
                          ID: {contract.witness_id}
                        </p>
                      )}
                      {contract.witness_signed_at && (
                        <p className="text-xs text-slate-600 mt-1">
                          Firmó:{' '}
                          {new Date(
                            contract.witness_signed_at
                          ).toLocaleDateString('es-ES')}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Cancel Confirmation Dialog */}
        <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirmar Cancelación</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas cancelar el contrato "
                {contract.contract_number}"? Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <div className="flex justify-end gap-3 mt-4">
              <Button
                variant="outline"
                onClick={() => setCancelDialogOpen(false)}
                disabled={isActionLoading}
              >
                No, Mantener
              </Button>
              <Button
                variant="destructive"
                onClick={handleCancel}
                disabled={isActionLoading}
              >
                {isActionLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Cancelando...
                  </>
                ) : (
                  'Sí, Cancelar'
                )}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Archive Confirmation Dialog */}
        <Dialog open={archiveDialogOpen} onOpenChange={setArchiveDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirmar Archivo</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas archivar el contrato "
                {contract.contract_number}"? El contrato archivado se ocultará de la
                lista principal, pero podrás restaurarlo en cualquier momento.
              </DialogDescription>
            </DialogHeader>
            <div className="flex justify-end gap-3 mt-4">
              <Button
                variant="outline"
                onClick={() => setArchiveDialogOpen(false)}
                disabled={isActionLoading}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleArchive}
                disabled={isActionLoading}
                className="bg-slate-600 hover:bg-slate-700"
              >
                {isActionLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Archivando...
                  </>
                ) : (
                  <>
                    <Archive className="mr-2 h-4 w-4" />
                    Sí, Archivar
                  </>
                )}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Send for Signature Dialog */}
        <Dialog open={sendDialogOpen} onOpenChange={setSendDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Enviar Contrato para Firma</DialogTitle>
              <DialogDescription>
                Envía un enlace seguro por email para que el destinatario pueda firmar
                el contrato digitalmente.
              </DialogDescription>
            </DialogHeader>

            {sendSuccess ? (
              <div className="py-6">
                <div className="flex flex-col items-center justify-center gap-3">
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <CheckCircle2 className="h-6 w-6 text-green-600" />
                  </div>
                  <p className="text-sm font-medium text-green-800">
                    ¡Contrato enviado exitosamente!
                  </p>
                  <p className="text-xs text-slate-600 text-center">
                    Se ha enviado un correo a {sendEmail} con el enlace de firma.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <label htmlFor="email" className="text-sm font-medium text-slate-700">
                    Email del Destinatario
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={sendEmail}
                    onChange={(e) => setSendEmail(e.target.value)}
                    placeholder="cliente@ejemplo.com"
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={isActionLoading}
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="days" className="text-sm font-medium text-slate-700">
                    Días de Validez
                  </label>
                  <input
                    id="days"
                    type="number"
                    min="1"
                    max="30"
                    value={sendDaysValid}
                    onChange={(e) => setSendDaysValid(parseInt(e.target.value) || 7)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={isActionLoading}
                  />
                  <p className="text-xs text-slate-500">
                    El enlace expirará después de {sendDaysValid} día(s).
                  </p>
                </div>

                {sendError && (
                  <Alert variant="destructive">
                    <AlertDescription>{sendError}</AlertDescription>
                  </Alert>
                )}

                <div className="flex justify-end gap-3 pt-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setSendDialogOpen(false);
                      setSendEmail('');
                      setSendDaysValid(7);
                      setSendError('');
                    }}
                    disabled={isActionLoading}
                  >
                    Cancelar
                  </Button>
                  <Button
                    onClick={handleSendForSignature}
                    disabled={isActionLoading || !sendEmail}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {isActionLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Enviando...
                      </>
                    ) : (
                      <>
                        <Send className="mr-2 h-4 w-4" />
                        Enviar
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
