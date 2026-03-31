'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { apiClient } from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { NativeSelect } from '@/components/ui/native-select';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  ArrowLeft,
  Download,
  FileSpreadsheet,
  TrendingUp,
  DollarSign,
  Receipt,
  AlertCircle,
  Calendar,
  Building2,
  Banknote,
  CreditCard,
  ArrowRightLeft,
  Info,
  FileText,
} from 'lucide-react';

interface Report607Summary {
  periodo: string;
  total_registros: number;
  total_facturado: number;
  total_efectivo: number;
  total_cheque_transferencia: number;
  total_tarjeta: number;
  total_interes_cobrado: number;
  total_capital_cobrado: number;
  total_mora_cobrada: number;
  total_itbis: number;
}

interface Report607Detail {
  cliente: string;
  rnc_cedula: string;
  prestamo: string;
  pago: string;
  fecha: string;
  monto: string;
  interes: string;
  capital: string;
  mora: string;
  metodo_efectivo: string;
  metodo_cheque: string;
  metodo_tarjeta: string;
}

interface Report606Summary {
  periodo: string;
  total_registros: number;
  total_facturado: number;
  total_itbis: number;
  nota?: string;
}

const MONTHS = [
  { value: '1', label: 'Enero' }, { value: '2', label: 'Febrero' },
  { value: '3', label: 'Marzo' }, { value: '4', label: 'Abril' },
  { value: '5', label: 'Mayo' }, { value: '6', label: 'Junio' },
  { value: '7', label: 'Julio' }, { value: '8', label: 'Agosto' },
  { value: '9', label: 'Septiembre' }, { value: '10', label: 'Octubre' },
  { value: '11', label: 'Noviembre' }, { value: '12', label: 'Diciembre' },
];

