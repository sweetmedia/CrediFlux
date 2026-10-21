'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { billingAPI } from '@/lib/api/billing';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  ArrowLeft,
  FileText,
  Send,
  CheckCircle,
  XCircle,
  Shield,
  RefreshCw,
  FileCode,
  Clock,
  Trash2,
  Copy,
  Download,
  AlertTriangle,
} from 'lucide-react';
import {
  Invoice,
  ECFSubmission,
  InvoiceStatus,
  INVOICE_STATUS_LABELS,
  INVOICE_STATUS_COLORS,
  ECF_TYPE_LABELS,
  ECFType,
  PAYMENT_METHOD_LABELS,
  PaymentMethod,
} from '@/types/billing';
import { useConfirm } from '@/components/ui/confirm-dialog';
import { ErrorState } from '@/components/ui/error-state';
import { getApiErrorMessage } from '@/lib/api/client';

// Pasos del flujo NexConnect: NexConnect firma y envía; el último paso es el veredicto de la DGII.
const NEXCONNECT_STEPS = ['Borrador', 'Firmado', 'Enviado'] as const;

const NEXCONNECT_STEP_INDEX: Partial<Record<InvoiceStatus, number>> = {
  draft: 0,
  generated: 0,
  signed: 1,
  submitted: 2,
};

const FINAL_STEP: Partial<Record<InvoiceStatus, { label: string; className: string }>> = {
  accepted: { label: 'Aceptado', className: 'bg-green-600 text-white' },
  conditionally_accepted: { label: 'Aceptado condicional', className: 'bg-orange-500 text-white' },
  rejected: { label: 'Rechazado', className: 'bg-red-600 text-white' },
  cancelled: { label: 'Anulado', className: 'bg-slate-500 text-white' },
};

// Estados que devuelve NexConnect (Invoice.dgii_status / ECFSubmission.response_status).
const NEXCONNECT_STATUS_LABELS: Record<string, string> = {
  signed: 'Firmado',
  submitted: 'Enviado a la DGII',
  delivered_to_receiver: 'Entregado al receptor',
  queued_offline: 'En cola (DGII sin conexión)',
  accepted: 'Aceptado',
  accepted_conditional: 'Aceptado condicional',
  rejected: 'Rechazado',
  cancelled: 'Anulado',
  error: 'Error',
};

const SUBMISSION_ACTION_LABELS: Record<string, string> = {
  submit: 'Emisión',
  query_status: 'Consulta de estado',
  webhook: 'Notificación de NexConnect',
};

const submissionStatusClass = (value: string) => {
  if (['aceptado', 'accepted'].includes(value)) return 'bg-green-100 text-green-700';
  if (['accepted_conditional'].includes(value)) return 'bg-orange-100 text-orange-700';
  if (['rechazado', 'rejected', 'error'].includes(value)) return 'bg-red-100 text-red-700';
  return 'bg-slate-100 text-slate-700';
};

/** Un 502 de emit/refresh-status significa que NexConnect no respondió, no que CrediFlux esté caído. */
const providerErrorMessage = (err: any, fallback: string) => {
  const body = err?.response?.data;
  if (err?.response?.status === 502 && typeof body?.error === 'string') {
    return `NexConnect no respondió: ${body.error}`;
  }
  return getApiErrorMessage(err, fallback);
};

