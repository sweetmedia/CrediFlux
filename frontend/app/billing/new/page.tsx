'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { billingAPI } from '@/lib/api/billing';
import { apiClient } from '@/lib/api/client';
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
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  ArrowLeft,
  Plus,
  Trash2,
  Save,
  FileText,
} from 'lucide-react';
import {
  ECF_TYPE_LABELS,
  PAYMENT_METHOD_LABELS,
  ITBIS_RATE_LABELS,
  InvoiceItemCreate,
} from '@/types/billing';
import { Customer } from '@/types';

export default function NewInvoicePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loadingCustomers, setLoadingCustomers] = useState(true);

  // Form state
  const [ecfType, setEcfType] = useState('31');
  const [customerId, setCustomerId] = useState('');
  const [issueDate, setIssueDate] = useState(new Date().toISOString().split('T')[0]);
  const [dueDate, setDueDate] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('04');
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState<InvoiceItemCreate[]>([
    { line_number: 1, description: '', quantity: 1, unit_price: 0, itbis_rate: '18' as any },
  ]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) loadCustomers();
  }, [isAuthenticated]);

  const loadCustomers = async () => {
    try {
      setLoadingCustomers(true);
      const response = await apiClient.get<any>('/api/customers/?page_size=100');
      setCustomers(response.results || []);
    } catch (err) {
      console.error('Error loading customers:', err);
    } finally {
      setLoadingCustomers(false);
    }
  };

  const addItem = () => {
    setItems([
      ...items,
      {
        line_number: items.length + 1,
        description: '',
        quantity: 1,
        unit_price: 0,
        itbis_rate: '18' as any,
      },
    ]);
  };

  const removeItem = (index: number) => {
    if (items.length <= 1) return;
    const newItems = items.filter((_, i) => i !== index).map((item, i) => ({
      ...item,
      line_number: i + 1,
    }));
    setItems(newItems);
  };

  const updateItem = (index: number, field: keyof InvoiceItemCreate, value: any) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
  };

  const calculateItemTotal = (item: InvoiceItemCreate) => {
    const subtotal = item.quantity * item.unit_price;
    const itbisRate = parseInt(item.itbis_rate) / 100;
    const itbis = subtotal * itbisRate;
    return { subtotal, itbis, total: subtotal + itbis };
  };

  const calculateTotals = () => {
    let subtotal = 0;
    let totalItbis = 0;
    items.forEach((item) => {
      const calc = calculateItemTotal(item);
      subtotal += calc.subtotal;
      totalItbis += calc.itbis;
    });
    return { subtotal, totalItbis, total: subtotal + totalItbis };
  };

  const formatCurrency = (amount: number) => {
    return `RD$${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerId) {
      setError('Selecciona un cliente');
      return;
    }
    if (items.some((item) => !item.description || item.unit_price <= 0)) {
      setError('Completa todos los campos de las líneas de detalle');
      return;
    }

    try {
      setIsSubmitting(true);
      setError('');
      const invoice = await billingAPI.createInvoice({
        ecf_type: ecfType as any,
        customer: customerId,
        issue_date: issueDate,
        due_date: dueDate || undefined,
        payment_method: paymentMethod as any,
        notes,
        items: items.map((item) => ({
          ...item,
          unit_price_currency: 'DOP',
        })),
      });
      router.push(`/billing/${invoice.id}`);
    } catch (err: any) {
      const detail = err?.response?.data;
      if (typeof detail === 'object') {
        setError(JSON.stringify(detail));
      } else {
        setError('Error al crear la factura');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const totals = calculateTotals();

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
          Volver a Facturas
        </Link>
        <h1 className="text-2xl font-bold text-slate-900">Nueva Factura Electrónica</h1>
        <p className="text-sm text-slate-600 mt-1">
          Crea un borrador de factura. Luego podrás generar el XML, firmar y enviar a la DGII.
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        {/* General Info */}
        <Card className="mb-6 border-slate-200 shadow-sm">
          <CardHeader className="border-b border-slate-200">
            <CardTitle className="text-base font-semibold text-slate-900">Información General</CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-slate-700">Tipo de e-CF *</Label>
                <Select value={ecfType} onChange={(e) => setEcfType(e.target.value)}>
                  {Object.entries(ECF_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{value} — {label}</option>
                  ))}
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium text-slate-700">Cliente *</Label>
                <Select value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
                  <option value="">Seleccionar cliente...</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.full_name} ({c.id_number})
                    </option>
                  ))}
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium text-slate-700">Fecha de Emisión *</Label>
                <Input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} required />
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium text-slate-700">Fecha de Vencimiento</Label>
                <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium text-slate-700">Forma de Pago *</Label>
                <Select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
                  {Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium text-slate-700">Notas</Label>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Notas internas (opcionales)"
                  rows={2}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Line Items */}
        <Card className="mb-6 border-slate-200 shadow-sm">
          <CardHeader className="border-b border-slate-200">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold text-slate-900">Detalle de Bienes / Servicios</CardTitle>
              <Button type="button" variant="outline" size="sm" onClick={addItem}>
                <Plus className="mr-2 h-4 w-4" />
                Agregar Línea
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {items.map((item, index) => (
                <div key={index} className="grid grid-cols-12 gap-3 items-end">
                  <div className="col-span-4 space-y-1">
                    {index === 0 && <Label className="text-xs text-slate-600">Descripción</Label>}
                    <Input
                      value={item.description}
                      onChange={(e) => updateItem(index, 'description', e.target.value)}
                      placeholder="Descripción del servicio o bien"
                    />
                  </div>
                  <div className="col-span-1 space-y-1">
                    {index === 0 && <Label className="text-xs text-slate-600">Cant.</Label>}
                    <Input
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={item.quantity}
                      onChange={(e) => updateItem(index, 'quantity', parseFloat(e.target.value) || 0)}
                    />
                  </div>
                  <div className="col-span-2 space-y-1">
                    {index === 0 && <Label className="text-xs text-slate-600">Precio Unit.</Label>}
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={item.unit_price}
                      onChange={(e) => updateItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                    />
                  </div>
                  <div className="col-span-2 space-y-1">
                    {index === 0 && <Label className="text-xs text-slate-600">ITBIS</Label>}
                    <Select value={item.itbis_rate} onChange={(e) => updateItem(index, 'itbis_rate', e.target.value)}>
                      {Object.entries(ITBIS_RATE_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </Select>
                  </div>
                  <div className="col-span-2 space-y-1">
                    {index === 0 && <Label className="text-xs text-slate-600">Total</Label>}
                    <div className="h-10 flex items-center px-3 bg-slate-50 border border-slate-200 rounded-md text-sm font-medium text-slate-900">
                      {formatCurrency(calculateItemTotal(item).total)}
                    </div>
                  </div>
                  <div className="col-span-1 space-y-1">
                    {index === 0 && <Label className="text-xs text-transparent">X</Label>}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="w-full text-red-500 hover:text-red-700"
                      onClick={() => removeItem(index)}
                      disabled={items.length <= 1}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            {/* Totals Summary */}
            <div className="mt-6 pt-4 border-t border-slate-200">
              <div className="flex flex-col items-end gap-1">
                <div className="flex items-center justify-between w-64">
                  <span className="text-sm text-slate-600">Subtotal:</span>
                  <span className="text-sm font-medium text-slate-900">{formatCurrency(totals.subtotal)}</span>
                </div>
                <div className="flex items-center justify-between w-64">
                  <span className="text-sm text-slate-600">ITBIS:</span>
                  <span className="text-sm font-medium text-slate-900">{formatCurrency(totals.totalItbis)}</span>
                </div>
                <div className="flex items-center justify-between w-64 pt-2 border-t border-slate-300">
                  <span className="text-base font-bold text-slate-900">Total:</span>
                  <span className="text-lg font-bold text-blue-600">{formatCurrency(totals.total)}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex items-center justify-end gap-3">
          <Link href="/billing">
            <Button type="button" variant="outline">Cancelar</Button>
          </Link>
          <Button type="submit" className="bg-blue-600 hover:bg-blue-700" disabled={isSubmitting}>
            {isSubmitting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Crear Factura (Borrador)
          </Button>
        </div>
      </form>
    </div>
  );
}