export default function DGIIReportsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();

  const now = new Date();
  const [year, setYear] = useState(now.getFullYear().toString());
  const [month, setMonth] = useState(now.getMonth().toString()); // Previous month default
  const [activeTab, setActiveTab] = useState<'607' | '606'>('607');

  const [loading607, setLoading607] = useState(false);
  const [loading606, setLoading606] = useState(false);
  const [summary607, setSummary607] = useState<Report607Summary | null>(null);
  const [detail607, setDetail607] = useState<Report607Detail[]>([]);
  const [summary606, setSummary606] = useState<Report606Summary | null>(null);
  const [error, setError] = useState('');

  const currencySymbol = config?.currency_symbol || 'RD$';
  const formatCurrency = (amount: number | string | undefined) => {
    if (amount === undefined || amount === null) return `${currencySymbol}0.00`;
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(num)) return `${currencySymbol}0.00`;
    return `${currencySymbol}${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDGIIDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr;
    return `${dateStr.substring(6, 8)}/${dateStr.substring(4, 6)}/${dateStr.substring(0, 4)}`;
  };

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  // Generate available years (current year and 2 prior)
  const years = Array.from({ length: 3 }, (_, i) => {
    const y = now.getFullYear() - i;
    return { value: y.toString(), label: y.toString() };
  });

  const fetch607 = async () => {
    setLoading607(true);
    setError('');
    try {
      const data = await apiClient.get<any>(`/api/billing/dgii-reports/607/?year=${year}&month=${month}`);
      setSummary607(data.resumen);
      setDetail607(data.detalle || []);
    } catch (err: any) {
      setError(err?.message || 'Error generando reporte 607');
    } finally {
      setLoading607(false);
    }
  };

  const fetch606 = async () => {
    setLoading606(true);
    setError('');
    try {
      const data = await apiClient.get<any>(`/api/billing/dgii-reports/606/?year=${year}&month=${month}`);
      setSummary606(data.resumen);
    } catch (err: any) {
      setError(err?.message || 'Error generando reporte 606');
    } finally {
      setLoading606(false);
    }
  };

  const handleGenerate = () => {
    if (activeTab === '607') fetch607();
    else fetch606();
  };

  const handleDownloadCSV = (reportType: '606' | '607') => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
    window.open(`${baseUrl}/api/billing/dgii-reports/${reportType}/csv/?year=${year}&month=${month}`, '_blank');
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/billing">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Reportes DGII</h1>
            <p className="text-sm text-gray-500">Formatos 606 y 607 para la Dirección General de Impuestos Internos</p>
          </div>
        </div>
      </div>

      {/* Period Selector + Tab */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-end gap-4">
            {/* Report Type Tabs */}
            <div className="flex gap-1 p-1 bg-gray-100 rounded-lg">
              <button
                onClick={() => setActiveTab('607')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === '607'
                    ? 'bg-[#163300] text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <TrendingUp className="h-4 w-4 inline mr-1.5" />
                607 — Ventas
              </button>
              <button
                onClick={() => setActiveTab('606')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === '606'
                    ? 'bg-[#163300] text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <Receipt className="h-4 w-4 inline mr-1.5" />
                606 — Compras
              </button>
            </div>

            {/* Period */}
            <div className="flex gap-3">
              <div>
                <Label className="text-xs text-gray-500">Año</Label>
                <NativeSelect value={year} onChange={(e) => setYear(e.target.value)} className="w-24">
                  {years.map(y => <option key={y.value} value={y.value}>{y.label}</option>)}
                </NativeSelect>
              </div>
              <div>
                <Label className="text-xs text-gray-500">Mes</Label>
                <NativeSelect value={month} onChange={(e) => setMonth(e.target.value)} className="w-36">
                  {MONTHS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </NativeSelect>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button onClick={handleGenerate} disabled={loading607 || loading606} className="bg-[#163300] hover:bg-[#1e4400]">
                {(loading607 || loading606) ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <FileSpreadsheet className="h-4 w-4 mr-2" />}
                Generar Reporte
              </Button>
              <Button
                variant="outline"
                onClick={() => handleDownloadCSV(activeTab)}
                disabled={loading607 || loading606}
              >
                <Download className="h-4 w-4 mr-2" />
                Descargar CSV
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* 607 Content */}
      {activeTab === '607' && summary607 && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-50 rounded-lg">
                    <FileText className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Registros</p>
                    <p className="text-2xl font-bold text-gray-900">{summary607.total_registros}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <DollarSign className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Total Facturado</p>
                    <p className="text-xl font-bold text-gray-900">{formatCurrency(summary607.total_facturado)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-50 rounded-lg">
                    <TrendingUp className="h-5 w-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Interés Cobrado</p>
                    <p className="text-xl font-bold text-gray-900">{formatCurrency(summary607.total_interes_cobrado)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-50 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-red-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Mora Cobrada</p>
                    <p className="text-xl font-bold text-gray-900">{formatCurrency(summary607.total_mora_cobrada)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Payment Method Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Desglose por Método de Pago</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Banknote className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="text-xs text-gray-500">Efectivo</p>
                    <p className="font-semibold">{formatCurrency(summary607.total_efectivo)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <ArrowRightLeft className="h-5 w-5 text-blue-600" />
                  <div>
                    <p className="text-xs text-gray-500">Cheque/Transferencia</p>
                    <p className="font-semibold">{formatCurrency(summary607.total_cheque_transferencia)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <CreditCard className="h-5 w-5 text-purple-600" />
                  <div>
                    <p className="text-xs text-gray-500">Tarjeta</p>
                    <p className="font-semibold">{formatCurrency(summary607.total_tarjeta)}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ITBIS Note */}
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <strong>Nota sobre ITBIS:</strong> Los intereses de préstamos están{' '}
              <strong>exentos de ITBIS</strong> según la legislación dominicana.
              Las comisiones de desembolso y servicios sí pagan el 18%.
            </AlertDescription>
          </Alert>

          {/* Detail Table */}
          {detail607.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Detalle de Registros ({detail607.length})</CardTitle>
                <CardDescription>Cada pago recibido es un registro en el 607</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="text-left py-2.5 px-3 font-medium text-gray-600">Cliente</th>
                        <th className="text-left py-2.5 px-3 font-medium text-gray-600">RNC/Cédula</th>
                        <th className="text-left py-2.5 px-3 font-medium text-gray-600">Préstamo</th>
                        <th className="text-left py-2.5 px-3 font-medium text-gray-600">Fecha</th>
                        <th className="text-right py-2.5 px-3 font-medium text-gray-600">Monto</th>
                        <th className="text-right py-2.5 px-3 font-medium text-gray-600">Interés</th>
                        <th className="text-right py-2.5 px-3 font-medium text-gray-600">Capital</th>
                        <th className="text-right py-2.5 px-3 font-medium text-gray-600">Mora</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {detail607.map((row, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="py-2 px-3 text-gray-900">{row.cliente}</td>
                          <td className="py-2 px-3 text-gray-600 font-mono text-xs">{row.rnc_cedula}</td>
                          <td className="py-2 px-3 text-gray-600">{row.prestamo}</td>
                          <td className="py-2 px-3 text-gray-600">{formatDGIIDate(row.fecha)}</td>
                          <td className="py-2 px-3 text-right font-medium">{formatCurrency(row.monto)}</td>
                          <td className="py-2 px-3 text-right text-green-700">{formatCurrency(row.interes)}</td>
                          <td className="py-2 px-3 text-right text-blue-700">{formatCurrency(row.capital)}</td>
                          <td className="py-2 px-3 text-right text-red-600">{formatCurrency(row.mora)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t-2 font-semibold bg-gray-50">
                        <td colSpan={4} className="py-2.5 px-3">TOTALES</td>
                        <td className="py-2.5 px-3 text-right">{formatCurrency(summary607.total_facturado)}</td>
                        <td className="py-2.5 px-3 text-right text-green-700">{formatCurrency(summary607.total_interes_cobrado)}</td>
                        <td className="py-2.5 px-3 text-right text-blue-700">{formatCurrency(summary607.total_capital_cobrado)}</td>
                        <td className="py-2.5 px-3 text-right text-red-600">{formatCurrency(summary607.total_mora_cobrada)}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* 606 Content */}
      {activeTab === '606' && summary606 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Receipt className="h-5 w-5" />
              Reporte 606 — Compras y Gastos
            </CardTitle>
            <CardDescription>Período: {summary606.periodo}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="p-4 bg-gray-50 rounded-lg text-center">
                <p className="text-xs text-gray-500">Registros</p>
                <p className="text-2xl font-bold">{summary606.total_registros}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg text-center">
                <p className="text-xs text-gray-500">Total Facturado</p>
                <p className="text-xl font-bold">{formatCurrency(summary606.total_facturado)}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg text-center">
                <p className="text-xs text-gray-500">ITBIS</p>
                <p className="text-xl font-bold">{formatCurrency(summary606.total_itbis)}</p>
              </div>
            </div>

            {summary606.nota && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>{summary606.nota}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Empty state when no data generated yet */}
      {activeTab === '607' && !summary607 && !loading607 && (
        <Card>
          <CardContent className="py-16 text-center">
            <FileSpreadsheet className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600">Selecciona un período</h3>
            <p className="text-sm text-gray-400 mt-1">Elige año y mes, luego haz clic en "Generar Reporte"</p>
          </CardContent>
        </Card>
      )}

      {activeTab === '606' && !summary606 && !loading606 && (
        <Card>
          <CardContent className="py-16 text-center">
            <FileSpreadsheet className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600">Selecciona un período</h3>
            <p className="text-sm text-gray-400 mt-1">Elige año y mes, luego haz clic en "Generar Reporte"</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