export default function InvoiceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [askConfirm, confirmDialog] = useConfirm();
  const [submissions, setSubmissions] = useState<ECFSubmission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState('');
  const [success, setSuccess] = useState('');
  const [showXML, setShowXML] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && id) {
      loadInvoice();
    }
  }, [isAuthenticated, id]);

  const loadInvoice = async () => {
    try {
      setIsLoading(true);
      setError('');
      setLoadError('');
      const [inv, subs] = await Promise.all([
        billingAPI.getInvoice(id),
        billingAPI.getInvoiceSubmissions(id).catch(() => []),
      ]);
      setInvoice(inv);
      setSubmissions(subs);
    } catch (err: any) {
      setLoadError(getApiErrorMessage(err, 'Error al cargar la factura'));
    } finally {
      setIsLoading(false);
    }
  };

  const reloadSubmissions = async () => {
    setSubmissions(await billingAPI.getInvoiceSubmissions(id).catch(() => submissions));
  };

  const handleEmit = async () => {
    if (!invoice) return;
    const confirmed = await askConfirm({
      title: '¿Emitir este e-CF vía NexConnect?',
      description:
        'NexConnect asigna el e-NCF, firma y envía a la DGII. Una vez emitida, la factura ya no se puede editar ni eliminar; para anularla hará falta una nota de crédito.',
      customer: invoice.comprador_razon_social || null,
      amount: invoice.total,
      confirmLabel: 'Emitir e-CF',
    });
    if (!confirmed) return;
    try {
      setActionLoading('emit');
      setError('');
      setSuccess('');
      const result = await billingAPI.emitInvoice(id);
      setInvoice(result.invoice);
      setSuccess(`e-CF emitido: ${result.ncf}. NexConnect lo está enviando a la DGII.`);
    } catch (err: any) {
      setError(providerErrorMessage(err, 'Error al emitir el e-CF'));
    } finally {
      await reloadSubmissions();
      setActionLoading(null);
    }
  };

  const handleRefreshStatus = async () => {
    try {
      setActionLoading('refresh');
      setError('');
      setSuccess('');
      const result = await billingAPI.refreshInvoiceStatus(id);
      setInvoice(result.invoice);
      const label = NEXCONNECT_STATUS_LABELS[result.status] || result.status;
      setSuccess(result.is_final ? `Estado final: ${label}` : `Estado actual: ${label}. La DGII aún no responde.`);
    } catch (err: any) {
      setError(providerErrorMessage(err, 'Error al consultar el estado'));
    } finally {
      await reloadSubmissions();
      setActionLoading(null);
    }
  };

  const handleGenerateECF = async () => {
    try {
      setActionLoading('generate');
      setError('');
      setSuccess('');
      const updated = await billingAPI.generateECF(id);
      setInvoice(updated);
      setSuccess('✅ XML generado exitosamente. e-NCF asignado: ' + updated.encf_number);
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Error al generar el e-CF'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleSignECF = async () => {
    try {
      setActionLoading('sign');
      setError('');
      setSuccess('');
      const updated = await billingAPI.signECF(id);
      setInvoice(updated);
      setSuccess('✅ e-CF firmado digitalmente');
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Error al firmar el e-CF'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleSubmitDGII = async () => {
    try {
      setActionLoading('submit');
      setError('');
      setSuccess('');
      const result = await billingAPI.submitToDGII(id);
      setInvoice(result.invoice);
      setSuccess(`✅ Enviado a DGII. TrackId: ${result.trackid}`);
      await reloadSubmissions();
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Error al enviar a DGII'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleCheckStatus = async () => {
    try {
      setActionLoading('check');
      setError('');
      setSuccess('');
      const result = await billingAPI.checkDGIIStatus(id);
      setInvoice(result.invoice);
      setSuccess(`Estado DGII: ${result.dgii_status}`);
      await reloadSubmissions();
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Error al consultar DGII'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async () => {
    if (!(await askConfirm({
      title: '¿Eliminar esta factura?',
      description: `${invoice?.encf_number || 'La factura borrador'} se eliminará. Esta acción no se puede deshacer.`,
      amount: invoice?.total,
      confirmLabel: 'Eliminar factura',
      variant: 'destructive',
    }))) return;
    try {
      await billingAPI.deleteInvoice(id);
      router.push('/billing');
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Error al eliminar la factura'));
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copiado al portapapeles');
    setTimeout(() => setSuccess(''), 2000);
  };

  const formatCurrency = (amount: number) => {
    return `RD$${Number(amount).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadge = (status: InvoiceStatus) => {
    const colors = INVOICE_STATUS_COLORS[status] || 'bg-slate-100 text-slate-700';
    const label = INVOICE_STATUS_LABELS[status] || status;
    return (
      <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${colors}`}>
        {label}
      </span>
    );
  };

  // Workflow: which actions are available
  const isNexConnect = invoice?.ecf_provider === 'nexconnect';
  const emittedViaNexConnect = invoice?.dgii_response?.provider === 'nexconnect';
  const canEmit = isNexConnect && !emittedViaNexConnect && ['draft', 'generated'].includes(invoice?.status ?? '');
  const canRefresh = isNexConnect && emittedViaNexConnect;
  const canGenerate = invoice?.status === 'draft';
  const canSign = invoice?.status === 'generated';
  const canSubmit = invoice?.status === 'signed';
  const canCheckStatus = invoice?.status === 'submitted' && !!invoice?.dgii_trackid;
  const canDelete = invoice?.status === 'draft';

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="p-8">
        {loadError ? (
          <ErrorState variant="page" message={loadError} onRetry={loadInvoice} />
        ) : (
          <Alert variant="destructive">
            <AlertDescription>Factura no encontrada</AlertDescription>
          </Alert>
        )}
      </div>
    );
  }

  const nexconnectStepIndex = NEXCONNECT_STEP_INDEX[invoice.status] ?? NEXCONNECT_STEPS.length;
  const finalStep = FINAL_STEP[invoice.status];

  return (
    <div className="p-8">
      {confirmDialog}
      {/* Header */}
      <div className="mb-8">
        <Link href="/billing" className="inline-flex items-center text-sm text-slate-600 hover:text-slate-900 mb-4">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Volver a Facturas
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-slate-900">
                {invoice.encf_number || 'Factura Borrador'}
              </h1>
              {getStatusBadge(invoice.status)}
            </div>
            <p className="text-sm text-slate-600">
              {ECF_TYPE_LABELS[invoice.ecf_type as ECFType] || invoice.ecf_type} • Creada {formatDate(invoice.created_at)}
            </p>
          </div>
          <div className="flex gap-2">
            {canDelete && (
              <Button variant="outline" className="text-red-600 hover:text-red-700" onClick={handleDelete}>
                <Trash2 className="mr-2 h-4 w-4" />
                Eliminar
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Alerts */}
      {error && <ErrorState message={error} className="mb-6" />}
      {success && (
        <Alert className="mb-6 border-green-200 bg-green-50">
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}
      {invoice.status === 'rejected' && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <p className="font-semibold">La DGII rechazó este e-CF.</p>
            <p className="mt-1">
              {invoice.dgii_error_message || 'La DGII no indicó el motivo.'}
              {invoice.dgii_response?.dgii_error_code && (
                <span className="ml-1 font-mono text-xs">(código {invoice.dgii_response.dgii_error_code})</span>
              )}
            </p>
          </AlertDescription>
        </Alert>
      )}

      {/* Workflow Actions Bar */}
      {isNexConnect ? (
      <Card className="mb-6 border-blue-200 bg-blue-50/50 shadow-sm">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium text-blue-900">Emisión vía NexConnect:</p>
              <ol className="flex items-center gap-1" aria-label="Progreso de la emisión">
                {NEXCONNECT_STEPS.map((label, idx) => {
                  const isCompleted = idx < nexconnectStepIndex;
                  const isCurrent = idx === nexconnectStepIndex;
                  return (
                    <li key={label} className="flex items-center" aria-current={isCurrent ? 'step' : undefined}>
                      {idx > 0 && <div className={`w-6 h-0.5 ${isCompleted || isCurrent ? 'bg-green-500' : 'bg-slate-300'}`} />}
                      <div className={`
                        px-2 py-1 rounded text-xs font-medium
                        ${isCompleted ? 'bg-green-100 text-green-700' : ''}
                        ${isCurrent ? 'bg-blue-600 text-white' : ''}
                        ${!isCompleted && !isCurrent ? 'bg-slate-200 text-slate-500' : ''}
                      `}>
                        {label}
                      </div>
                    </li>
                  );
                })}
                <li className="flex items-center" aria-current={finalStep ? 'step' : undefined}>
                  <div className={`w-6 h-0.5 ${finalStep ? 'bg-green-500' : 'bg-slate-300'}`} />
                  <div className={`px-2 py-1 rounded text-xs font-medium ${finalStep ? finalStep.className : 'bg-slate-200 text-slate-500'}`}>
                    {finalStep ? finalStep.label : 'Aceptado / Rechazado'}
                  </div>
                </li>
              </ol>
            </div>
            <div className="flex gap-2">
              {canEmit && (
                <Button size="sm" className="bg-green-600 hover:bg-green-700" onClick={handleEmit} disabled={!!actionLoading}>
                  {actionLoading === 'emit' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                  Emitir vía NexConnect
                </Button>
              )}
              {canRefresh && (
                <Button size="sm" variant="outline" onClick={handleRefreshStatus} disabled={!!actionLoading}>
                  {actionLoading === 'refresh' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                  Actualizar estado
                </Button>
              )}
            </div>
          </div>
          {emittedViaNexConnect && !invoice.is_final && (
            <p className="mt-2 text-xs text-blue-900/80">
              <Clock className="mr-1 inline h-3.5 w-3.5" aria-hidden />
              NexConnect avisa automáticamente cuando la DGII responde; «Actualizar estado» consulta ahora mismo.
            </p>
          )}
        </CardContent>
      </Card>
      ) : (
      <Card className="mb-6 border-blue-200 bg-blue-50/50 shadow-sm">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-blue-900">Flujo de emisión:</p>
              <div className="flex items-center gap-1">
                {['draft', 'generated', 'signed', 'submitted', 'accepted'].map((step, idx) => {
                  const stepLabels: Record<string, string> = {
                    draft: 'Borrador',
                    generated: 'XML',
                    signed: 'Firmado',
                    submitted: 'Enviado',
                    accepted: 'Aceptado',
                  };
                  const steps = ['draft', 'generated', 'signed', 'submitted', 'accepted'];
                  const currentIdx = steps.indexOf(invoice.status);
                  const isCompleted = idx < currentIdx;
                  const isCurrent = idx === currentIdx;
                  return (
                    <div key={step} className="flex items-center">
                      {idx > 0 && <div className={`w-6 h-0.5 ${isCompleted ? 'bg-green-500' : 'bg-slate-300'}`} />}
                      <div className={`
                        px-2 py-1 rounded text-xs font-medium
                        ${isCompleted ? 'bg-green-100 text-green-700' : ''}
                        ${isCurrent ? 'bg-blue-600 text-white' : ''}
                        ${!isCompleted && !isCurrent ? 'bg-slate-200 text-slate-500' : ''}
                      `}>
                        {stepLabels[step]}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex gap-2">
              {canGenerate && (
                <Button size="sm" onClick={handleGenerateECF} disabled={!!actionLoading}>
                  {actionLoading === 'generate' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileCode className="mr-2 h-4 w-4" />}
                  Generar XML
                </Button>
              )}
              {canSign && (
                <Button size="sm" onClick={handleSignECF} disabled={!!actionLoading}>
                  {actionLoading === 'sign' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Shield className="mr-2 h-4 w-4" />}
                  Firmar
                </Button>
              )}
              {canSubmit && (
                <Button size="sm" className="bg-green-600 hover:bg-green-700" onClick={handleSubmitDGII} disabled={!!actionLoading}>
                  {actionLoading === 'submit' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                  Enviar a DGII
                </Button>
              )}
              {canCheckStatus && (
                <Button size="sm" variant="outline" onClick={handleCheckStatus} disabled={!!actionLoading}>
                  {actionLoading === 'check' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                  Consultar Estado
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* Left: Invoice Details */}
        <div className="col-span-2 space-y-6">
          {/* Emisor / Comprador */}
          <div className="grid grid-cols-2 gap-6">
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 pb-3">
                <CardTitle className="text-sm font-semibold text-slate-700">Emisor</CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <p className="font-medium text-slate-900">{invoice.emisor_razon_social || '—'}</p>
                <p className="text-sm text-slate-600">RNC: {invoice.emisor_rnc || '—'}</p>
              </CardContent>
            </Card>
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 pb-3">
                <CardTitle className="text-sm font-semibold text-slate-700">Comprador</CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <p className="font-medium text-slate-900">{invoice.comprador_razon_social || '—'}</p>
                <p className="text-sm text-slate-600">RNC: {invoice.comprador_rnc || '—'}</p>
              </CardContent>
            </Card>
          </div>

          {/* Line Items */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="border-b border-slate-200">
              <CardTitle className="text-base font-semibold text-slate-900">Detalle de Líneas</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">#</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Descripción</th>
                    <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Cant.</th>
                    <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Precio</th>
                    <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase">ITBIS</th>
                    <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.items?.map((item) => (
                    <tr key={item.id} className="border-b border-slate-100">
                      <td className="py-3 px-4 text-sm text-slate-600">{item.line_number}</td>
                      <td className="py-3 px-4 text-sm text-slate-900">{item.description}</td>
                      <td className="py-3 px-4 text-sm text-right text-slate-700">{item.quantity}</td>
                      <td className="py-3 px-4 text-sm text-right text-slate-700">{formatCurrency(item.unit_price)}</td>
                      <td className="py-3 px-4 text-sm text-right text-slate-600">{formatCurrency(item.itbis_amount)}</td>
                      <td className="py-3 px-4 text-sm text-right font-medium text-slate-900">{formatCurrency(item.total)}</td>
                    </tr>
                  ))}
                  {(!invoice.items || invoice.items.length === 0) && (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-slate-500">Sin líneas de detalle</td>
                    </tr>
                  )}
                </tbody>
              </table>

              {/* Totals */}
              <div className="border-t border-slate-200 p-4">
                <div className="flex flex-col items-end gap-1">
                  <div className="flex items-center justify-between w-64">
                    <span className="text-sm text-slate-600">Subtotal:</span>
                    <span className="text-sm font-medium text-slate-900">{formatCurrency(invoice.subtotal)}</span>
                  </div>
                  {Number(invoice.total_discount) > 0 && (
                    <div className="flex items-center justify-between w-64">
                      <span className="text-sm text-slate-600">Descuento:</span>
                      <span className="text-sm font-medium text-red-600">-{formatCurrency(invoice.total_discount)}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between w-64">
                    <span className="text-sm text-slate-600">ITBIS:</span>
                    <span className="text-sm font-medium text-slate-900">{formatCurrency(invoice.total_itbis)}</span>
                  </div>
                  <div className="flex items-center justify-between w-64 pt-2 border-t border-slate-200">
                    <span className="text-base font-bold text-slate-900">Total:</span>
                    <span className="text-lg font-bold text-blue-600">{formatCurrency(invoice.total)}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* XML Content */}
          {(invoice.xml_content || invoice.signed_xml) && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-semibold text-slate-900">
                    {emittedViaNexConnect ? 'XML firmado por NexConnect' : 'XML del e-CF'}
                  </CardTitle>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setShowXML(!showXML)}>
                      <FileCode className="mr-2 h-4 w-4" />
                      {showXML ? 'Ocultar' : 'Mostrar'} XML
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(invoice.signed_xml || invoice.xml_content)}
                    >
                      <Copy className="mr-2 h-4 w-4" />
                      Copiar
                    </Button>
                  </div>
                </div>
              </CardHeader>
              {showXML && (
                <CardContent className="p-4">
                  <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-96">
                    {invoice.signed_xml || invoice.xml_content}
                  </pre>
                </CardContent>
              )}
            </Card>
          )}
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          {/* Invoice Info */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="border-b border-slate-200">
              <CardTitle className="text-sm font-semibold text-slate-700">Información</CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              <div>
                <p className="text-xs text-slate-500">Tipo e-CF</p>
                <p className="text-sm font-medium text-slate-900">
                  {invoice.ecf_type} — {ECF_TYPE_LABELS[invoice.ecf_type as ECFType]}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Fecha Emisión</p>
                <p className="text-sm font-medium text-slate-900">{formatDate(invoice.issue_date)}</p>
              </div>
              {invoice.due_date && (
                <div>
                  <p className="text-xs text-slate-500">Fecha Vencimiento</p>
                  <p className="text-sm font-medium text-slate-900">{formatDate(invoice.due_date)}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-slate-500">Forma de Pago</p>
                <p className="text-sm font-medium text-slate-900">
                  {PAYMENT_METHOD_LABELS[invoice.payment_method as PaymentMethod] || invoice.payment_method}
                </p>
              </div>
              {invoice.security_code && !emittedViaNexConnect && (
                <div>
                  <p className="text-xs text-slate-500">Código Seguridad</p>
                  <p className="text-sm font-mono font-medium text-slate-900">{invoice.security_code}</p>
                </div>
              )}
              {invoice.notes && (
                <div>
                  <p className="text-xs text-slate-500">Notas</p>
                  <p className="text-sm text-slate-700">{invoice.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* NexConnect / DGII Status */}
          {emittedViaNexConnect && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200">
                <CardTitle className="text-sm font-semibold text-slate-700">e-CF en NexConnect</CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-3">
                <div>
                  <p className="text-xs text-slate-500">e-NCF</p>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-mono font-medium text-slate-900">{invoice.encf_number || '—'}</p>
                    {invoice.encf_number && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-1.5"
                        onClick={() => copyToClipboard(invoice.encf_number!)}
                        aria-label="Copiar e-NCF"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Código de seguridad</p>
                  <p className="text-sm font-mono font-medium text-slate-900">{invoice.security_code || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Estado</p>
                  <p className="text-sm font-medium text-slate-900">
                    {NEXCONNECT_STATUS_LABELS[invoice.dgii_status] || invoice.dgii_status || 'Pendiente'}
                  </p>
                </div>
                {invoice.dgii_trackid && (
                  <div>
                    <p className="text-xs text-slate-500">TrackId DGII</p>
                    <p className="text-sm font-mono text-slate-900 break-all">{invoice.dgii_trackid}</p>
                  </div>
                )}
                {invoice.dgii_submitted_at && (
                  <div>
                    <p className="text-xs text-slate-500">Emitido</p>
                    <p className="text-sm text-slate-700">{formatDateTime(invoice.dgii_submitted_at)}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* DGII Status */}
          {invoice.dgii_trackid && !emittedViaNexConnect && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200">
                <CardTitle className="text-sm font-semibold text-slate-700">Estado DGII</CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-3">
                <div>
                  <p className="text-xs text-slate-500">TrackId</p>
                  <p className="text-sm font-mono text-slate-900">{invoice.dgii_trackid}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Estado</p>
                  <p className="text-sm font-medium text-slate-900 capitalize">{invoice.dgii_status || 'Pendiente'}</p>
                </div>
                {invoice.dgii_submitted_at && (
                  <div>
                    <p className="text-xs text-slate-500">Enviado</p>
                    <p className="text-sm text-slate-700">{formatDateTime(invoice.dgii_submitted_at)}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Submission History */}
          {submissions.length > 0 && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200">
                <CardTitle className="text-sm font-semibold text-slate-700">
                  Historial de Envíos ({submissions.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="space-y-3">
                  {submissions.map((sub) => (
                    <div key={sub.id} className="border-l-2 border-slate-200 pl-3">
                      <p className="text-xs font-medium text-slate-900">
                        {(emittedViaNexConnect && SUBMISSION_ACTION_LABELS[sub.action]) || sub.action_display}
                      </p>
                      <p className="text-xs text-slate-600">{sub.environment_display}</p>
                      <p className="text-xs text-slate-500">{formatDateTime(sub.submitted_at)}</p>
                      {sub.response_status && (
                        <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full ${submissionStatusClass(sub.response_status)}`}>
                          {(emittedViaNexConnect && NEXCONNECT_STATUS_LABELS[sub.response_status]) || sub.response_status}
                        </span>
                      )}
                      {sub.error_message && (
                        <p className="text-xs text-red-600 mt-1">{sub.error_message}</p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
