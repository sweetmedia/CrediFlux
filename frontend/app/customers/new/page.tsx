'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { customersAPI } from '@/lib/api/customers';
import { contactsAPI } from '@/lib/api/contacts';
import { rncAPI, RNCData } from '@/lib/api/rnc';
import { cedulaAPI } from '@/lib/api/cedula';
import { validateDominicanID } from '@/lib/utils/rd-validation';
import { formatIDNumber, cleanIDNumber, getIDPlaceholder } from '@/lib/utils/id-formatter';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { NativeSelect as Select } from '@/components/ui/native-select';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ArrowLeft, Loader2, Save, UserPlus, Search,
  CheckCircle, AlertCircle, Info, Plus, X, Phone, Mail, Star,
} from 'lucide-react';

/* --- Types for dynamic contact fields --- */
interface PhoneEntry {
  phone: string;
  phone_type: 'mobile' | 'home' | 'work' | 'landline' | 'whatsapp' | 'other';
  is_primary: boolean;
  is_whatsapp: boolean;
}

interface EmailEntry {
  email: string;
  email_type: 'personal' | 'work' | 'business' | 'other';
  is_primary: boolean;
}

/* --- Zod schema (core customer fields) --- */
const customerSchema = z.object({
  first_name: z.string().min(2, 'Nombre requerido'),
  last_name: z.string().min(2, 'Apellido requerido'),
  date_of_birth: z.string().min(1, 'Fecha de nacimiento requerida'),
  gender: z.enum(['M', 'F', 'O']).optional(),
  email: z.string().optional(),
  phone: z.string().optional(),
  id_type: z.string().min(1, 'Tipo de identificación requerido'),
  id_number: z.string().min(5, 'Número de identificación requerido'),
  address_line1: z.string().min(5, 'Dirección requerida'),
  address_line2: z.string().optional(),
  city: z.string().min(2, 'Ciudad requerida'),
  state: z.string().min(2, 'Estado/Provincia requerido'),
  postal_code: z.string().min(2, 'Código postal requerido'),
  country: z.string().min(2, 'País requerido'),
  employment_status: z.string().optional(),
  employer_name: z.string().optional(),
  occupation: z.string().optional(),
  employment_start_date: z.string().optional(),
  monthly_income: z.string().optional(),
  notes: z.string().optional(),
});

type CustomerFormData = z.infer<typeof customerSchema>;

/* --- Constants --- */
const PHONE_TYPES = [
  { value: 'mobile', label: 'Celular' },
  { value: 'home', label: 'Casa' },
  { value: 'work', label: 'Oficina' },
  { value: 'landline', label: 'Fijo' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'other', label: 'Otro' },
] as const;

const EMAIL_TYPES = [
  { value: 'personal', label: 'Personal' },
  { value: 'work', label: 'Trabajo' },
  { value: 'business', label: 'Empresa' },
  { value: 'other', label: 'Otro' },
] as const;

const MAX_PHONES = 5;
const MAX_EMAILS = 3;

