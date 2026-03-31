'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { loansAPI } from '@/lib/api/loans';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { NativeSelect as Select } from '@/components/ui/native-select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Calculator,
  DollarSign,
  Calendar,
  Percent,
  Hash,
  FileText,
  TrendingUp,
  TrendingDown,
  Loader2,
  Download,
  ArrowRight,
  Info,
  Banknote,
  PiggyBank,
  Receipt,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ScheduleItem {
  installment_number: number;
  due_date: string;
  payment: string;
  principal: string;
  interest: string;
  balance: string;
}

interface CalculatorResult {
  payment_amount: string;
  total_loan: string;
  total_interest: string;
  total_disbursed: string;
  schedule: ScheduleItem[];
}

const AMORTIZATION_METHODS = [
  {
    value: 'flat',
    label: 'Interés Fijo (Flat)',
    description: 'Interés calculado sobre el monto original. Cuota fija. El más simple y común para préstamos pequeños.',
  },
  {
    value: 'saldo_insoluto',
    label: 'Saldo Insoluto',
    description: 'Interés sobre el balance pendiente. Capital fijo cada cuota, interés decrece. Estándar en financieras RD.',
  },
  {
    value: 'french',
    label: 'Francés (Cuota Fija)',
    description: 'Cuota total fija. Al inicio se paga más interés, al final más capital. El más usado mundialmente.',
  },
  {
    value: 'german',
    label: 'Alemán (Capital Fijo)',
    description: 'Capital fijo cada cuota. Cuota total decrece con el tiempo. Menor interés total.',
  },
];

const PAYMENT_FREQUENCIES = [
  { value: 'daily', label: 'Diario' },
  { value: 'weekly', label: 'Semanal' },
  { value: 'biweekly', label: 'Quincenal' },
  { value: 'monthly', label: 'Mensual' },
];

const LEGAL_FEE_CONDITIONS = [
  { value: 'deducted', label: 'Deducido del desembolso' },
  { value: 'financed', label: 'Financiado (se suma al préstamo)' },
];

