'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { cashboxAPI, CashSession, CashMovement, SessionSummary, CashRegister } from '@/lib/api/cashbox';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { NativeSelect } from '@/components/ui/native-select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  DollarSign,
  ArrowUpCircle,
  ArrowDownCircle,
  Lock,
  Unlock,
  Plus,
  Clock,
  Banknote,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  Calculator,
  X,
  RefreshCw,
  User,
  Building,
} from 'lucide-react';

const INFLOW_CATEGORIES = [
  { value: 'loan_payment', label: 'Pago de préstamo' },
  { value: 'loan_payoff', label: 'Saldo de préstamo' },
  { value: 'commission', label: 'Comisión cobrada' },
  { value: 'late_fee', label: 'Mora cobrada' },
  { value: 'insurance', label: 'Seguro cobrado' },
  { value: 'other_income', label: 'Otro ingreso' },
];

const OUTFLOW_CATEGORIES = [
  { value: 'loan_disbursement', label: 'Desembolso de préstamo' },
  { value: 'expense', label: 'Gasto operativo' },
  { value: 'withdrawal', label: 'Retiro de efectivo' },
  { value: 'refund', label: 'Devolución' },
  { value: 'salary', label: 'Pago de nómina' },
  { value: 'other_expense', label: 'Otro gasto' },
];

