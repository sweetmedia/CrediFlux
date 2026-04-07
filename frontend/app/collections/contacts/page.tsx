'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { collectionsAPI } from '@/lib/api/loans';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Loader2,
  ArrowLeft,
  Phone,
  Bell,
  ShieldAlert,
  CalendarClock,
  XCircle,
  Plus,
  ArrowRight,
  MessageSquare,
  Mail,
  MapPin,
  Building2,
  Users,
  Filter,
  CheckCircle2,
  Clock3,
} from 'lucide-react';
import type { CollectionContact } from '@/types';

const CONTACT_TYPE_LABELS: Record<string, string> = {
  all: 'Todos',
  phone_call: 'Llamada',
  sms: 'SMS',
  whatsapp: 'WhatsApp',
  email: 'Email',
  home_visit: 'Visita a domicilio',
  office_visit: 'Visita al negocio',
  meeting: 'Reunión',
};

const OUTCOME_LABELS: Record<string, string> = {
  all: 'Todos',
  answered: 'Respondió',
  no_answer: 'Sin respuesta',
  wrong_number: 'Número incorrecto',
  promise_to_pay: 'Promesa de pago',
  payment_plan: 'Plan de pago',
  partial_payment: 'Pago parcial',
  full_payment: 'Pago total',
  dispute: 'Disputa',
  hardship: 'Dificultad',
  refused_to_pay: 'Se negó a pagar',
  not_reachable: 'No localizable',
};

