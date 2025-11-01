'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { tenantsAPI, Tenant, TenantUpdateData } from '@/lib/api/tenants';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Loader2,
  Save,
  Percent,
  DollarSign,
  Calendar,
  CreditCard,
  FileText,
  Shield,
  Settings,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
} from 'lucide-react';
import Link from 'next/link';

const loanSettingsSchema = z.object({
  // Interest Rates
  default_interest_rate: z.number().min(0).max(100).optional(),
  min_interest_rate: z.number().min(0).max(100).optional(),
  max_interest_rate: z.number().min(0).max(100).optional(),

  // Loan Amounts
  min_loan_amount: z.number().min(0).optional(),
  max_loan_amount: z.number().min(0).optional(),

  // Loan Terms
  default_loan_term_months: z.number().min(1).optional(),
  min_loan_term_months: z.number().min(1).optional(),
  max_loan_term_months: z.number().min(1).optional(),

  // Payment Configuration
  default_payment_frequency: z.string().optional(),
  default_loan_type: z.string().optional(),
  default_grace_period_days: z.number().min(0).optional(),

  // Auto-Approval
  enable_auto_approval: z.boolean().optional(),
  auto_approval_max_amount: z.number().min(0).optional(),

  // Collateral
  require_collateral_default: z.boolean().optional(),
  collateral_required_above: z.number().min(0).optional(),

  // Disbursement
  require_disbursement_approval: z.boolean().optional(),
  allow_partial_disbursement: z.boolean().optional(),

  // Credit Score
  require_credit_score: z.boolean().optional(),
  minimum_credit_score: z.number().min(300).max(850).optional(),
  credit_score_for_auto_approval: z.number().min(300).max(850).optional(),

  // Currency
  default_currency: z.string().optional(),
  allow_multiple_currencies: z.boolean().optional(),

  // Payment Methods
  enable_cash_payments: z.boolean().optional(),
  enable_check_payments: z.boolean().optional(),
  enable_bank_transfer_payments: z.boolean().optional(),
  enable_card_payments: z.boolean().optional(),
  enable_mobile_payments: z.boolean().optional(),

  // Documents
  require_id_document: z.boolean().optional(),
  require_proof_of_income: z.boolean().optional(),
  require_proof_of_address: z.boolean().optional(),
  require_bank_statement: z.boolean().optional(),
  require_employment_letter: z.boolean().optional(),
  enhanced_verification_amount: z.number().min(0).optional(),

  // Additional Settings
  allow_early_repayment: z.boolean().optional(),
  early_repayment_penalty: z.number().min(0).max(100).optional(),
  require_guarantor: z.boolean().optional(),
  guarantor_required_above: z.number().min(0).optional(),
  max_active_loans_per_customer: z.number().min(1).optional(),

  // Late Fees
  late_fee_type: z.string().optional(),
  late_fee_percentage: z.number().min(0).optional(),
  late_fee_fixed_amount: z.number().min(0).optional(),
  late_fee_frequency: z.string().optional(),
  grace_period_days: z.number().min(0).optional(),

  // Notifications
  enable_email_reminders: z.boolean().optional(),
  enable_sms_reminders: z.boolean().optional(),
  enable_whatsapp_reminders: z.boolean().optional(),
  reminder_days_before: z.number().min(0).optional(),
  notification_email_from: z.string().email().optional().or(z.literal('')),
});

type LoanSettingsFormData = z.infer<typeof loanSettingsSchema>;