export default function CashboxPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();

  const [registers, setRegisters] = useState<CashRegister[]>([]);
  const [activeSession, setActiveSession] = useState<CashSession | null>(null);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [movements, setMovements] = useState<CashMovement[]>([]);
  const [recentSessions, setRecentSessions] = useState<CashSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modals
  const [showOpenModal, setShowOpenModal] = useState(false);
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [showMovementModal, setShowMovementModal] = useState(false);
  const [movementType, setMovementType] = useState<'inflow' | 'outflow'>('inflow');

  // Form state
  const [selectedRegister, setSelectedRegister] = useState('');
  const [openingBalance, setOpeningBalance] = useState('');
  const [openingNotes, setOpeningNotes] = useState('');
  const [closingBalance, setClosingBalance] = useState('');
  const [closingNotes, setClosingNotes] = useState('');
  const [movAmount, setMovAmount] = useState('');
  const [movCategory, setMovCategory] = useState('');
  const [movDescription, setMovDescription] = useState('');
  const [movReference, setMovReference] = useState('');
  const [movCustomerName, setMovCustomerName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const currencySymbol = config?.currency_symbol || 'RD$';
  const fmt = (n: number | null | undefined) => {
    if (n === null || n === undefined) return `${currencySymbol}0.00`;
    const num = typeof n === 'string' ? parseFloat(n) : n;
    return `${currencySymbol}${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  const fetchData = async () => {
    try {
      setError('');
      const [regs, active, sessions] = await Promise.all([
        cashboxAPI.getRegisters(),
        cashboxAPI.getActiveSessions().catch(() => []),
        cashboxAPI.getSessions().catch(() => []),
      ]);
      setRegisters(regs);
      setRecentSessions(sessions.slice(0, 10));

      if (active.length > 0) {
        const session = active[0];
        setActiveSession(session);
        const [sum, movs] = await Promise.all([
          cashboxAPI.getSessionSummary(session.id),
          cashboxAPI.getSessionMovements(session.id),
        ]);
        setSummary(sum);
        setMovements(movs);
      } else {
        setActiveSession(null);
        setSummary(null);
        setMovements([]);
      }
    } catch (err: any) {
      setError(err?.message || 'Error cargando datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) fetchData();
  }, [isAuthenticated]);

  const handleOpenSession = async () => {
    if (!selectedRegister || !openingBalance) return;
    setSubmitting(true);
    try {
      await cashboxAPI.openSession({
        register: selectedRegister,
        opening_balance: parseFloat(openingBalance),
        opening_notes: openingNotes,
      });
      setShowOpenModal(false);
      setOpeningBalance('');
      setOpeningNotes('');
      await fetchData();
    } catch (err: any) {
      setError(err?.message || 'Error abriendo caja');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCloseSession = async () => {
    if (!activeSession || !closingBalance) return;
    setSubmitting(true);
    try {
      await cashboxAPI.closeSession(activeSession.id, {
        closing_balance: parseFloat(closingBalance),
        closing_notes: closingNotes,
      });
      setShowCloseModal(false);
      setClosingBalance('');
      setClosingNotes('');
      await fetchData();
    } catch (err: any) {
      setError(err?.message || 'Error cerrando caja');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddMovement = async () => {
    if (!activeSession || !movAmount || !movCategory || !movDescription) return;
    setSubmitting(true);
    try {
      await cashboxAPI.createMovement({
        session: activeSession.id,
        movement_type: movementType,
        category: movCategory,
        amount: movAmount,
        amount_currency: 'DOP',
        description: movDescription,
        reference: movReference,
        customer_name: movCustomerName,
      });
      setShowMovementModal(false);
      setMovAmount('');
      setMovCategory('');
      setMovDescription('');
      setMovReference('');
      setMovCustomerName('');
      await fetchData();
    } catch (err: any) {
      setError(err?.message || 'Error registrando movimiento');
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Gestión de Caja</h1>
          <p className="text-sm text-gray-500">Control de efectivo, apertura y cierre de caja</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => fetchData()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
          {!activeSession ? (
            <Button onClick={() => setShowOpenModal(true)} className="bg-[#163300] hover:bg-[#1e4400]">
              <Unlock className="h-4 w-4 mr-2" />
              Abrir Caja
            </Button>
          ) : (
            <Button onClick={() => setShowCloseModal(true)} variant="destructive">
              <Lock className="h-4 w-4 mr-2" />
              Cerrar Caja
            </Button>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Active Session */}
      {activeSession && summary ? (
        <>
          {/* Session Info Bar */}
          <Card className="border-green-200 bg-green-50/50">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Unlock className="h-5 w-5 text-green-700" />
                  </div>
                  <div>
                    <p className="font-medium text-green-800">
                      Caja Abierta — {activeSession.register_name}
                    </p>
                    <p className="text-xs text-green-600">
                      {activeSession.cashier_name} · Desde {new Date(activeSession.opened_at).toLocaleString('es-DO')}
                    </p>
                  </div>
                </div>
                <Badge className="bg-green-100 text-green-800 border-green-300">
                  {summary.movement_count} movimientos
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-100 rounded-lg">
                    <Banknote className="h-4 w-4 text-gray-600" />
                  </div>
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wide">Apertura</p>
                    <p className="text-lg font-bold">{fmt(summary.opening_balance)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-50 rounded-lg">
                    <ArrowUpCircle className="h-4 w-4 text-green-600" />
                  </div>
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wide">Entradas</p>
                    <p className="text-lg font-bold text-green-700">{fmt(summary.total_inflows)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-50 rounded-lg">
                    <ArrowDownCircle className="h-4 w-4 text-red-600" />
                  </div>
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wide">Salidas</p>
                    <p className="text-lg font-bold text-red-700">{fmt(summary.total_outflows)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <Calculator className="h-4 w-4 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wide">Esperado</p>
                    <p className="text-lg font-bold text-blue-700">{fmt(summary.expected_balance)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-50 rounded-lg">
                    <DollarSign className="h-4 w-4 text-amber-600" />
                  </div>
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wide">Neto Hoy</p>
                    <p className="text-lg font-bold">
                      {fmt(summary.opening_balance + summary.total_inflows - summary.total_outflows)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              onClick={() => { setMovementType('inflow'); setMovCategory('loan_payment'); setShowMovementModal(true); }}
              className="bg-green-700 hover:bg-green-800"
            >
              <ArrowUpCircle className="h-4 w-4 mr-2" />
              Registrar Entrada
            </Button>
            <Button
              onClick={() => { setMovementType('outflow'); setMovCategory('loan_disbursement'); setShowMovementModal(true); }}
              variant="outline"
              className="border-red-200 text-red-700 hover:bg-red-50"
            >
              <ArrowDownCircle className="h-4 w-4 mr-2" />
              Registrar Salida
            </Button>
          </div>

          {/* Category Breakdown */}
          {(summary.inflows_by_category.length > 0 || summary.outflows_by_category.length > 0) && (
            <div className="grid md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm text-green-700 flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" /> Entradas por Categoría
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {summary.inflows_by_category.length === 0 ? (
                    <p className="text-sm text-gray-400">Sin entradas</p>
                  ) : (
                    <div className="space-y-2">
                      {summary.inflows_by_category.map((cat, i) => (
                        <div key={i} className="flex justify-between items-center py-1.5 border-b border-gray-100 last:border-0">
                          <span className="text-sm text-gray-600 capitalize">{cat.category.replace(/_/g, ' ')}</span>
                          <span className="text-sm font-medium text-green-700">{fmt(cat.total)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm text-red-700 flex items-center gap-2">
                    <TrendingDown className="h-4 w-4" /> Salidas por Categoría
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {summary.outflows_by_category.length === 0 ? (
                    <p className="text-sm text-gray-400">Sin salidas</p>
                  ) : (
                    <div className="space-y-2">
                      {summary.outflows_by_category.map((cat, i) => (
                        <div key={i} className="flex justify-between items-center py-1.5 border-b border-gray-100 last:border-0">
                          <span className="text-sm text-gray-600 capitalize">{cat.category.replace(/_/g, ' ')}</span>
                          <span className="text-sm font-medium text-red-700">{fmt(cat.total)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* Movements Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Movimientos del Día</CardTitle>
            </CardHeader>
            <CardContent>
              {movements.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">No hay movimientos registrados</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="text-left py-2 px-3 font-medium text-gray-600">Hora</th>
                        <th className="text-left py-2 px-3 font-medium text-gray-600">Tipo</th>
                        <th className="text-left py-2 px-3 font-medium text-gray-600">Categoría</th>
                        <th className="text-left py-2 px-3 font-medium text-gray-600">Descripción</th>
                        <th className="text-left py-2 px-3 font-medium text-gray-600">Cliente</th>
                        <th className="text-right py-2 px-3 font-medium text-gray-600">Monto</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {movements.map((mov) => (
                        <tr key={mov.id} className="hover:bg-gray-50">
                          <td className="py-2 px-3 text-gray-500 text-xs">
                            {new Date(mov.created_at).toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td className="py-2 px-3">
                            {mov.movement_type === 'inflow' ? (
                              <Badge className="bg-green-50 text-green-700 border-green-200 text-[10px]">↑ Entrada</Badge>
                            ) : (
                              <Badge className="bg-red-50 text-red-700 border-red-200 text-[10px]">↓ Salida</Badge>
                            )}
                          </td>
                          <td className="py-2 px-3 text-gray-600">{mov.category_display}</td>
                          <td className="py-2 px-3 text-gray-900">{mov.description}</td>
                          <td className="py-2 px-3 text-gray-500">{mov.customer_name || '—'}</td>
                          <td className={`py-2 px-3 text-right font-medium ${mov.movement_type === 'inflow' ? 'text-green-700' : 'text-red-700'}`}>
                            {mov.movement_type === 'inflow' ? '+' : '-'}{fmt(mov.amount)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        /* No Active Session */
        <Card>
          <CardContent className="py-16 text-center">
            <Lock className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600">No hay caja abierta</h3>
            <p className="text-sm text-gray-400 mt-1 mb-6">Abre una caja para comenzar a registrar movimientos</p>
            <Button onClick={() => setShowOpenModal(true)} className="bg-[#163300] hover:bg-[#1e4400]">
              <Unlock className="h-4 w-4 mr-2" />
              Abrir Caja
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Recent Sessions */}
      {recentSessions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sesiones Recientes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recentSessions.slice(0, 5).map(sess => (
                <div key={sess.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div className="flex items-center gap-3">
                    <div className={`p-1.5 rounded ${sess.status === 'open' ? 'bg-green-100' : 'bg-gray-100'}`}>
                      {sess.status === 'open' ? <Unlock className="h-3.5 w-3.5 text-green-600" /> : <Lock className="h-3.5 w-3.5 text-gray-400" />}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{sess.register_name}</p>
                      <p className="text-xs text-gray-400">
                        {new Date(sess.opened_at).toLocaleDateString('es-DO')} · {sess.cashier_name}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">{fmt(sess.opening_balance)}</p>
                    <Badge variant="outline" className="text-[10px]">{sess.status_display}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* === MODALS === */}

      {/* Open Session Modal */}
      {showOpenModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Abrir Caja</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setShowOpenModal(false)}><X className="h-4 w-4" /></Button>
              </div>
              <CardDescription>Registra el balance de apertura</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Caja</Label>
                <NativeSelect value={selectedRegister} onChange={e => setSelectedRegister(e.target.value)}>
                  <option value="">Seleccionar caja...</option>
                  {registers.map(r => (
                    <option key={r.id} value={r.id}>{r.name} ({r.code})</option>
                  ))}
                </NativeSelect>
              </div>
              <div>
                <Label>Balance de Apertura ({currencySymbol})</Label>
                <Input type="number" step="0.01" placeholder="0.00" value={openingBalance} onChange={e => setOpeningBalance(e.target.value)} />
              </div>
              <div>
                <Label>Notas (opcional)</Label>
                <Textarea value={openingNotes} onChange={e => setOpeningNotes(e.target.value)} placeholder="Observaciones al abrir..." />
              </div>
              <Button onClick={handleOpenSession} disabled={submitting || !selectedRegister || !openingBalance} className="w-full bg-[#163300]">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Unlock className="h-4 w-4 mr-2" />}
                Abrir Caja
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Close Session Modal */}
      {showCloseModal && activeSession && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Cerrar Caja</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setShowCloseModal(false)}><X className="h-4 w-4" /></Button>
              </div>
              <CardDescription>
                Balance esperado: <strong>{fmt(summary?.expected_balance || 0)}</strong>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Balance de Cierre ({currencySymbol})</Label>
                <Input type="number" step="0.01" placeholder="0.00" value={closingBalance} onChange={e => setClosingBalance(e.target.value)} />
                {closingBalance && summary && (
                  <p className={`text-xs mt-1 ${parseFloat(closingBalance) - summary.expected_balance === 0 ? 'text-green-600' : parseFloat(closingBalance) - summary.expected_balance > 0 ? 'text-blue-600' : 'text-red-600'}`}>
                    Diferencia: {fmt(parseFloat(closingBalance) - summary.expected_balance)}
                    {parseFloat(closingBalance) - summary.expected_balance > 0 ? ' (sobrante)' : parseFloat(closingBalance) - summary.expected_balance < 0 ? ' (faltante)' : ' (cuadra ✓)'}
                  </p>
                )}
              </div>
              <div>
                <Label>Notas de Cierre (opcional)</Label>
                <Textarea value={closingNotes} onChange={e => setClosingNotes(e.target.value)} placeholder="Observaciones al cerrar..." />
              </div>
              <Button onClick={handleCloseSession} disabled={submitting || !closingBalance} variant="destructive" className="w-full">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Lock className="h-4 w-4 mr-2" />}
                Cerrar Caja
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Movement Modal */}
      {showMovementModal && activeSession && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>{movementType === 'inflow' ? '↑ Registrar Entrada' : '↓ Registrar Salida'}</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setShowMovementModal(false)}><X className="h-4 w-4" /></Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Categoría</Label>
                <NativeSelect value={movCategory} onChange={e => setMovCategory(e.target.value)}>
                  <option value="">Seleccionar...</option>
                  {(movementType === 'inflow' ? INFLOW_CATEGORIES : OUTFLOW_CATEGORIES).map(c => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </NativeSelect>
              </div>
              <div>
                <Label>Monto ({currencySymbol})</Label>
                <Input type="number" step="0.01" placeholder="0.00" value={movAmount} onChange={e => setMovAmount(e.target.value)} />
              </div>
              <div>
                <Label>Descripción</Label>
                <Input value={movDescription} onChange={e => setMovDescription(e.target.value)} placeholder="Ej: Pago cuota #5 préstamo PRE-2026-001" />
              </div>
              <div>
                <Label>Cliente (opcional)</Label>
                <Input value={movCustomerName} onChange={e => setMovCustomerName(e.target.value)} placeholder="Nombre del cliente" />
              </div>
              <div>
                <Label>Referencia (opcional)</Label>
                <Input value={movReference} onChange={e => setMovReference(e.target.value)} placeholder="Número de recibo, etc." />
              </div>
              <Button
                onClick={handleAddMovement}
                disabled={submitting || !movAmount || !movCategory || !movDescription}
                className={`w-full ${movementType === 'inflow' ? 'bg-green-700 hover:bg-green-800' : 'bg-red-600 hover:bg-red-700'}`}
              >
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
                Registrar
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
      </div>
    </div>
  );
}