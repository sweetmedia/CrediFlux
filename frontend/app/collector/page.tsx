'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { schedulesAPI, paymentsAPI, collectionsAPI } from '@/lib/api/loans';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  AlertCircle,
  Phone,
  MapPin,
  Clock,
  DollarSign,
  CheckCircle,
  ChevronRight,
  Search,
  Filter,
  Calendar,
  TrendingDown,
  User,
  MessageSquare,
  ArrowUpDown,
  RefreshCw,
  Banknote,
  AlertTriangle,
  CircleDollarSign,
  FileText,
} from 'lucide-react';

// Types for the collector view
interface OverdueItem {
  id: string;
  installment_number: number;
  due_date: string;
  total_amount: number;
  total_amount_currency: string;
  principal_amount: number;
  interest_amount: number;
  late_fee_amount: number;
  balance: number;
  status: string;
  loan: string;
  loan_number?: string;
  customer_name?: string;
  customer_phone?: string;
  customer_address?: string;
  customer_id?: string;
  days_overdue: number;
}

// Helper to calculate days overdue
function getDaysOverdue(dueDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dueDate);
  due.setHours(0, 0, 0, 0);
  const diff = today.getTime() - due.getTime();
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
}

// Urgency level based on days overdue
function getUrgencyLevel(days: number): { label: string; color: string; bgColor: string; borderColor: string } {
  if (days <= 7) return { label: 'Reciente', color: 'text-amber-700', bgColor: 'bg-amber-50', borderColor: 'border-amber-200' };
  if (days <= 30) return { label: 'Urgente', color: 'text-orange-700', bgColor: 'bg-orange-50', borderColor: 'border-orange-200' };
  if (days <= 60) return { label: 'Crítico', color: 'text-red-700', bgColor: 'bg-red-50', borderColor: 'border-red-200' };
  return { label: 'Severo', color: 'text-red-900', bgColor: 'bg-red-100', borderColor: 'border-red-300' };
}

type SortMode = 'days_overdue' | 'amount' | 'name';
type FilterMode = 'all' | 'week' | 'month' | 'critical';