export default function NewCustomerPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  /* --- RNC validation states --- */
  const [rncData, setRncData] = useState<RNCData | null>(null);
  const [isValidatingRnc, setIsValidatingRnc] = useState(false);
  const [rncValidationMessage, setRncValidationMessage] = useState<string>('');
  const [rncValidationStatus, setRncValidationStatus] = useState<'success' | 'warning' | 'error' | null>(null);

  const [idFormatValidation, setIdFormatValidation] = useState<{
    valid: boolean;
    warning?: boolean;
    message: string;
  } | null>(null);

  const [formattedIdNumber, setFormattedIdNumber] = useState<string>('');

  /* --- Dynamic contact arrays --- */
  const [phones, setPhones] = useState<PhoneEntry[]>([
    { phone: '+1', phone_type: 'mobile', is_primary: true, is_whatsapp: false },
  ]);
  const [emails, setEmails] = useState<EmailEntry[]>([
    { email: '', email_type: 'personal', is_primary: true },
  ]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CustomerFormData>({
    resolver: zodResolver(customerSchema),
    defaultValues: {
      country: 'Dominican Republic',
    },
  });

  const idNumber = watch('id_number');
  const idType = watch('id_type');

  /* --- RNC/Cédula validation --- */
  const validateRncNumber = async (rnc: string) => {
    if (!rnc || rnc.length < 9) {
      setRncData(null);
      setRncValidationMessage('');
      setRncValidationStatus(null);
      return;
    }

    try {
      setIsValidatingRnc(true);
      setRncValidationStatus(null);

      // For cédulas: try JCE Padrón first (better personal data)
      if (idType === 'cedula') {
        setRncValidationMessage('Buscando en Padrón JCE...');
        try {
          const jceResult = await cedulaAPI.validate(rnc);
          if (jceResult.found) {
            // Auto-populate from JCE
            if (jceResult.first_name) setValue('first_name', jceResult.first_name);
            if (jceResult.middle_name) {
              // If middle name exists, combine with first name or set separately
              const currentFirst = jceResult.first_name || '';
              if (jceResult.middle_name) {
                setValue('first_name', `${currentFirst} ${jceResult.middle_name}`.trim());
              }
            }
            if (jceResult.apellido1) {
              const fullLast = jceResult.apellido2
                ? `${jceResult.apellido1} ${jceResult.apellido2}`
                : jceResult.apellido1;
              setValue('last_name', fullLast);
            }
            if (jceResult.fecha_nacimiento) {
              setValue('date_of_birth', jceResult.fecha_nacimiento);
            }

            setRncValidationMessage(`[OK] Encontrado: ${jceResult.nombre_completo}`);
            setRncValidationStatus('success');
            return;
          }
        } catch (jceErr) {
          console.log('JCE lookup failed, falling back to DGII:', jceErr);
        }
      }

      // Fallback: DGII lookup (for RNC or if JCE didn't find it)
      if (idType === 'cedula' || idType === 'rnc') {
        setRncValidationMessage('Buscando en DGII...');
        const result = await rncAPI.validateRNC(rnc);

        if (result.exists && result.data) {
          setRncData(result.data);
          const fullName = result.data.razon_social.trim();
          const nameParts = fullName.split(' ');
          if (nameParts.length >= 2) {
            setValue('first_name', nameParts[0]);
            setValue('last_name', nameParts.slice(1).join(' '));
          } else {
            setValue('first_name', fullName);
          }

          if (result.is_active) {
            setRncValidationMessage(`[OK] Encontrado en DGII: ${result.data.razon_social}`);
            setRncValidationStatus('success');
          } else {
            setRncValidationMessage(`[!] Encontrado pero SUSPENDIDO: ${result.data.razon_social}`);
            setRncValidationStatus('warning');
          }
        } else {
          setRncData(null);
          setRncValidationMessage('No encontrado. Puede continuar manualmente.');
          setRncValidationStatus('warning');
        }
      }
    } catch (err: any) {
      console.error('Error validating:', err);
      setRncData(null);
      setRncValidationMessage('No se pudo validar. Puede continuar sin validación.');
      setRncValidationStatus('warning');
    } finally {
      setIsValidatingRnc(false);
    }
  };

  const handleRncBlur = () => {
    validateRncNumber(idNumber || '');
  };

  const handleIdNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    if (!idType) {
      setFormattedIdNumber(inputValue);
      setValue('id_number', inputValue);
      return;
    }
    const formatted = formatIDNumber(inputValue, idType as any);
    setFormattedIdNumber(formatted);
    setValue('id_number', cleanIDNumber(formatted));
  };

  useEffect(() => {
    if (idNumber && idType) {
      setFormattedIdNumber(formatIDNumber(idNumber, idType as any));
    } else if (!idNumber) {
      setFormattedIdNumber('');
    }
  }, [idType]);

  useEffect(() => {
    if (!idNumber || !idType || idNumber.length < 3) {
      setIdFormatValidation(null);
      return;
    }
    const r = validateDominicanID(idNumber, idType as any);
    setIdFormatValidation({ valid: r.valid, warning: r.warning, message: r.message });
  }, [idNumber, idType]);

  /* --- Phone helpers --- */
  const addPhone = () => {
    if (phones.length >= MAX_PHONES) return;
    setPhones(prev => [...prev, { phone: '+1', phone_type: 'mobile', is_primary: false, is_whatsapp: false }]);
  };

  const removePhone = (idx: number) => {
    if (phones.length <= 1) return;
    setPhones(prev => {
      const next = prev.filter((_, i) => i !== idx);
      if (prev[idx].is_primary && next.length > 0) next[0].is_primary = true;
      return next;
    });
  };

  const updatePhone = (idx: number, field: keyof PhoneEntry, value: any) => {
    setPhones(prev => {
      const next = prev.map((p, i) => ({ ...p }));
      if (field === 'is_primary' && value === true) {
        next.forEach((p, i) => { p.is_primary = i === idx; });
      } else {
        (next[idx] as any)[field] = value;
      }
      return next;
    });
  };

  /* --- Email helpers --- */
  const addEmail = () => {
    if (emails.length >= MAX_EMAILS) return;
    setEmails(prev => [...prev, { email: '', email_type: 'personal', is_primary: false }]);
  };

  const removeEmail = (idx: number) => {
    if (emails.length <= 1) return;
    setEmails(prev => {
      const next = prev.filter((_, i) => i !== idx);
      if (prev[idx].is_primary && next.length > 0) next[0].is_primary = true;
      return next;
    });
  };

  const updateEmail = (idx: number, field: keyof EmailEntry, value: any) => {
    setEmails(prev => {
      const next = prev.map((e, i) => ({ ...e }));
      if (field === 'is_primary' && value === true) {
        next.forEach((e, i) => { e.is_primary = i === idx; });
      } else {
        (next[idx] as any)[field] = value;
      }
      return next;
    });
  };

  /* --- Form submit --- */
  const onSubmit = async (data: CustomerFormData) => {
    try {
      setIsLoading(true);
      setError('');

      const validPhones = phones.filter(p => p.phone && p.phone.length > 3);
      const validEmails = emails.filter(e => e.email && e.email.includes('@'));

      if (validPhones.length === 0) {
        setError('Debe agregar al menos un número de teléfono válido.');
        setIsLoading(false);
        return;
      }
      if (validEmails.length === 0) {
        setError('Debe agregar al menos un email válido.');
        setIsLoading(false);
        return;
      }

      const primaryPhone = validPhones.find(p => p.is_primary) || validPhones[0];
      const primaryEmail = validEmails.find(e => e.is_primary) || validEmails[0];

      const submitData = {
        ...data,
        phone: primaryPhone.phone,
        email: primaryEmail.email,
        monthly_income: data.monthly_income ? parseFloat(data.monthly_income) : undefined,
      };

      const customer = await customersAPI.createCustomer(submitData);
      const customerId = (customer as any).id;

      // Create all contact entries in parallel
      await Promise.all([
        ...validPhones.map(p =>
          contactsAPI.createPhone({
            customer: customerId,
            phone: p.phone,
            phone_type: p.phone_type,
            is_primary: p.is_primary,
            is_whatsapp: p.is_whatsapp || p.phone_type === 'whatsapp',
          })
        ),
        ...validEmails.map(e =>
          contactsAPI.createEmail({
            customer: customerId,
            email: e.email,
            email_type: e.email_type,
            is_primary: e.is_primary,
          })
        ),
      ]);

      router.push('/customers');
    } catch (err: any) {
      if (err.response?.data) {
        const errorData = err.response.data;
        const fieldErrors: string[] = [];
        const labels: Record<string, string> = {
          id_number: 'RNC/Cédula', email: 'Email', phone: 'Teléfono',
          date_of_birth: 'Fecha nacimiento', address_line1: 'Dirección',
          first_name: 'Nombre', last_name: 'Apellido', monthly_income: 'Ingreso mensual',
        };
        for (const [key, value] of Object.entries(errorData)) {
          if (Array.isArray(value)) {
            fieldErrors.push(`${labels[key] || key}: ${(value as string[])[0]}`);
          }
        }
        if (fieldErrors.length > 0) setError(fieldErrors.join(' | '));
        else if (errorData.detail) setError(errorData.detail);
        else if (errorData.non_field_errors) setError(errorData.non_field_errors[0]);
        else setError('Error al crear el cliente. Verifique los datos.');
      } else {
        setError('Error al conectar con el servidor');
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  /* ===========================================================
     RENDER
     =========================================================== */
  return (
    <div className="min-h-screen bg-background">
      <div className="p-6 lg:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Nuevo Cliente</h1>
            <p className="text-sm text-gray-500 mt-1">
              Registra un nuevo cliente en el sistema
            </p>
          </div>
          <Link href="/customers">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver
            </Button>
          </Link>
        </div>
        
        <div className="max-w-4xl mx-auto">

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-6">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* === 1. IDENTIFICACIÓN (cédula-first) === */}
            <Card className="border-[#163300]/20">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5 text-[#163300]" />
                  Identificación
                </CardTitle>
                <CardDescription>
                  Ingrese la cédula o RNC — se buscará automáticamente en el Padrón JCE y DGII
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="id_type">
                      Tipo de ID <span className="text-red-500">*</span>
                    </Label>
                    <Select id="id_type" {...register('id_type')} disabled={isLoading}>
                      <option value="">Seleccionar...</option>
                      <option value="cedula">Cédula (11 dígitos)</option>
                      <option value="rnc">RNC (9 dígitos)</option>
                      <option value="passport">Pasaporte</option>
                    </Select>
                    {errors.id_type && (
                      <p className="text-sm text-red-500">{errors.id_type.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="id_number">
                      Número de ID <span className="text-red-500">*</span>
                    </Label>
                    <div className="relative">
                      <Input
                        id="id_number"
                        placeholder={idType ? getIDPlaceholder(idType as any) : '000-0000000-0'}
                        value={formattedIdNumber}
                        onChange={handleIdNumberChange}
                        onBlur={handleRncBlur}
                        disabled={isLoading}
                        className="pr-10"
                      />
                      {isValidatingRnc && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2">
                          <Loader2 className="h-4 w-4 animate-spin text-[#163300]" />
                        </div>
                      )}
                    </div>
                    {errors.id_number && (
                      <p className="text-sm text-red-500">{errors.id_number.message}</p>
                    )}

                    {idFormatValidation && (
                      <div className={`flex items-start gap-2 p-2 rounded-md text-xs ${
                        !idFormatValidation.valid
                          ? 'bg-red-50 text-red-700 border border-red-200'
                          : idFormatValidation.warning
                          ? 'bg-yellow-50 text-yellow-700 border border-yellow-200'
                          : 'bg-green-50 text-green-700 border border-green-200'
                      }`}>
                        {!idFormatValidation.valid ? (
                          <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                        ) : idFormatValidation.warning ? (
                          <Info className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                        ) : (
                          <CheckCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                        )}
                        <p>{idFormatValidation.message}</p>
                      </div>
                    )}

                    {rncValidationMessage && (
                      <div className={`flex items-start gap-2 p-3 rounded-md text-sm ${
                        rncValidationStatus === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
                        rncValidationStatus === 'warning' ? 'bg-yellow-50 text-yellow-800 border border-yellow-200' :
                        'bg-red-50 text-red-800 border border-red-200'
                      }`}>
                        {rncValidationStatus === 'success' && <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />}
                        {rncValidationStatus === 'warning' && <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />}
                        {rncValidationStatus === 'error' && <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />}
                        <div className="flex-1">
                          <p className="font-medium">{rncValidationMessage}</p>
                          {rncData && (
                            <div className="mt-2 space-y-1 text-xs">
                              <p><strong>Actividad:</strong> {rncData.actividad_economica}</p>
                              {rncData.fecha_inicio && (
                                <p><strong>Fecha Inicio:</strong> {rncData.fecha_inicio}</p>
                              )}
                              <p><strong>Estado:</strong> {rncData.estado}</p>
                              <p><strong>Régimen:</strong> {rncData.regimen_pago}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* === 2. DATOS PERSONALES === */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Datos Personales</CardTitle>
                <CardDescription>
                  {rncData ? 'Datos auto-completados — puede editarlos' : 'Información personal del cliente'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">
                      Nombre <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="first_name"
                      placeholder="Juan"
                      {...register('first_name')}
                      disabled={isLoading}
                    />
                    {errors.first_name && (
                      <p className="text-sm text-red-500">{errors.first_name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">
                      Apellido <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="last_name"
                      placeholder="Pérez"
                      {...register('last_name')}
                      disabled={isLoading}
                    />
                    {errors.last_name && (
                      <p className="text-sm text-red-500">{errors.last_name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="date_of_birth">
                      Fecha de Nacimiento <span className="text-red-500">*</span>
                    </Label>
                    <Input id="date_of_birth" type="date" {...register('date_of_birth')} disabled={isLoading} />
                    {errors.date_of_birth && (
                      <p className="text-sm text-red-500">{errors.date_of_birth.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="gender">Género</Label>
                    <Select id="gender" {...register('gender')} disabled={isLoading}>
                      <option value="">Seleccionar...</option>
                      <option value="M">Masculino</option>
                      <option value="F">Femenino</option>
                      <option value="O">Otro</option>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* === 3. CONTACTO — Multi-phone & multi-email === */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2">
                  <Phone className="h-5 w-5 text-[#738566]" />
                  Información de Contacto
                </CardTitle>
                <CardDescription>
                  Teléfonos y emails del cliente — puede agregar múltiples
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">

                {/* -- Phone Numbers -- */}
                <div className="space-y-3">
                  <Label className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                    <Phone className="h-3.5 w-3.5" />
                    Teléfonos <span className="text-red-500">*</span>
                  </Label>
                  <div className="space-y-2">
                    {phones.map((phone, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 p-2.5 rounded-lg border border-gray-200 bg-white hover:border-gray-300 transition-colors"
                      >
                        <button
                          type="button"
                          onClick={() => updatePhone(idx, 'is_primary', true)}
                          className={`flex-shrink-0 p-1 rounded transition-colors ${
                            phone.is_primary ? 'text-[#FFE026]' : 'text-gray-300 hover:text-gray-400'
                          }`}
                          title={phone.is_primary ? 'Teléfono principal' : 'Marcar como principal'}
                        >
                          <Star className="h-4 w-4" fill={phone.is_primary ? 'currentColor' : 'none'} />
                        </button>

                        <Input
                          value={phone.phone}
                          onChange={(e) => updatePhone(idx, 'phone', e.target.value)}
                          placeholder="+1 (809) 555-1234"
                          disabled={isLoading}
                          className="flex-1 h-9 text-sm"
                        />

                        <select
                          value={phone.phone_type}
                          onChange={(e) => updatePhone(idx, 'phone_type', e.target.value)}
                          disabled={isLoading}
                          className="h-9 px-2 text-xs rounded-md border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                        >
                          {PHONE_TYPES.map(t => (
                            <option key={t.value} value={t.value}>{t.label}</option>
                          ))}
                        </select>

                        <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer flex-shrink-0" title="¿Tiene WhatsApp?">
                          <input
                            type="checkbox"
                            checked={phone.is_whatsapp || phone.phone_type === 'whatsapp'}
                            onChange={(e) => updatePhone(idx, 'is_whatsapp', e.target.checked)}
                            disabled={isLoading}
                            className="h-3.5 w-3.5 rounded border-gray-300 text-green-600 focus:ring-green-500"
                          />
                          <span className="hidden sm:inline">WA</span>
                        </label>

                        <button
                          type="button"
                          onClick={() => removePhone(idx)}
                          disabled={phones.length <= 1 || isLoading}
                          className="flex-shrink-0 p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                          title="Eliminar"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>

                  {phones.length < MAX_PHONES && (
                    <button
                      type="button"
                      onClick={addPhone}
                      disabled={isLoading}
                      className="flex items-center gap-1.5 text-xs text-[#163300] hover:text-[#163300]/80 font-medium py-1.5 px-3 rounded-md border border-dashed border-[#163300]/30 hover:border-[#163300]/50 hover:bg-[#163300]/5 transition-colors"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Agregar teléfono
                    </button>
                  )}
                </div>

                {/* -- Divider -- */}
                <div className="border-t border-gray-100" />

                {/* -- Email Addresses -- */}
                <div className="space-y-3">
                  <Label className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                    <Mail className="h-3.5 w-3.5" />
                    Emails <span className="text-red-500">*</span>
                  </Label>
                  <div className="space-y-2">
                    {emails.map((email, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 p-2.5 rounded-lg border border-gray-200 bg-white hover:border-gray-300 transition-colors"
                      >
                        <button
                          type="button"
                          onClick={() => updateEmail(idx, 'is_primary', true)}
                          className={`flex-shrink-0 p-1 rounded transition-colors ${
                            email.is_primary ? 'text-[#FFE026]' : 'text-gray-300 hover:text-gray-400'
                          }`}
                          title={email.is_primary ? 'Email principal' : 'Marcar como principal'}
                        >
                          <Star className="h-4 w-4" fill={email.is_primary ? 'currentColor' : 'none'} />
                        </button>

                        <Input
                          value={email.email}
                          onChange={(e) => updateEmail(idx, 'email', e.target.value)}
                          placeholder="cliente@ejemplo.com"
                          type="email"
                          disabled={isLoading}
                          className="flex-1 h-9 text-sm"
                        />

                        <select
                          value={email.email_type}
                          onChange={(e) => updateEmail(idx, 'email_type', e.target.value)}
                          disabled={isLoading}
                          className="h-9 px-2 text-xs rounded-md border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                        >
                          {EMAIL_TYPES.map(t => (
                            <option key={t.value} value={t.value}>{t.label}</option>
                          ))}
                        </select>

                        <button
                          type="button"
                          onClick={() => removeEmail(idx)}
                          disabled={emails.length <= 1 || isLoading}
                          className="flex-shrink-0 p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                          title="Eliminar"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>

                  {emails.length < MAX_EMAILS && (
                    <button
                      type="button"
                      onClick={addEmail}
                      disabled={isLoading}
                      className="flex items-center gap-1.5 text-xs text-[#163300] hover:text-[#163300]/80 font-medium py-1.5 px-3 rounded-md border border-dashed border-[#163300]/30 hover:border-[#163300]/50 hover:bg-[#163300]/5 transition-colors"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Agregar email
                    </button>
                  )}
                </div>

              </CardContent>
            </Card>

            {/* === 4. DIRECCIÓN === */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Dirección</CardTitle>
                <CardDescription>Domicilio del cliente</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="address_line1">
                    Dirección Línea 1 <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="address_line1"
                    placeholder="Calle Principal #123"
                    {...register('address_line1')}
                    disabled={isLoading}
                  />
                  {errors.address_line1 && (
                    <p className="text-sm text-red-500">{errors.address_line1.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="address_line2">Dirección Línea 2</Label>
                  <Input
                    id="address_line2"
                    placeholder="Apto/Suite (opcional)"
                    {...register('address_line2')}
                    disabled={isLoading}
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="city">Ciudad <span className="text-red-500">*</span></Label>
                    <Input id="city" placeholder="Santo Domingo" {...register('city')} disabled={isLoading} />
                    {errors.city && <p className="text-sm text-red-500">{errors.city.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="state">Estado/Provincia <span className="text-red-500">*</span></Label>
                    <Input id="state" placeholder="Distrito Nacional" {...register('state')} disabled={isLoading} />
                    {errors.state && <p className="text-sm text-red-500">{errors.state.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="postal_code">Código Postal <span className="text-red-500">*</span></Label>
                    <Input id="postal_code" placeholder="10100" {...register('postal_code')} disabled={isLoading} />
                    {errors.postal_code && <p className="text-sm text-red-500">{errors.postal_code.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="country">País <span className="text-red-500">*</span></Label>
                    <Input id="country" placeholder="República Dominicana" {...register('country')} disabled={isLoading} />
                    {errors.country && <p className="text-sm text-red-500">{errors.country.message}</p>}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* === 5. INFORMACIÓN LABORAL === */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Información Laboral</CardTitle>
                <CardDescription>Datos de empleo e ingresos (opcional)</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="employment_status">Estado Laboral</Label>
                    <Select id="employment_status" {...register('employment_status')} disabled={isLoading}>
                      <option value="">Seleccionar...</option>
                      <option value="employed">Empleado</option>
                      <option value="self_employed">Trabajador Independiente</option>
                      <option value="unemployed">Desempleado</option>
                      <option value="retired">Retirado</option>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="employer_name">Nombre del Empleador</Label>
                    <Input id="employer_name" placeholder="Empresa XYZ" {...register('employer_name')} disabled={isLoading} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="occupation">Ocupación</Label>
                    <Input id="occupation" placeholder="Ingeniero, Contador, etc." {...register('occupation')} disabled={isLoading} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="employment_start_date">Fecha de Ingreso al Empleo</Label>
                    <Input id="employment_start_date" type="date" {...register('employment_start_date')} disabled={isLoading} />
                    <p className="text-xs text-gray-500">Para evaluar estabilidad laboral</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="monthly_income">Ingreso Mensual (RD$)</Label>
                    <Input id="monthly_income" type="number" step="0.01" placeholder="0.00" {...register('monthly_income')} disabled={isLoading} />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* === 6. NOTAS === */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Notas Adicionales</CardTitle>
                <CardDescription>Información adicional sobre el cliente (opcional)</CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  id="notes"
                  placeholder="Notas, comentarios o información relevante..."
                  rows={4}
                  {...register('notes')}
                  disabled={isLoading}
                />
              </CardContent>
            </Card>

            {/* === Actions === */}
            <div className="flex justify-end gap-3">
              <Link href="/customers">
                <Button type="button" variant="outline" disabled={isLoading}>
                  Cancelar
                </Button>
              </Link>
              <Button type="submit" disabled={isLoading} className="bg-[#163300] hover:bg-[#0f2400] text-white">
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                <Save className="mr-2 h-4 w-4" />
                Guardar Cliente
              </Button>
            </div>
          </div>
        </form>
        </div>
      </div>
    </div>
  );
}