export default function CollectionContactsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [contacts, setContacts] = useState<CollectionContact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [contactType, setContactType] = useState('all');
  const [outcome, setOutcome] = useState('all');
  const [escalationFilter, setEscalationFilter] = useState('all');
  const [stats, setStats] = useState({
    requiringEscalation: 0,
    promisesDueToday: 0,
    brokenPromises: 0,
  });

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated, currentPage, contactType, outcome, escalationFilter]);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: Record<string, string | number | boolean> = {
        page: currentPage,
      };

      if (contactType !== 'all') params.contact_type = contactType;
      if (outcome !== 'all') params.outcome = outcome;
      if (escalationFilter === 'yes') params.requires_escalation = true;
      if (escalationFilter === 'no') params.requires_escalation = false;

      const [contactsResponse, escalationResponse, promisesResponse, brokenPromisesResponse] = await Promise.all([
        collectionsAPI.getContacts(params),
        collectionsAPI.getRequiringEscalation(),
        collectionsAPI.getPromisesDueToday(),
        collectionsAPI.getBrokenPromises(),
      ]);

      setContacts(contactsResponse.results || []);
      setTotalCount(contactsResponse.count || 0);
      setStats({
        requiringEscalation: escalationResponse.length,
        promisesDueToday: promisesResponse.length,
        brokenPromises: brokenPromisesResponse.length,
      });
    } catch (err: any) {
      console.error('Error loading collection contacts:', err);
      setError('Error al cargar la bitácora de contactos');
    } finally {
      setIsLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / 25));

  const contactSummary = useMemo(() => {
    const withPromise = contacts.filter((contact) =>
      ['promise_to_pay', 'payment_plan'].includes(contact.outcome)
    ).length;
    const escalated = contacts.filter((contact) => contact.requires_escalation).length;
    return {
      visible: contacts.length,
      withPromise,
      escalated,
    };
  }, [contacts]);

  const formatDateTime = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('es-DO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (amount?: number) => {
    const value = Number(amount || 0);
    return new Intl.NumberFormat('es-DO', {
      style: 'currency',
      currency: 'DOP',
    }).format(value);
  };

  const getContactIcon = (type: string) => {
    switch (type) {
      case 'phone_call':
        return <Phone className="h-4 w-4 text-[#163300]" />;
      case 'whatsapp':
      case 'sms':
        return <MessageSquare className="h-4 w-4 text-green-600" />;
      case 'email':
        return <Mail className="h-4 w-4 text-[#738566]" />;
      case 'home_visit':
        return <MapPin className="h-4 w-4 text-orange-600" />;
      case 'office_visit':
      case 'meeting':
        return <Building2 className="h-4 w-4 text-slate-600" />;
      default:
        return <Phone className="h-4 w-4 text-slate-500" />;
    }
  };

  const getOutcomeTone = (contact: CollectionContact) => {
    if (contact.requires_escalation) return 'bg-red-50 text-red-700 border-red-200';
    if (contact.promise_kept === true) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (contact.promise_kept === false) return 'bg-orange-50 text-orange-700 border-orange-200';
    if (['promise_to_pay', 'payment_plan'].includes(contact.outcome)) {
      return 'bg-blue-50 text-blue-700 border-blue-200';
    }
    return 'bg-slate-50 text-slate-700 border-slate-200';
  };

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f6f8f7]">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] px-4 py-6 md:px-6 md:py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <Link
            href="/collections"
            className="mb-3 inline-flex items-center text-sm text-slate-500 transition-colors hover:text-slate-900"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Volver a Collections
          </Link>

          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
                <Phone className="h-3.5 w-3.5" />
                Bitácora de gestión de cobro
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Contactos de cobranza</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">
                Aquí ves el historial operativo de llamadas, mensajes, visitas y compromisos registrados en la gestión de cobros.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" className="bg-white" onClick={() => router.push('/collections')}>
                <Bell className="mr-2 h-4 w-4" />
                Dashboard
              </Button>
              <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/collections/contacts/new')}>
                <Plus className="mr-2 h-4 w-4" />
                Nuevo contacto
              </Button>
            </div>
          </div>
        </div>

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-sm text-white/70">Actividad visible en la bandeja</p>
                  <h2 className="mt-1 text-3xl font-semibold">{totalCount} contacto(s)</h2>
                  <p className="mt-3 max-w-2xl text-sm text-white/80">
                    Esta vista debe ayudarte a leer la calidad del seguimiento: promesas, casos escalados, incumplimientos y próximos pasos.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[440px] xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Escalación</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.requiringEscalation}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Promesas hoy</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.promisesDueToday}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Incumplidas</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.brokenPromises}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Con promesa</p>
                    <p className="mt-2 text-2xl font-semibold">{contactSummary.withPromise}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Registros visibles</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{contactSummary.visible} en esta página</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Promesas activas</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{contactSummary.withPromise} contacto(s)</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Escalados visibles</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{contactSummary.escalated} caso(s)</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Página</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{currentPage} de {totalPages}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid gap-6 xl:grid-cols-[0.84fr_1.16fr]">
          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base text-[#163300]">
                  <Filter className="h-4 w-4" />
                  Filtros
                </CardTitle>
                <CardDescription>Recorta la bitácora por canal, resultado o nivel de escalación.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Tipo de contacto</label>
                  <Select value={contactType} onValueChange={(value) => { setCurrentPage(1); setContactType(value); }}>
                    <SelectTrigger className="bg-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(CONTACT_TYPE_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Resultado</label>
                  <Select value={outcome} onValueChange={(value) => { setCurrentPage(1); setOutcome(value); }}>
                    <SelectTrigger className="bg-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(OUTCOME_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Escalación</label>
                  <Select value={escalationFilter} onValueChange={(value) => { setCurrentPage(1); setEscalationFilter(value); }}>
                    <SelectTrigger className="bg-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      <SelectItem value="yes">Requiere escalación</SelectItem>
                      <SelectItem value="no">Sin escalación</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Lectura operativa</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-slate-700">
                <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4">
                  <ShieldAlert className="mt-0.5 h-4 w-4 text-red-600" />
                  <p>Los casos escalados merecen seguimiento supervisor o una acción distinta al contacto rutinario.</p>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4">
                  <CalendarClock className="mt-0.5 h-4 w-4 text-blue-600" />
                  <p>Las promesas de pago son útiles solo si luego se verifican; si no, el historial se vuelve decorativo.</p>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-orange-200 bg-orange-50 p-4">
                  <XCircle className="mt-0.5 h-4 w-4 text-orange-600" />
                  <p>Promesas incumplidas y falta de respuesta deberían empujar acciones más fuertes o cambio de canal.</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle className="text-base text-[#163300]">Bitácora de contactos</CardTitle>
                  <CardDescription>Historial de interacciones registradas por el equipo de cobranza.</CardDescription>
                </div>
                <Button variant="outline" size="sm" className="bg-white" onClick={() => router.push('/collections/contacts/new')}>
                  <Plus className="mr-2 h-4 w-4" />
                  Nuevo
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {contacts.length === 0 ? (
                <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
                  <Users className="mb-4 h-12 w-12 text-slate-400" />
                  <h3 className="text-lg font-medium text-slate-900">No hay contactos registrados</h3>
                  <p className="mt-2 mb-4 max-w-md text-sm text-slate-500">
                    Crea el primer contacto para empezar a construir el historial de gestión.
                  </p>
                  <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/collections/contacts/new')}>
                    <Plus className="mr-2 h-4 w-4" />
                    Registrar contacto
                  </Button>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-slate-50/70">
                          <TableHead>Cliente / préstamo</TableHead>
                          <TableHead>Canal</TableHead>
                          <TableHead>Resultado</TableHead>
                          <TableHead>Promesa</TableHead>
                          <TableHead>Fecha</TableHead>
                          <TableHead className="text-right">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {contacts.map((contact) => (
                          <TableRow key={contact.id} className="hover:bg-slate-50">
                            <TableCell className="min-w-[250px] align-top">
                              <div className="space-y-1">
                                <p className="font-medium text-slate-900">{contact.customer_name}</p>
                                <p className="text-sm text-slate-500">{contact.loan_number}</p>
                                {contact.contacted_by_name && (
                                  <p className="text-xs text-slate-400">Registrado por {contact.contacted_by_name}</p>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="flex items-center gap-2 text-sm text-slate-700">
                                {getContactIcon(contact.contact_type)}
                                {contact.contact_type_display}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="space-y-2">
                                <Badge variant="outline" className={getOutcomeTone(contact)}>
                                  {contact.outcome_display}
                                </Badge>
                                {contact.requires_escalation && (
                                  <div className="text-xs font-medium text-red-600">Escalado</div>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              {contact.promise_date ? (
                                <div className="space-y-1 text-sm">
                                  <p className="text-slate-900">{formatDateTime(contact.promise_date)}</p>
                                  <p className="font-medium text-slate-700">{formatCurrency(contact.promise_amount)}</p>
                                  {contact.promise_kept === true && <p className="text-emerald-600">Cumplida</p>}
                                  {contact.promise_kept === false && <p className="text-orange-600">Incumplida</p>}
                                  {contact.promise_kept == null && <p className="text-slate-500">Pendiente</p>}
                                </div>
                              ) : (
                                <span className="text-sm text-slate-400">-</span>
                              )}
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="flex items-center gap-2 text-sm text-slate-700">
                                <Clock3 className="h-4 w-4 text-slate-400" />
                                {formatDateTime(contact.contact_date)}
                              </div>
                            </TableCell>
                            <TableCell className="text-right align-top">
                              <div className="flex justify-end">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="bg-white"
                                  onClick={() => router.push(`/loans/${contact.loan}`)}
                                >
                                  Ver préstamo
                                  <ArrowRight className="ml-2 h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
                    <p className="text-sm text-slate-600">Página {currentPage} de {totalPages}</p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="bg-white"
                        disabled={currentPage === 1}
                        onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                      >
                        Anterior
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="bg-white"
                        disabled={currentPage >= totalPages}
                        onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                      >
                        Siguiente
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