export default function LoanSettingsPage() {
  const { user, tenant: authTenant, isAuthenticated, isLoading: authLoading, refreshTenant } = useAuth();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
    setValue,
  } = useForm<LoanSettingsFormData>({
    resolver: zodResolver(loanSettingsSchema),
  });

  // Watch for boolean fields to sync with UI
  const watchEnableAutoApproval = watch('enable_auto_approval');
  const watchRequireCollateral = watch('require_collateral_default');
  const watchRequireCreditScore = watch('require_credit_score');
  const watchRequireGuarantor = watch('require_guarantor');
  const watchLateFeeType = watch('late_fee_type');

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchTenantSettings();
    }
  }, [authLoading, isAuthenticated]);

  const fetchTenantSettings = async () => {
    try {
      setIsLoading(true);
      const data = await tenantsAPI.getSettings();
      setTenant(data);

      // Reset form with tenant data
      reset({
        default_interest_rate: data.default_interest_rate || 12,
        min_interest_rate: data.min_interest_rate || 5,
        max_interest_rate: data.max_interest_rate || 36,
        min_loan_amount: data.min_loan_amount || 100,
        max_loan_amount: data.max_loan_amount || 50000,
        default_loan_term_months: data.default_loan_term_months || 12,
        min_loan_term_months: data.min_loan_term_months || 1,
        max_loan_term_months: data.max_loan_term_months || 60,
        default_payment_frequency: data.default_payment_frequency || 'monthly',
        default_loan_type: data.default_loan_type || 'personal',
        default_grace_period_days: data.default_grace_period_days || 0,
        enable_auto_approval: data.enable_auto_approval || false,
        auto_approval_max_amount: data.auto_approval_max_amount || 1000,
        require_collateral_default: data.require_collateral_default || false,
        collateral_required_above: data.collateral_required_above || 10000,
        require_disbursement_approval: data.require_disbursement_approval !== false,
        allow_partial_disbursement: data.allow_partial_disbursement || false,
        require_credit_score: data.require_credit_score || false,
        minimum_credit_score: data.minimum_credit_score || 300,
        credit_score_for_auto_approval: data.credit_score_for_auto_approval || 700,
        default_currency: data.default_currency || 'USD',
        allow_multiple_currencies: data.allow_multiple_currencies || false,
        enable_cash_payments: data.enable_cash_payments !== false,
        enable_check_payments: data.enable_check_payments !== false,
        enable_bank_transfer_payments: data.enable_bank_transfer_payments !== false,
        enable_card_payments: data.enable_card_payments || false,
        enable_mobile_payments: data.enable_mobile_payments || false,
        require_id_document: data.require_id_document !== false,
        require_proof_of_income: data.require_proof_of_income !== false,
        require_proof_of_address: data.require_proof_of_address || false,
        require_bank_statement: data.require_bank_statement || false,
        require_employment_letter: data.require_employment_letter || false,
        enhanced_verification_amount: data.enhanced_verification_amount || 5000,
        allow_early_repayment: data.allow_early_repayment !== false,
        early_repayment_penalty: data.early_repayment_penalty || 0,
        require_guarantor: data.require_guarantor || false,
        guarantor_required_above: data.guarantor_required_above || 10000,
        max_active_loans_per_customer: data.max_active_loans_per_customer || 3,
        late_fee_type: data.late_fee_type || 'percentage',
        late_fee_percentage: data.late_fee_percentage || 5,
        late_fee_fixed_amount: data.late_fee_fixed_amount || 0,
        late_fee_frequency: data.late_fee_frequency || 'monthly',
        grace_period_days: data.grace_period_days || 0,
        enable_email_reminders: data.enable_email_reminders !== false,
        enable_sms_reminders: data.enable_sms_reminders || false,
        enable_whatsapp_reminders: data.enable_whatsapp_reminders !== false,
        reminder_days_before: data.reminder_days_before || 3,
        notification_email_from: data.notification_email_from || '',
      });
    } catch (err: any) {
      setError(err.message || 'Error al cargar la configuración');
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmit = async (data: LoanSettingsFormData) => {
    try {
      setIsSaving(true);
      setError('');
      setSuccessMessage('');

      await tenantsAPI.updateSettings(data as TenantUpdateData);
      await refreshTenant();

      setSuccessMessage('Configuración de préstamos actualizada exitosamente');
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar la configuración');
    } finally {
      setIsSaving(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            href="/settings"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-2"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Configuración
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">Configuración de Préstamos</h1>
          <p className="text-muted-foreground">
            Configura las reglas y límites para los préstamos de tu organización
          </p>
        </div>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">{successMessage}</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Tabs defaultValue="basic" className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="basic">Básico</TabsTrigger>
            <TabsTrigger value="advanced">Avanzado</TabsTrigger>
            <TabsTrigger value="payments">Pagos</TabsTrigger>
            <TabsTrigger value="documents">Documentos</TabsTrigger>
            <TabsTrigger value="notifications">Notificaciones</TabsTrigger>
          </TabsList>

          {/* BASIC TAB */}
          <TabsContent value="basic" className="space-y-6">
            {/* Interest Rates */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Percent className="h-5 w-5 text-primary" />
                  <CardTitle>Tasas de Interés</CardTitle>
                </div>
                <CardDescription>
                  Configura las tasas de interés permitidas para los préstamos
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="default_interest_rate">
                    Tasa Predeterminada (% anual)
                  </Label>
                  <Input
                    id="default_interest_rate"
                    type="number"
                    step="0.01"
                    {...register('default_interest_rate', { valueAsNumber: true })}
                  />
                  {errors.default_interest_rate && (
                    <p className="text-sm text-red-500">{errors.default_interest_rate.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="min_interest_rate">Tasa Mínima (% anual)</Label>
                  <Input
                    id="min_interest_rate"
                    type="number"
                    step="0.01"
                    {...register('min_interest_rate', { valueAsNumber: true })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="max_interest_rate">Tasa Máxima (% anual)</Label>
                  <Input
                    id="max_interest_rate"
                    type="number"
                    step="0.01"
                    {...register('max_interest_rate', { valueAsNumber: true })}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Loan Amounts */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-primary" />
                  <CardTitle>Montos de Préstamo</CardTitle>
                </div>
                <CardDescription>
                  Define los límites de montos para los préstamos
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="min_loan_amount">Monto Mínimo</Label>
                  <Input
                    id="min_loan_amount"
                    type="number"
                    step="0.01"
                    {...register('min_loan_amount', { valueAsNumber: true })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="max_loan_amount">Monto Máximo</Label>
                  <Input
                    id="max_loan_amount"
                    type="number"
                    step="0.01"
                    {...register('max_loan_amount', { valueAsNumber: true })}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Loan Terms */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-primary" />
                  <CardTitle>Plazos de Préstamo</CardTitle>
                </div>
                <CardDescription>
                  Configura los plazos permitidos en meses
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="default_loan_term_months">Plazo Predeterminado (meses)</Label>
                  <Input
                    id="default_loan_term_months"
                    type="number"
                    {...register('default_loan_term_months', { valueAsNumber: true })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="min_loan_term_months">Plazo Mínimo (meses)</Label>
                  <Input
                    id="min_loan_term_months"
                    type="number"
                    {...register('min_loan_term_months', { valueAsNumber: true })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="max_loan_term_months">Plazo Máximo (meses)</Label>
                  <Input
                    id="max_loan_term_months"
                    type="number"
                    {...register('max_loan_term_months', { valueAsNumber: true })}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Default Settings */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Settings className="h-5 w-5 text-primary" />
                  <CardTitle>Configuración Predeterminada</CardTitle>
                </div>
                <CardDescription>
                  Valores predeterminados para nuevos préstamos
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="default_payment_frequency">Frecuencia de Pago</Label>
                  <Select
                    value={watch('default_payment_frequency')}
                    onValueChange={(value) => setValue('default_payment_frequency', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="daily">Diario</SelectItem>
                      <SelectItem value="weekly">Semanal</SelectItem>
                      <SelectItem value="biweekly">Quincenal</SelectItem>
                      <SelectItem value="monthly">Mensual</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="default_loan_type">Tipo de Préstamo</Label>
                  <Select
                    value={watch('default_loan_type')}
                    onValueChange={(value) => setValue('default_loan_type', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="personal">Personal</SelectItem>
                      <SelectItem value="business">Empresarial</SelectItem>
                      <SelectItem value="mortgage">Hipotecario</SelectItem>
                      <SelectItem value="auto">Vehicular</SelectItem>
                      <SelectItem value="education">Educativo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="default_grace_period_days">Días de Gracia</Label>
                  <Input
                    id="default_grace_period_days"
                    type="number"
                    {...register('default_grace_period_days', { valueAsNumber: true })}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Currency Settings */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-primary" />
                  <CardTitle>Configuración de Moneda</CardTitle>
                </div>
                <CardDescription>
                  Moneda predeterminada para los préstamos
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="default_currency">Moneda Predeterminada</Label>
                    <Select
                      value={watch('default_currency')}
                      onValueChange={(value) => setValue('default_currency', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Seleccionar..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="USD">US Dollar ($)</SelectItem>
                        <SelectItem value="DOP">Dominican Peso (RD$)</SelectItem>
                        <SelectItem value="EUR">Euro (€)</SelectItem>
                        <SelectItem value="GBP">British Pound (£)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center space-x-2 pt-7">
                    <Switch
                      id="allow_multiple_currencies"
                      checked={watch('allow_multiple_currencies')}
                      onCheckedChange={(checked) => setValue('allow_multiple_currencies', checked)}
                    />
                    <Label htmlFor="allow_multiple_currencies" className="cursor-pointer">
                      Permitir múltiples monedas
                    </Label>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ADVANCED TAB */}
          <TabsContent value="advanced" className="space-y-6">
            {/* Auto-Approval */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                  <CardTitle>Auto-Aprobación</CardTitle>
                </div>
                <CardDescription>
                  Configura la aprobación automática de préstamos
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="enable_auto_approval"
                    checked={watchEnableAutoApproval}
                    onCheckedChange={(checked) => setValue('enable_auto_approval', checked)}
                  />
                  <Label htmlFor="enable_auto_approval" className="cursor-pointer">
                    Habilitar auto-aprobación de préstamos
                  </Label>
                </div>

                {watchEnableAutoApproval && (
                  <div className="grid gap-4 md:grid-cols-2 pt-4">
                    <div className="space-y-2">
                      <Label htmlFor="auto_approval_max_amount">
                        Monto Máximo para Auto-Aprobación
                      </Label>
                      <Input
                        id="auto_approval_max_amount"
                        type="number"
                        step="0.01"
                        {...register('auto_approval_max_amount', { valueAsNumber: true })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="credit_score_for_auto_approval">
                        Score Crediticio Mínimo (300-850)
                      </Label>
                      <Input
                        id="credit_score_for_auto_approval"
                        type="number"
                        {...register('credit_score_for_auto_approval', { valueAsNumber: true })}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Credit Score */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  <CardTitle>Requisitos de Score Crediticio</CardTitle>
                </div>
                <CardDescription>
                  Configura los requisitos de historial crediticio
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="require_credit_score"
                    checked={watchRequireCreditScore}
                    onCheckedChange={(checked) => setValue('require_credit_score', checked)}
                  />
                  <Label htmlFor="require_credit_score" className="cursor-pointer">
                    Requerir score crediticio para aprobación
                  </Label>
                </div>

                {watchRequireCreditScore && (
                  <div className="grid gap-4 md:grid-cols-2 pt-4">
                    <div className="space-y-2">
                      <Label htmlFor="minimum_credit_score">
                        Score Crediticio Mínimo (300-850)
                      </Label>
                      <Input
                        id="minimum_credit_score"
                        type="number"
                        min="300"
                        max="850"
                        {...register('minimum_credit_score', { valueAsNumber: true })}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Collateral */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  <CardTitle>Requisitos de Colateral</CardTitle>
                </div>
                <CardDescription>
                  Configura los requisitos de garantía/colateral
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="require_collateral_default"
                    checked={watchRequireCollateral}
                    onCheckedChange={(checked) => setValue('require_collateral_default', checked)}
                  />
                  <Label htmlFor="require_collateral_default" className="cursor-pointer">
                    Requerir colateral por defecto
                  </Label>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="collateral_required_above">
                    Requerir colateral para préstamos mayores a
                  </Label>
                  <Input
                    id="collateral_required_above"
                    type="number"
                    step="0.01"
                    {...register('collateral_required_above', { valueAsNumber: true })}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Guarantor */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  <CardTitle>Requisitos de Garante</CardTitle>
                </div>
                <CardDescription>
                  Configura los requisitos de fiador/garante
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="require_guarantor"
                    checked={watchRequireGuarantor}
                    onCheckedChange={(checked) => setValue('require_guarantor', checked)}
                  />
                  <Label htmlFor="require_guarantor" className="cursor-pointer">
                    Requerir garante por defecto
                  </Label>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="guarantor_required_above">
                    Requerir garante para préstamos mayores a
                  </Label>
                  <Input
                    id="guarantor_required_above"
                    type="number"
                    step="0.01"
                    {...register('guarantor_required_above', { valueAsNumber: true })}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Disbursement */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-primary" />
                  <CardTitle>Configuración de Desembolso</CardTitle>
                </div>
                <CardDescription>
                  Opciones para el desembolso de fondos
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="require_disbursement_approval"
                    checked={watch('require_disbursement_approval')}
                    onCheckedChange={(checked) =>
                      setValue('require_disbursement_approval', checked)
                    }
                  />
                  <Label htmlFor="require_disbursement_approval" className="cursor-pointer">
                    Requiere aprobación adicional para desembolsar
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="allow_partial_disbursement"
                    checked={watch('allow_partial_disbursement')}
                    onCheckedChange={(checked) => setValue('allow_partial_disbursement', checked)}
                  />
                  <Label htmlFor="allow_partial_disbursement" className="cursor-pointer">
                    Permitir desembolsos parciales
                  </Label>
                </div>
              </CardContent>
            </Card>

            {/* Early Repayment */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-primary" />
                  <CardTitle>Pago Anticipado</CardTitle>
                </div>
                <CardDescription>
                  Configura las opciones de pago anticipado
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="allow_early_repayment"
                    checked={watch('allow_early_repayment')}
                    onCheckedChange={(checked) => setValue('allow_early_repayment', checked)}
                  />
                  <Label htmlFor="allow_early_repayment" className="cursor-pointer">
                    Permitir pago anticipado
                  </Label>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="early_repayment_penalty">
                    Penalidad por pago anticipado (% del saldo restante)
                  </Label>
                  <Input
                    id="early_repayment_penalty"
                    type="number"
                    step="0.01"
                    {...register('early_repayment_penalty', { valueAsNumber: true })}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Additional Settings */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Settings className="h-5 w-5 text-primary" />
                  <CardTitle>Configuraciones Adicionales</CardTitle>
                </div>
                <CardDescription>
                  Otras restricciones y límites
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Label htmlFor="max_active_loans_per_customer">
                  Máximo de préstamos activos por cliente
                </Label>
                <Input
                  id="max_active_loans_per_customer"
                  type="number"
                  {...register('max_active_loans_per_customer', { valueAsNumber: true })}
                />
              </CardContent>
            </Card>
          </TabsContent>

          {/* PAYMENTS TAB */}
          <TabsContent value="payments" className="space-y-6">
            {/* Payment Methods */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-primary" />
                  <CardTitle>Métodos de Pago Aceptados</CardTitle>
                </div>
                <CardDescription>
                  Selecciona los métodos de pago que acepta tu organización
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="enable_cash_payments"
                    checked={watch('enable_cash_payments')}
                    onCheckedChange={(checked) => setValue('enable_cash_payments', checked)}
                  />
                  <Label htmlFor="enable_cash_payments" className="cursor-pointer">
                    Aceptar pagos en efectivo
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="enable_check_payments"
                    checked={watch('enable_check_payments')}
                    onCheckedChange={(checked) => setValue('enable_check_payments', checked)}
                  />
                  <Label htmlFor="enable_check_payments" className="cursor-pointer">
                    Aceptar pagos con cheque
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="enable_bank_transfer_payments"
                    checked={watch('enable_bank_transfer_payments')}
                    onCheckedChange={(checked) =>
                      setValue('enable_bank_transfer_payments', checked)
                    }
                  />
                  <Label htmlFor="enable_bank_transfer_payments" className="cursor-pointer">
                    Aceptar transferencias bancarias
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="enable_card_payments"
                    checked={watch('enable_card_payments')}
                    onCheckedChange={(checked) => setValue('enable_card_payments', checked)}
                  />
                  <Label htmlFor="enable_card_payments" className="cursor-pointer">
                    Aceptar pagos con tarjeta de crédito/débito
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="enable_mobile_payments"
                    checked={watch('enable_mobile_payments')}
                    onCheckedChange={(checked) => setValue('enable_mobile_payments', checked)}
                  />
                  <Label htmlFor="enable_mobile_payments" className="cursor-pointer">
                    Aceptar pagos móviles (Yappy, ACH móvil)
                  </Label>
                </div>
              </CardContent>
            </Card>

            {/* Late Fees */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Percent className="h-5 w-5 text-primary" />
                  <CardTitle>Configuración de Mora</CardTitle>
                </div>
                <CardDescription>
                  Cargos por pagos atrasados
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="late_fee_type">Tipo de Cargo por Mora</Label>
                  <Select
                    value={watchLateFeeType}
                    onValueChange={(value) => setValue('late_fee_type', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="percentage">Porcentaje del Saldo</SelectItem>
                      <SelectItem value="fixed">Monto Fijo</SelectItem>
                      <SelectItem value="none">Sin Mora</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {watchLateFeeType === 'percentage' && (
                  <div className="space-y-2">
                    <Label htmlFor="late_fee_percentage">
                      Porcentaje de Mora (% del saldo vencido)
                    </Label>
                    <Input
                      id="late_fee_percentage"
                      type="number"
                      step="0.01"
                      {...register('late_fee_percentage', { valueAsNumber: true })}
                    />
                  </div>
                )}

                {watchLateFeeType === 'fixed' && (
                  <div className="space-y-2">
                    <Label htmlFor="late_fee_fixed_amount">Monto Fijo de Mora</Label>
                    <Input
                      id="late_fee_fixed_amount"
                      type="number"
                      step="0.01"
                      {...register('late_fee_fixed_amount', { valueAsNumber: true })}
                    />
                  </div>
                )}

                {watchLateFeeType !== 'none' && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="late_fee_frequency">Frecuencia de Aplicación</Label>
                      <Select
                        value={watch('late_fee_frequency')}
                        onValueChange={(value) => setValue('late_fee_frequency', value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Seleccionar..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="daily">Por Día</SelectItem>
                          <SelectItem value="monthly">Por Mes</SelectItem>
                          <SelectItem value="one_time">Único al Vencer</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="grace_period_days">
                        Días de Gracia (antes de aplicar mora)
                      </Label>
                      <Input
                        id="grace_period_days"
                        type="number"
                        {...register('grace_period_days', { valueAsNumber: true })}
                      />
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* DOCUMENTS TAB */}
          <TabsContent value="documents" className="space-y-6">
            {/* Document Requirements */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  <CardTitle>Requisitos de Documentación</CardTitle>
                </div>
                <CardDescription>
                  Documentos requeridos para solicitar un préstamo
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="require_id_document"
                    checked={watch('require_id_document')}
                    onCheckedChange={(checked) => setValue('require_id_document', checked)}
                  />
                  <Label htmlFor="require_id_document" className="cursor-pointer">
                    Requerir documento de identificación
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="require_proof_of_income"
                    checked={watch('require_proof_of_income')}
                    onCheckedChange={(checked) => setValue('require_proof_of_income', checked)}
                  />
                  <Label htmlFor="require_proof_of_income" className="cursor-pointer">
                    Requerir comprobante de ingresos
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="require_proof_of_address"
                    checked={watch('require_proof_of_address')}
                    onCheckedChange={(checked) => setValue('require_proof_of_address', checked)}
                  />
                  <Label htmlFor="require_proof_of_address" className="cursor-pointer">
                    Requerir comprobante de domicilio
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="require_bank_statement"
                    checked={watch('require_bank_statement')}
                    onCheckedChange={(checked) => setValue('require_bank_statement', checked)}
                  />
                  <Label htmlFor="require_bank_statement" className="cursor-pointer">
                    Requerir estado de cuenta bancario
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="require_employment_letter"
                    checked={watch('require_employment_letter')}
                    onCheckedChange={(checked) => setValue('require_employment_letter', checked)}
                  />
                  <Label htmlFor="require_employment_letter" className="cursor-pointer">
                    Requerir carta de empleo
                  </Label>
                </div>
              </CardContent>
            </Card>

            {/* Enhanced Verification */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  <CardTitle>Verificación Adicional</CardTitle>
                </div>
                <CardDescription>
                  Documentos adicionales requeridos para montos altos
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="enhanced_verification_amount">
                    Monto a partir del cual se requiere verificación adicional
                  </Label>
                  <Input
                    id="enhanced_verification_amount"
                    type="number"
                    step="0.01"
                    {...register('enhanced_verification_amount', { valueAsNumber: true })}
                  />
                </div>
                <p className="text-sm text-muted-foreground">
                  Para préstamos superiores a este monto, se pueden solicitar documentos
                  adicionales como estados de cuenta, declaraciones de impuestos, etc.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* NOTIFICATIONS TAB */}
          <TabsContent value="notifications" className="space-y-6">
            {/* Notification Settings */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Settings className="h-5 w-5 text-primary" />
                  <CardTitle>Configuración de Notificaciones</CardTitle>
                </div>
                <CardDescription>
                  Recordatorios y notificaciones a clientes
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="enable_email_reminders"
                    checked={watch('enable_email_reminders')}
                    onCheckedChange={(checked) => setValue('enable_email_reminders', checked)}
                  />
                  <Label htmlFor="enable_email_reminders" className="cursor-pointer">
                    Enviar recordatorios por email
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="enable_sms_reminders"
                    checked={watch('enable_sms_reminders')}
                    onCheckedChange={(checked) => setValue('enable_sms_reminders', checked)}
                  />
                  <Label htmlFor="enable_sms_reminders" className="cursor-pointer">
                    Enviar recordatorios por SMS
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="enable_whatsapp_reminders"
                    checked={watch('enable_whatsapp_reminders')}
                    onCheckedChange={(checked) => setValue('enable_whatsapp_reminders', checked)}
                  />
                  <Label htmlFor="enable_whatsapp_reminders" className="cursor-pointer">
                    Enviar recordatorios por WhatsApp
                  </Label>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="reminder_days_before">
                    Días antes del vencimiento para enviar recordatorio
                  </Label>
                  <Input
                    id="reminder_days_before"
                    type="number"
                    {...register('reminder_days_before', { valueAsNumber: true })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notification_email_from">
                    Email desde donde se envían notificaciones (opcional)
                  </Label>
                  <Input
                    id="notification_email_from"
                    type="email"
                    placeholder="notificaciones@tuempresa.com"
                    {...register('notification_email_from')}
                  />
                  {errors.notification_email_from && (
                    <p className="text-sm text-red-500">
                      {errors.notification_email_from.message}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Submit Button */}
        <div className="flex justify-end gap-4">
          <Button
            type="submit"
            disabled={isSaving}
            className="min-w-[150px]"
          >
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Guardando...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Guardar Cambios
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}