function formatDOP(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('es-DO', {
    style: 'currency',
    currency: 'DOP',
    minimumFractionDigits: 2,
  }).format(num).replace('DOP', 'RD$');
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('es-DO', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function CalculatorPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  // Form state
  const [principalAmount, setPrincipalAmount] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [term, setTerm] = useState('');
  const [paymentFrequency, setPaymentFrequency] = useState('monthly');
  const [amortizationMethod, setAmortizationMethod] = useState('flat');
  const [legalFees, setLegalFees] = useState('0');
  const [legalFeesCondition, setLegalFeesCondition] = useState('deducted');
  const [startDate, setStartDate] = useState(
    new Date().toISOString().split('T')[0]
  );

  // Result state
  const [result, setResult] = useState<CalculatorResult | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState('');
  const [showAllSchedule, setShowAllSchedule] = useState(false);

  // Selected method description
  const selectedMethod = AMORTIZATION_METHODS.find(m => m.value === amortizationMethod);

  const handleCalculate = async () => {
    setError('');
    setResult(null);

    // Basic validation
    if (!principalAmount || parseFloat(principalAmount) <= 0) {
      setError('Ingrese un monto válido');
      return;
    }
    if (!interestRate || parseFloat(interestRate) < 0) {
      setError('Ingrese una tasa de interés válida');
      return;
    }
    if (!term || parseInt(term) <= 0) {
      setError('Ingrese un número de cuotas válido');
      return;
    }

    try {
      setIsCalculating(true);
      if (typeof loansAPI.calculateLoan !== 'function') {
        throw new Error('calculateLoan no está disponible. Reinicia el servidor de desarrollo.');
      }
      const data = await loansAPI.calculateLoan({
        principal_amount: principalAmount,
        interest_rate: interestRate,
        term: parseInt(term),
        payment_frequency: paymentFrequency,
        amortization_method: amortizationMethod,
        legal_fees: legalFees || '0',
        legal_fees_condition: legalFeesCondition,
        start_date: startDate,
      });
      setResult(data);
      setShowAllSchedule(false);
    } catch (err: any) {
      console.error('Calculation error:', err);
      if (err.response?.data) {
        const errData = err.response.data;
        const messages = Object.values(errData).flat().join('. ');
        setError(messages || 'Error al calcular');
      } else {
        setError('Error de conexión al servidor');
      }
    } finally {
      setIsCalculating(false);
    }
  };

  const handleCreateLoan = () => {
    if (!result) return;
    // Navigate to new loan page with pre-filled data
    const params = new URLSearchParams({
      principal: principalAmount,
      rate: interestRate,
      term: term,
      frequency: paymentFrequency,
      method: amortizationMethod,
      payment: result.payment_amount,
    });
    router.push(`/loans/new?${params.toString()}`);
  };

  const scheduleToShow = result
    ? showAllSchedule
      ? result.schedule
      : result.schedule.slice(0, 6)
    : [];

  // Redirect check
  if (!authLoading && !isAuthenticated) {
    router.push('/login');
    return null;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="h-9 w-9 rounded-lg bg-[#e8eddf] flex items-center justify-center">
            <Calculator className="h-5 w-5 text-[#163300]" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-foreground">Calculadora de Préstamos</h1>
            <p className="text-sm text-muted-foreground">
              Simula préstamos con diferentes métodos de amortización
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column — Form */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="border shadow-none">
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                Parámetros del Préstamo
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Principal Amount */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Monto del Préstamo (RD$)
                </Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="number"
                    placeholder="100,000"
                    value={principalAmount}
                    onChange={(e) => setPrincipalAmount(e.target.value)}
                    className="pl-9 h-10"
                    min="0"
                    step="1000"
                  />
                </div>
              </div>

              {/* Interest Rate */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Tasa de Interés Mensual (%)
                </Label>
                <div className="relative">
                  <Percent className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="number"
                    placeholder="3.5"
                    value={interestRate}
                    onChange={(e) => setInterestRate(e.target.value)}
                    className="pl-9 h-10"
                    min="0"
                    step="0.1"
                  />
                </div>
              </div>

              {/* Term */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Número de Cuotas
                </Label>
                <div className="relative">
                  <Hash className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="number"
                    placeholder="12"
                    value={term}
                    onChange={(e) => setTerm(e.target.value)}
                    className="pl-9 h-10"
                    min="1"
                  />
                </div>
              </div>

              {/* Payment Frequency */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Frecuencia de Pago
                </Label>
                <Select
                  value={paymentFrequency}
                  onChange={(e) => setPaymentFrequency(e.target.value)}
                  className="h-10"
                >
                  {PAYMENT_FREQUENCIES.map((freq) => (
                    <option key={freq.value} value={freq.value}>
                      {freq.label}
                    </option>
                  ))}
                </Select>
              </div>

              {/* Amortization Method */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Método de Amortización
                </Label>
                <Select
                  value={amortizationMethod}
                  onChange={(e) => setAmortizationMethod(e.target.value)}
                  className="h-10"
                >
                  {AMORTIZATION_METHODS.map((method) => (
                    <option key={method.value} value={method.value}>
                      {method.label}
                    </option>
                  ))}
                </Select>
                {selectedMethod && (
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    {selectedMethod.description}
                  </p>
                )}
              </div>

              {/* Divider */}
              <div className="border-t pt-4">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                  Gastos Legales (Opcional)
                </p>

                {/* Legal Fees */}
                <div className="space-y-1.5 mb-3">
                  <Label className="text-xs font-medium text-muted-foreground">
                    Monto Gastos Legales (RD$)
                  </Label>
                  <Input
                    type="number"
                    placeholder="0"
                    value={legalFees}
                    onChange={(e) => setLegalFees(e.target.value)}
                    className="h-10"
                    min="0"
                  />
                </div>

                {/* Legal Fees Condition */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-medium text-muted-foreground">
                    Condición
                  </Label>
                  <Select
                    value={legalFeesCondition}
                    onChange={(e) => setLegalFeesCondition(e.target.value)}
                    className="h-10"
                  >
                    {LEGAL_FEE_CONDITIONS.map((cond) => (
                      <option key={cond.value} value={cond.value}>
                        {cond.label}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>

              {/* Start Date */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Fecha de Inicio
                </Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="pl-9 h-10"
                  />
                </div>
              </div>

              {/* Error */}
              {error && (
                <Alert variant="destructive" className="py-2">
                  <AlertDescription className="text-sm">{error}</AlertDescription>
                </Alert>
              )}

              {/* Calculate Button */}
              <Button
                onClick={handleCalculate}
                disabled={isCalculating}
                className="w-full h-11 font-medium"
              >
                {isCalculating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Calculando...
                  </>
                ) : (
                  <>
                    <Calculator className="h-4 w-4 mr-2" />
                    Calcular
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right Column — Results */}
        <div className="lg:col-span-2 space-y-4">
          {!result && !isCalculating && (
            <Card className="border shadow-none">
              <CardContent className="py-16 text-center">
                <div className="mx-auto h-16 w-16 rounded-full bg-[#e8eddf] flex items-center justify-center mb-4">
                  <Calculator className="h-8 w-8 text-[#738566]" />
                </div>
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Simula tu préstamo
                </h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Ingresa los parámetros a la izquierda y presiona &quot;Calcular&quot; para ver
                  la tabla de amortización y el resumen del préstamo.
                </p>
              </CardContent>
            </Card>
          )}

          {isCalculating && (
            <Card className="border shadow-none">
              <CardContent className="py-16 text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto text-[#738566] mb-4" />
                <p className="text-sm text-muted-foreground">Calculando amortización...</p>
              </CardContent>
            </Card>
          )}

          {result && (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Card className="border shadow-none">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Banknote className="h-4 w-4 text-[#738566]" />
                      <span className="text-xs font-medium text-muted-foreground">Cuota</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">
                      {formatDOP(result.payment_amount)}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {PAYMENT_FREQUENCIES.find(f => f.value === paymentFrequency)?.label}
                    </p>
                  </CardContent>
                </Card>

                <Card className="border shadow-none">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <PiggyBank className="h-4 w-4 text-[#738566]" />
                      <span className="text-xs font-medium text-muted-foreground">Total Préstamo</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">
                      {formatDOP(result.total_loan)}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Capital + Interés
                    </p>
                  </CardContent>
                </Card>

                <Card className="border shadow-none">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="h-4 w-4 text-[#FF7503]" />
                      <span className="text-xs font-medium text-muted-foreground">Total Interés</span>
                    </div>
                    <p className="text-lg font-bold text-[#FF7503]">
                      {formatDOP(result.total_interest)}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {principalAmount && (
                        <>
                          {((parseFloat(result.total_interest) / parseFloat(principalAmount)) * 100).toFixed(1)}% del capital
                        </>
                      )}
                    </p>
                  </CardContent>
                </Card>

                <Card className="border shadow-none">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Receipt className="h-4 w-4 text-[#738566]" />
                      <span className="text-xs font-medium text-muted-foreground">Desembolso</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">
                      {formatDOP(result.total_disbursed)}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Monto a entregar
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Quick Summary */}
              <Card className="border shadow-none bg-[#f0f3ec]">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <Info className="h-4 w-4 text-[#163300] mt-0.5 shrink-0" />
                    <div className="text-sm text-[#163300]">
                      <strong>Resumen:</strong> Préstamo de {formatDOP(principalAmount)} a{' '}
                      {interestRate}% mensual, {term} cuotas{' '}
                      {PAYMENT_FREQUENCIES.find(f => f.value === paymentFrequency)?.label.toLowerCase()}es.
                      Método: {selectedMethod?.label}.
                      {parseFloat(legalFees) > 0 && (
                        <> Gastos legales: {formatDOP(legalFees)} ({legalFeesCondition === 'deducted' ? 'deducidos' : 'financiados'}).</>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Amortization Table */}
              <Card className="border shadow-none">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                      Tabla de Amortización
                    </CardTitle>
                    <span className="text-xs text-muted-foreground">
                      {result.schedule.length} cuotas
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/50">
                          <TableHead className="text-xs font-medium w-12">#</TableHead>
                          <TableHead className="text-xs font-medium">Fecha</TableHead>
                          <TableHead className="text-xs font-medium text-right">Cuota</TableHead>
                          <TableHead className="text-xs font-medium text-right">Capital</TableHead>
                          <TableHead className="text-xs font-medium text-right">Interés</TableHead>
                          <TableHead className="text-xs font-medium text-right">Balance</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {scheduleToShow.map((item, index) => (
                          <TableRow
                            key={item.installment_number}
                            className={index % 2 === 0 ? 'bg-white' : 'bg-muted/30'}
                          >
                            <TableCell className="text-xs text-muted-foreground font-mono">
                              {item.installment_number}
                            </TableCell>
                            <TableCell className="text-xs">
                              {formatDate(item.due_date)}
                            </TableCell>
                            <TableCell className="text-xs text-right font-medium">
                              {formatDOP(item.payment)}
                            </TableCell>
                            <TableCell className="text-xs text-right text-[#163300]">
                              {formatDOP(item.principal)}
                            </TableCell>
                            <TableCell className="text-xs text-right text-[#FF7503]">
                              {formatDOP(item.interest)}
                            </TableCell>
                            <TableCell className="text-xs text-right font-medium">
                              {formatDOP(item.balance)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {/* Show more / less */}
                  {result.schedule.length > 6 && (
                    <div className="border-t px-4 py-3 text-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowAllSchedule(!showAllSchedule)}
                        className="text-xs text-muted-foreground hover:text-foreground"
                      >
                        {showAllSchedule ? (
                          <>
                            <ChevronUp className="h-3 w-3 mr-1" />
                            Mostrar menos
                          </>
                        ) : (
                          <>
                            <ChevronDown className="h-3 w-3 mr-1" />
                            Ver las {result.schedule.length} cuotas
                          </>
                        )}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <Button
                  onClick={handleCreateLoan}
                  className="flex-1 h-11"
                >
                  <ArrowRight className="h-4 w-4 mr-2" />
                  Crear Préstamo con estos Datos
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setResult(null);
                    setShowAllSchedule(false);
                  }}
                  className="h-11"
                >
                  Nueva Simulación
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
