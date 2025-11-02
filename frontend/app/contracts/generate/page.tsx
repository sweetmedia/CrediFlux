'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { contractsAPI, contractTemplatesAPI, ContractTemplate } from '@/lib/api/contracts';
import { loansAPI, Loan } from '@/lib/api/loans';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
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
  FileText,
  CheckCircle2,
  Info,
} from 'lucide-react';

export default function GenerateContractPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const loanIdParam = searchParams.get('loan');
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  const [loans, setLoans] = useState<Loan[]>([]);
  const [templates, setTemplates] = useState<ContractTemplate[]>([]);
  const [selectedLoan, setSelectedLoan] = useState<Loan | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<ContractTemplate | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    loan: loanIdParam || '',
    template: '',
    special_terms: '',
    notes: '',
  });

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load initial data
  useEffect(() => {
    if (isAuthenticated) {
      loadInitialData();
    }
  }, [isAuthenticated]);

  const loadInitialData = async () => {
    try {
      setIsLoadingData(true);
      setError('');

      // Load active loans and templates in parallel
      const [loansResponse, templatesResponse] = await Promise.all([
        loansAPI.getLoans({ status: 'active', page_size: 100 }),
        contractTemplatesAPI.getTemplates({ is_active: true, page_size: 100 }),
      ]);

      setLoans(loansResponse.results || []);
      setTemplates(templatesResponse.results || []);

      // Set default template if available
      const defaultTemplate = templatesResponse.results?.find(
        (t: ContractTemplate) => t.is_default
      );
      if (defaultTemplate) {
        setFormData((prev) => ({ ...prev, template: defaultTemplate.id }));
        setSelectedTemplate(defaultTemplate);
      }

      // If loan is pre-selected from URL
      if (loanIdParam) {
        const loan = loansResponse.results?.find(
          (l: Loan) => l.id === loanIdParam
        );
        if (loan) {
          setSelectedLoan(loan);
        }
      }
    } catch (err: any) {
      console.error('Error loading data:', err);
      setError('Error al cargar los datos');
    } finally {
      setIsLoadingData(false);
    }
  };

  const handleLoanChange = (loanId: string) => {
    setFormData((prev) => ({ ...prev, loan: loanId }));
    const loan = loans.find((l) => l.id === loanId);
    setSelectedLoan(loan || null);
  };

  const handleTemplateChange = (templateId: string) => {
    setFormData((prev) => ({ ...prev, template: templateId }));
    const template = templates.find((t) => t.id === templateId);
    setSelectedTemplate(template || null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.loan) {
      setError('Debes seleccionar un préstamo');
      return;
    }

    try {
      setIsLoading(true);

      const submitData: any = {
        loan: formData.loan,
      };

      if (formData.template) {
        submitData.template = formData.template;
      }
      if (formData.special_terms.trim()) {
        submitData.special_terms = formData.special_terms.trim();
      }
      if (formData.notes.trim()) {
        submitData.notes = formData.notes.trim();
      }

      const newContract = await contractsAPI.createContract(submitData);
      setSuccess('Contrato generado exitosamente');

      // Redirect to contract view after a brief delay
      setTimeout(() => {
        router.push(`/contracts/${newContract.id}`);
      }, 1500);
    } catch (err: any) {
      console.error('Error generating contract:', err);
      const errorMessage =
        err.response?.data?.message ||
        err.response?.data?.error ||
        err.message ||
        'Error al generar el contrato';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || isLoadingData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="container mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Link href="/contracts">
              <Button variant="outline" size="sm" className="border-slate-200">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Volver
              </Button>
            </Link>
            <h1 className="text-2xl font-bold text-slate-900">
              Generar Contrato de Préstamo
            </h1>
          </div>
          <p className="text-sm text-slate-600">
            Selecciona un préstamo y una plantilla para generar el contrato
          </p>
        </div>

        {/* Success */}
        {success && (
          <Alert className="mb-6 border-green-200 bg-green-50">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              {success}
            </AlertDescription>
          </Alert>
        )}

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            {/* Loan Selection Card */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Seleccionar Préstamo *
                </CardTitle>
                <CardDescription className="text-sm text-slate-600">
                  Elige el préstamo para el cual generar el contrato
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div>
                  <Label
                    htmlFor="loan"
                    className="text-sm font-medium text-slate-700"
                  >
                    Préstamo
                  </Label>
                  <Select
                    value={formData.loan}
                    onValueChange={handleLoanChange}
                    required
                  >
                    <SelectTrigger className="mt-1.5 border-slate-200">
                      <SelectValue placeholder="Selecciona un préstamo..." />
                    </SelectTrigger>
                    <SelectContent>
                      {loans.length === 0 ? (
                        <div className="p-4 text-center text-sm text-slate-600">
                          No hay préstamos activos disponibles
                        </div>
                      ) : (
                        loans.map((loan) => (
                          <SelectItem key={loan.id} value={loan.id}>
                            {loan.loan_number} - {loan.customer_name} - $
                            {loan.principal_amount?.toLocaleString()}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                {/* Loan Details */}
                {selectedLoan && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                    <h4 className="text-sm font-semibold text-blue-900 mb-3">
                      Detalles del Préstamo
                    </h4>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <p className="text-blue-700 mb-1">Cliente</p>
                        <p className="text-blue-900 font-medium">
                          {selectedLoan.customer_name}
                        </p>
                      </div>
                      <div>
                        <p className="text-blue-700 mb-1">Monto</p>
                        <p className="text-blue-900 font-medium">
                          ${selectedLoan.principal_amount?.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-blue-700 mb-1">Tasa de Interés</p>
                        <p className="text-blue-900 font-medium">
                          {selectedLoan.interest_rate}%
                        </p>
                      </div>
                      <div>
                        <p className="text-blue-700 mb-1">Plazo</p>
                        <p className="text-blue-900 font-medium">
                          {selectedLoan.loan_term_months} meses
                        </p>
                      </div>
                      <div>
                        <p className="text-blue-700 mb-1">Estado</p>
                        <p className="text-blue-900 font-medium">
                          {selectedLoan.status}
                        </p>
                      </div>
                      <div>
                        <p className="text-blue-700 mb-1">Tipo de Préstamo</p>
                        <p className="text-blue-900 font-medium">
                          {selectedLoan.loan_type}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Template Selection Card */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Seleccionar Plantilla
                </CardTitle>
                <CardDescription className="text-sm text-slate-600">
                  Elige la plantilla de contrato (opcional - se usará la
                  predeterminada)
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div>
                  <Label
                    htmlFor="template"
                    className="text-sm font-medium text-slate-700"
                  >
                    Plantilla de Contrato
                  </Label>
                  <Select
                    value={formData.template}
                    onValueChange={handleTemplateChange}
                  >
                    <SelectTrigger className="mt-1.5 border-slate-200">
                      <SelectValue placeholder="Selecciona una plantilla..." />
                    </SelectTrigger>
                    <SelectContent>
                      {templates.length === 0 ? (
                        <div className="p-4 text-center text-sm text-slate-600">
                          No hay plantillas activas disponibles
                        </div>
                      ) : (
                        templates.map((template) => (
                          <SelectItem key={template.id} value={template.id}>
                            {template.name}
                            {template.is_default && ' (Por Defecto)'}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                {/* Template Details */}
                {selectedTemplate && (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mt-4">
                    <div className="flex items-start gap-3">
                      <FileText className="h-5 w-5 text-slate-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-sm font-semibold text-slate-900 mb-1">
                          {selectedTemplate.name}
                        </h4>
                        {selectedTemplate.description && (
                          <p className="text-xs text-slate-600">
                            {selectedTemplate.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Special Terms Card */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Términos Especiales
                </CardTitle>
                <CardDescription className="text-sm text-slate-600">
                  Agrega condiciones o términos específicos para este contrato
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <Textarea
                  name="special_terms"
                  value={formData.special_terms}
                  onChange={handleInputChange}
                  placeholder="Ej: El cliente acepta realizar pagos anticipados sin penalización..."
                  className="border-slate-200 min-h-[120px]"
                />
              </CardContent>
            </Card>

            {/* Notes Card */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Notas Internas
                </CardTitle>
                <CardDescription className="text-sm text-slate-600">
                  Notas privadas sobre este contrato (no visibles para el cliente)
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <Textarea
                  name="notes"
                  value={formData.notes}
                  onChange={handleInputChange}
                  placeholder="Ej: Solicitar copia de cédula actualizada..."
                  className="border-slate-200 min-h-[100px]"
                />
              </CardContent>
            </Card>

            {/* Info Alert */}
            <Alert className="border-blue-200 bg-blue-50">
              <Info className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800 text-sm">
                Al generar el contrato, se reemplazarán automáticamente todas las
                variables de la plantilla con los datos reales del préstamo y
                cliente.
              </AlertDescription>
            </Alert>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex items-center justify-end gap-3">
            <Link href="/contracts">
              <Button
                type="button"
                variant="outline"
                className="border-slate-200"
                disabled={isLoading}
              >
                Cancelar
              </Button>
            </Link>
            <Button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700"
              disabled={isLoading || !formData.loan}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generando...
                </>
              ) : (
                <>
                  <FileText className="mr-2 h-4 w-4" />
                  Generar Contrato
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