export default function CollectorMobilePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [items, setItems] = useState<OverdueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortMode, setSortMode] = useState<SortMode>('days_overdue');
  const [filterMode, setFilterMode] = useState<FilterMode>('all');
  const [refreshing, setRefreshing] = useState(false);
  const [showQuickPay, setShowQuickPay] = useState<string | null>(null);

  const currencySymbol = config?.currency_symbol || 'RD$';

  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) return `${currencySymbol}0.00`;
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(num)) return `${currencySymbol}0.00`;
    return `${currencySymbol}${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-DO', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Fetch overdue schedules
  const fetchData = async () => {
    try {
      setError('');
      const data = await schedulesAPI.getOverdueSchedules();
      
      // Enrich with calculated fields
      const enriched: OverdueItem[] = (Array.isArray(data) ? data : []).map((schedule: any) => ({
        id: schedule.id,
        installment_number: schedule.installment_number,
        due_date: schedule.due_date,
        total_amount: parseFloat(schedule.total_amount) || 0,
        total_amount_currency: schedule.total_amount_currency || 'DOP',
        principal_amount: parseFloat(schedule.principal_amount) || 0,
        interest_amount: parseFloat(schedule.interest_amount) || 0,
        late_fee_amount: parseFloat(schedule.late_fee_amount) || 0,
        balance: parseFloat(schedule.balance) || parseFloat(schedule.total_amount) || 0,
        status: schedule.status,
        loan: schedule.loan,
        loan_number: schedule.loan_number || schedule.loan_detail?.loan_number || '',
        customer_name: schedule.customer_name || schedule.loan_detail?.customer_name || 'Sin nombre',
        customer_phone: schedule.customer_phone || schedule.loan_detail?.customer_phone || '',
        customer_address: schedule.customer_address || schedule.loan_detail?.customer_address || '',
        customer_id: schedule.customer_id || schedule.loan_detail?.customer_id || '',
        days_overdue: getDaysOverdue(schedule.due_date),
      }));

      setItems(enriched);
    } catch (err: any) {
      setError(err?.message || 'Error cargando datos');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) fetchData();
  }, [isAuthenticated]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  // Filter and sort
  const filteredItems = useMemo(() => {
    let result = [...items];

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(item =>
        (item.customer_name?.toLowerCase() || '').includes(term) ||
        (item.loan_number?.toLowerCase() || '').includes(term) ||
        (item.customer_phone || '').includes(term)
      );
    }

    // Time filter
    switch (filterMode) {
      case 'week':
        result = result.filter(item => item.days_overdue <= 7);
        break;
      case 'month':
        result = result.filter(item => item.days_overdue <= 30);
        break;
      case 'critical':
        result = result.filter(item => item.days_overdue > 30);
        break;
    }

    // Sort
    switch (sortMode) {
      case 'days_overdue':
        result.sort((a, b) => b.days_overdue - a.days_overdue);
        break;
      case 'amount':
        result.sort((a, b) => b.balance - a.balance);
        break;
      case 'name':
        result.sort((a, b) => (a.customer_name || '').localeCompare(b.customer_name || ''));
        break;
    }

    return result;
  }, [items, searchTerm, sortMode, filterMode]);

  // Stats
  const stats = useMemo(() => {
    const totalOverdue = items.reduce((sum, item) => sum + item.balance, 0);
    const clientCount = new Set(items.map(i => i.customer_id || i.customer_name)).size;
    const criticalCount = items.filter(i => i.days_overdue > 30).length;
    return { totalOverdue, clientCount, criticalCount, totalItems: items.length };
  }, [items]);

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#163300] mx-auto" />
          <p className="text-sm text-gray-500 mt-3">Cargando cobros...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Fixed Header */}
      <div className="sticky top-0 z-50 bg-[#163300] text-white shadow-lg">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold">Cobros del Día</h1>
              <p className="text-xs text-green-200">{new Date().toLocaleDateString('es-DO', { weekday: 'long', day: 'numeric', month: 'long' })}</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/10"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* Quick Stats Bar */}
        <div className="flex border-t border-white/20 divide-x divide-white/20">
          <div className="flex-1 px-3 py-2 text-center">
            <div className="text-xs text-green-200">Pendientes</div>
            <div className="text-lg font-bold">{stats.totalItems}</div>
          </div>
          <div className="flex-1 px-3 py-2 text-center">
            <div className="text-xs text-green-200">Clientes</div>
            <div className="text-lg font-bold">{stats.clientCount}</div>
          </div>
          <div className="flex-1 px-3 py-2 text-center">
            <div className="text-xs text-green-200">Monto Total</div>
            <div className="text-sm font-bold">{formatCurrency(stats.totalOverdue)}</div>
          </div>
          <div className="flex-1 px-3 py-2 text-center">
            <div className="text-xs text-green-200">Críticos</div>
            <div className="text-lg font-bold text-[#FFE026]">{stats.criticalCount}</div>
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="sticky top-[118px] z-40 bg-gray-50 px-4 py-3 space-y-2 border-b">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Buscar por nombre, préstamo o teléfono..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 h-10 bg-white"
          />
        </div>

        {/* Filter chips */}
        <div className="flex gap-2 overflow-x-auto">
          {([
            { key: 'all', label: 'Todos' },
            { key: 'week', label: '≤ 7 días' },
            { key: 'month', label: '≤ 30 días' },
            { key: 'critical', label: '30+ días' },
          ] as { key: FilterMode; label: string }[]).map(f => (
            <button
              key={f.key}
              onClick={() => setFilterMode(f.key)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                filterMode === f.key
                  ? 'bg-[#163300] text-white'
                  : 'bg-white text-gray-600 border border-gray-200'
              }`}
            >
              {f.label}
            </button>
          ))}

          <div className="border-l border-gray-300 mx-1" />

          {/* Sort toggle */}
          <button
            onClick={() => {
              const modes: SortMode[] = ['days_overdue', 'amount', 'name'];
              const idx = modes.indexOf(sortMode);
              setSortMode(modes[(idx + 1) % modes.length]);
            }}
            className="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap bg-white text-gray-600 border border-gray-200 flex items-center gap-1"
          >
            <ArrowUpDown className="h-3 w-3" />
            {sortMode === 'days_overdue' ? 'Atraso' : sortMode === 'amount' ? 'Monto' : 'Nombre'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 pt-3">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      )}

      {/* Empty State */}
      {filteredItems.length === 0 && !error && (
        <div className="text-center py-16 px-4">
          <CheckCircle className="h-16 w-16 text-[#163300] mx-auto mb-4 opacity-40" />
          <h3 className="text-lg font-medium text-gray-600">
            {searchTerm || filterMode !== 'all'
              ? 'No hay resultados'
              : '¡Todo al día!'}
          </h3>
          <p className="text-sm text-gray-400 mt-1">
            {searchTerm || filterMode !== 'all'
              ? 'Intenta cambiar los filtros'
              : 'No hay cuotas vencidas por cobrar'}
          </p>
        </div>
      )}

      {/* Collection Items */}
      <div className="px-4 py-3 space-y-3">
        {filteredItems.map((item) => {
          const urgency = getUrgencyLevel(item.days_overdue);
          const isExpanded = showQuickPay === item.id;

          return (
            <Card
              key={item.id}
              className={`overflow-hidden border ${urgency.borderColor} transition-all duration-200`}
            >
              {/* Main card content — tappable */}
              <div
                className="cursor-pointer active:bg-gray-50"
                onClick={() => setShowQuickPay(isExpanded ? null : item.id)}
              >
                <CardContent className="p-4">
                  {/* Top row: Customer name + Amount */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900 truncate">
                          {item.customer_name}
                        </h3>
                        <Badge className={`${urgency.bgColor} ${urgency.color} border-0 text-[10px] px-1.5 py-0`}>
                          {item.days_overdue}d
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Préstamo {item.loan_number} · Cuota {item.installment_number}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0 ml-3">
                      <div className="font-bold text-gray-900">
                        {formatCurrency(item.balance)}
                      </div>
                      <div className="text-[10px] text-gray-400">
                        Vencida {formatDate(item.due_date)}
                      </div>
                    </div>
                  </div>

                  {/* Bottom row: Phone + Address + Arrow */}
                  <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-100">
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      {item.customer_phone && (
                        <span className="flex items-center gap-1">
                          <Phone className="h-3 w-3" />
                          {item.customer_phone}
                        </span>
                      )}
                      {item.customer_address && (
                        <span className="flex items-center gap-1 truncate max-w-[150px]">
                          <MapPin className="h-3 w-3 flex-shrink-0" />
                          {item.customer_address}
                        </span>
                      )}
                    </div>
                    <ChevronRight className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                  </div>
                </CardContent>
              </div>

              {/* Expanded Quick Actions */}
              {isExpanded && (
                <div className="border-t bg-gray-50 p-3">
                  {/* Payment breakdown */}
                  <div className="grid grid-cols-3 gap-2 mb-3 text-center">
                    <div className="bg-white rounded-lg p-2 border">
                      <div className="text-[10px] text-gray-400 uppercase">Capital</div>
                      <div className="text-xs font-semibold">{formatCurrency(item.principal_amount)}</div>
                    </div>
                    <div className="bg-white rounded-lg p-2 border">
                      <div className="text-[10px] text-gray-400 uppercase">Interés</div>
                      <div className="text-xs font-semibold">{formatCurrency(item.interest_amount)}</div>
                    </div>
                    <div className="bg-white rounded-lg p-2 border">
                      <div className="text-[10px] text-gray-400 uppercase">Mora</div>
                      <div className="text-xs font-semibold text-red-600">{formatCurrency(item.late_fee_amount)}</div>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="grid grid-cols-2 gap-2">
                    {/* Call */}
                    {item.customer_phone && (
                      <a
                        href={`tel:${item.customer_phone}`}
                        className="flex items-center justify-center gap-2 bg-white border border-gray-200 rounded-lg py-2.5 px-3 text-sm font-medium text-gray-700 active:bg-gray-100"
                      >
                        <Phone className="h-4 w-4 text-green-600" />
                        Llamar
                      </a>
                    )}

                    {/* WhatsApp */}
                    {item.customer_phone && (
                      <a
                        href={`https://wa.me/${(item.customer_phone || '').replace(/[^0-9]/g, '')}?text=${encodeURIComponent(`Hola ${item.customer_name}, le contactamos referente a su cuota pendiente del préstamo ${item.loan_number} por ${formatCurrency(item.balance)}. ¿Podemos coordinar el pago?`)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-center gap-2 bg-white border border-gray-200 rounded-lg py-2.5 px-3 text-sm font-medium text-gray-700 active:bg-gray-100"
                      >
                        <MessageSquare className="h-4 w-4 text-green-500" />
                        WhatsApp
                      </a>
                    )}

                    {/* Register Payment */}
                    <Link
                      href={`/payments/new?loan=${item.loan}&schedule=${item.id}`}
                      className="flex items-center justify-center gap-2 bg-[#163300] rounded-lg py-2.5 px-3 text-sm font-medium text-white active:bg-[#0d2000] col-span-2"
                    >
                      <Banknote className="h-4 w-4" />
                      Registrar Pago
                    </Link>

                    {/* View Loan */}
                    <Link
                      href={`/loans/${item.loan}`}
                      className="flex items-center justify-center gap-2 bg-white border border-gray-200 rounded-lg py-2.5 px-3 text-sm font-medium text-gray-700 active:bg-gray-100"
                    >
                      <FileText className="h-4 w-4 text-gray-500" />
                      Ver Préstamo
                    </Link>

                    {/* Statement */}
                    {item.customer_id && (
                      <a
                        href={`${process.env.NEXT_PUBLIC_API_URL || ''}/api/loans/customers/${item.customer_id}/statement-preview/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-center gap-2 bg-white border border-gray-200 rounded-lg py-2.5 px-3 text-sm font-medium text-gray-700 active:bg-gray-100"
                      >
                        <CircleDollarSign className="h-4 w-4 text-blue-500" />
                        Estado de Cuenta
                      </a>
                    )}
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {/* Floating Summary Bar */}
      {filteredItems.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg px-4 py-3 z-50">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-gray-500">
                {filteredItems.length} cuota{filteredItems.length !== 1 ? 's' : ''} pendiente{filteredItems.length !== 1 ? 's' : ''}
              </div>
              <div className="text-lg font-bold text-[#163300]">
                {formatCurrency(filteredItems.reduce((sum, i) => sum + i.balance, 0))}
              </div>
            </div>
            <Link
              href="/collections"
              className="px-4 py-2 bg-[#163300] text-white rounded-lg text-sm font-medium"
            >
              Panel Completo
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
