'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { NativeSelect as Select } from '@/components/ui/native-select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  ArrowLeft,
  Plus,
  Receipt,
  AlertTriangle,
  CheckCircle,
  Save,
} from 'lucide-react';
import { FiscalSequence, ECF_TYPE_LABELS, ECFType } from '@/types/billing';

export default function SequencesPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [sequences, setSequences] = useState<FiscalSequence[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showForm, setShowForm] = useState(false);

  // New sequence form
  const [newEcfType, setNewEcfType] = useState('31');
  const [newPrefix, setNewPrefix] = useState('E31');
  const [newRangeFrom, setNewRangeFrom] = useState(1);
  const [newRangeTo, setNewRangeTo] = useState(1000);
  const [newExpDate, setNewExpDate] = useState('');
  const [newAuthNum, setNewAuthNum] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) loadSequences();
  }, [isAuthenticated]);

  const loadSequences = async () => {
    try {
      setIsLoading(true);
      const response = await billingAPI.getSequences();
      setSequences(response.results || []);
    } catch (err) {
      setError('Error al cargar las secuencias');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateSequence = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSaving(true);
      setError('');
      await billingAPI.createSequence({
        ecf_type: newEcfType as any,
        prefix: newPrefix,
        range_from: newRangeFrom,
        range_to: newRangeTo,
        current_number: newRangeFrom,
        expiration_date: newExpDate || null,
        authorization_number: newAuthNum,
        is_active: true,
      });
      setSuccess('Secuencia creada exitosamente');
      setShowForm(false);
      loadSequences();
    } catch (err: any) {
      setError(err?.response?.data ? JSON.stringify(err.response.data) : 'Error al crear secuencia');
    } finally {
      setIsSaving(false);
    }
  };

  // Auto-set prefix when ecf_type changes
  useEffect(() => {
    setNewPrefix(`E${newEcfType}`);
  }, [newEcfType]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="mb-8">
        <Link href="/billing" className="inline-flex items-center text-sm text-slate-600 hover:text-slate-900 mb-4">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Volver a Facturación
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Secuencias Fiscales (e-NCF)</h1>
            <p className="text-sm text-slate-600 mt-1">
              Administra los rangos de secuencias autorizados por la DGII
            </p>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700" onClick={() => setShowForm(!showForm)}>
            <Plus className="mr-2 h-4 w-4" />
            Nueva Secuencia
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="mb-6 border-green-200 bg-green-50">
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* New Sequence Form */}
      {showForm && (
        <Card className="mb-6 border-blue-200 bg-blue-50/30 shadow-sm">
          <CardHeader className="border-b border-blue-200">
            <CardTitle className="text-base font-semibold text-slate-900">Nueva Secuencia Fiscal</CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <form onSubmit={handleCreateSequence}>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">Tipo e-CF *</Label>
                  <Select value={newEcfType} onChange={(e) => setNewEcfType(e.target.value)}>
                    {Object.entries(ECF_TYPE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>{value} — {label}</option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">Prefijo *</Label>
                  <Input value={newPrefix} onChange={(e) => setNewPrefix(e.target.value)} placeholder="E31" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">No. Autorización</Label>
                  <Input value={newAuthNum} onChange={(e) => setNewAuthNum(e.target.value)} placeholder="Opcional" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">Rango Desde *</Label>
                  <Input type="number" min="1" value={newRangeFrom} onChange={(e) => setNewRangeFrom(parseInt(e.target.value) || 1)} />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">Rango Hasta *</Label>
                  <Input type="number" min="1" value={newRangeTo} onChange={(e) => setNewRangeTo(parseInt(e.target.value) || 1000)} />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">Fecha Vencimiento</Label>
                  <Input type="date" value={newExpDate} onChange={(e) => setNewExpDate(e.target.value)} />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
                <Button type="submit" className="bg-blue-600 hover:bg-blue-700" disabled={isSaving}>
                  {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                  Crear Secuencia
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Sequences List */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      ) : sequences.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="text-center py-12">
            <Receipt className="h-12 w-12 text-slate-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-2">Sin secuencias fiscales</h3>
            <p className="text-slate-600">Agrega las secuencias autorizadas por la DGII para comenzar a facturar</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Tipo</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Prefijo</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Rango</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Actual</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Disponibles</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Vencimiento</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Estado</th>
                </tr>
              </thead>
              <tbody>
                {sequences.map((seq) => {
                  const usagePercent = ((seq.current_number - seq.range_from) / (seq.range_to - seq.range_from + 1)) * 100;
                  const isLow = seq.available_count < 50;

                  return (
                    <tr key={seq.id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700">
                          {seq.ecf_type}
                        </span>
                        <p className="text-xs text-slate-500 mt-1">{seq.ecf_type_display}</p>
                      </td>
                      <td className="py-3 px-4">
                        <p className="font-mono font-medium text-slate-900">{seq.prefix}</p>
                      </td>
                      <td className="py-3 px-4">
                        <p className="text-sm text-slate-700">{seq.range_from.toLocaleString()} — {seq.range_to.toLocaleString()}</p>
                      </td>
                      <td className="py-3 px-4">
                        <p className="font-mono text-sm font-medium text-slate-900">{seq.current_number.toLocaleString()}</p>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          {isLow && !seq.is_exhausted && (
                            <AlertTriangle className="h-4 w-4 text-orange-500" />
                          )}
                          <div>
                            <p className={`text-sm font-medium ${seq.is_exhausted ? 'text-red-600' : isLow ? 'text-orange-600' : 'text-slate-900'}`}>
                              {seq.available_count.toLocaleString()}
                            </p>
                            {/* Progress bar */}
                            <div className="w-20 h-1.5 bg-slate-200 rounded-full mt-1">
                              <div
                                className={`h-1.5 rounded-full ${usagePercent > 90 ? 'bg-red-500' : usagePercent > 70 ? 'bg-orange-500' : 'bg-green-500'}`}
                                style={{ width: `${Math.min(usagePercent, 100)}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <p className="text-sm text-slate-700">{formatDate(seq.expiration_date)}</p>
                      </td>
                      <td className="py-3 px-4">
                        {seq.is_exhausted ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700">
                            Agotada
                          </span>
                        ) : seq.is_active ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-700">
                            <CheckCircle className="h-3 w-3" />
                            Activa
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
                            Inactiva
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
