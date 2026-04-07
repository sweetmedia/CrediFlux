'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { contractTemplatesAPI, ContractTemplate, ContractVariable } from '@/lib/api/contracts';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  Save,
  ArrowLeft,
  FileText,
} from 'lucide-react';

export default function EditContractTemplatePage() {
  const router = useRouter();
  const params = useParams();
  const templateId = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingTemplate, setIsLoadingTemplate] = useState(true);
  const [error, setError] = useState<string>('');
  const [variables, setVariables] = useState<ContractVariable[]>([]);
  const [loadingVariables, setLoadingVariables] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    content: '',
    footer_text: '',
    is_active: true,
    is_default: false,
  });

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load template and variables
  useEffect(() => {
    if (isAuthenticated && templateId) {
      loadTemplate();
      loadVariables();
    }
  }, [isAuthenticated, templateId]);

  const loadTemplate = async () => {
    try {
      setIsLoadingTemplate(true);
      setError('');
      const template = await contractTemplatesAPI.getTemplate(templateId);
      setFormData({
        name: template.name,
        description: template.description || '',
        content: template.content,
        footer_text: template.footer_text || '',
        is_active: template.is_active,
        is_default: template.is_default,
      });
    } catch (err: any) {
      console.error('Error loading template:', err);
      setError('Error al cargar la plantilla');
    } finally {
      setIsLoadingTemplate(false);
    }
  };

  const loadVariables = async () => {
    try {
      setLoadingVariables(true);
      const response = await contractTemplatesAPI.getVariables();
      setVariables(response.variables || []);
    } catch (err: any) {
      console.error('Error loading variables:', err);
    } finally {
      setLoadingVariables(false);
    }
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSwitchChange = (name: string, checked: boolean) => {
    setFormData((prev) => ({ ...prev, [name]: checked }));
  };

  const insertVariable = (variable: string) => {
    const textarea = document.querySelector(
      'textarea[name="content"]'
    ) as HTMLTextAreaElement;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = formData.content;
      const before = text.substring(0, start);
      const after = text.substring(end, text.length);
      const newContent = before + variable + after;
      setFormData((prev) => ({ ...prev, content: newContent }));

      // Set cursor position after inserted variable
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd =
          start + variable.length;
        textarea.focus();
      }, 0);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.name.trim()) {
      setError('El nombre es requerido');
      return;
    }

    if (!formData.content.trim()) {
      setError('El contenido de la plantilla es requerido');
      return;
    }

    try {
      setIsLoading(true);

      const submitData: any = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        content: formData.content,
        footer_text: formData.footer_text,
        is_active: formData.is_active,
        is_default: formData.is_default,
      };

      await contractTemplatesAPI.updateTemplate(templateId, submitData);
      router.push('/contract-templates');
    } catch (err: any) {
      console.error('Error updating template:', err);
      setError(
        err.response?.data?.message ||
          err.message ||
          'Error al actualizar la plantilla'
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || isLoadingTemplate) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link href="/contract-templates">
                <Button
                  variant="outline"
                  size="sm"
                  className="border-slate-200"
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Volver
                </Button>
              </Link>
              <h1 className="text-2xl font-bold text-slate-900">
                Editar Plantilla de Contrato
              </h1>
            </div>
            <p className="text-sm text-slate-600">
              Modifica la plantilla para actualizar los contratos generados
            </p>
          </div>
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Form */}
            <div className="lg:col-span-2 space-y-6">
              {/* Basic Info Card */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="border-b border-slate-200 bg-white">
                  <CardTitle className="text-lg font-semibold text-slate-900">
                    Información Básica
                  </CardTitle>
                  <CardDescription className="text-sm text-slate-600">
                    Detalles generales de la plantilla
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                  <div>
                    <Label htmlFor="name" className="text-sm font-medium text-slate-700">
                      Nombre de la Plantilla *
                    </Label>
                    <Input
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      placeholder="Ej: Contrato de Préstamo Personal"
                      className="mt-1.5 border-slate-200"
                      required
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="description"
                      className="text-sm font-medium text-slate-700"
                    >
                      Descripción
                    </Label>
                    <Textarea
                      id="description"
                      name="description"
                      value={formData.description}
                      onChange={handleInputChange}
                      placeholder="Describe el propósito de esta plantilla..."
                      className="mt-1.5 border-slate-200 min-h-[100px]"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Content Card */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="border-b border-slate-200 bg-white">
                  <CardTitle className="text-lg font-semibold text-slate-900">
                    Contenido del Contrato *
                  </CardTitle>
                  <CardDescription className="text-sm text-slate-600">
                    Usa las variables disponibles para personalizar el contrato
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                  <Textarea
                    name="content"
                    value={formData.content}
                    onChange={handleInputChange}
                    placeholder="Escribe el contenido del contrato aquí. Usa las variables del panel derecho para insertar datos dinámicos..."
                    className="border-slate-200 min-h-[400px] font-mono text-sm"
                    required
                  />
                  <p className="text-xs text-slate-500 mt-2">
                    Haz clic en las variables del panel derecho para insertarlas
                    en el contenido
                  </p>
                </CardContent>
              </Card>

              {/* Footer Card */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="border-b border-slate-200 bg-white">
                  <CardTitle className="text-lg font-semibold text-slate-900">
                    Pie de Página
                  </CardTitle>
                  <CardDescription className="text-sm text-slate-600">
                    Texto que aparecerá al final del contrato
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                  <Textarea
                    name="footer_text"
                    value={formData.footer_text}
                    onChange={handleInputChange}
                    placeholder="Ej: Este documento es válido con las firmas digitales correspondientes..."
                    className="border-slate-200 min-h-[100px]"
                  />
                </CardContent>
              </Card>

              {/* Settings Card */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="border-b border-slate-200 bg-white">
                  <CardTitle className="text-lg font-semibold text-slate-900">
                    Configuración
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-sm font-medium text-slate-700">
                        Plantilla Activa
                      </Label>
                      <p className="text-xs text-slate-600">
                        Permite usar esta plantilla para generar contratos
                      </p>
                    </div>
                    <Switch
                      checked={formData.is_active}
                      onCheckedChange={(checked) =>
                        handleSwitchChange('is_active', checked)
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-sm font-medium text-slate-700">
                        Plantilla por Defecto
                      </Label>
                      <p className="text-xs text-slate-600">
                        Seleccionar automáticamente al crear contratos
                      </p>
                    </div>
                    <Switch
                      checked={formData.is_default}
                      onCheckedChange={(checked) =>
                        handleSwitchChange('is_default', checked)
                      }
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Sidebar - Variables */}
            <div className="lg:col-span-1">
              <Card className="border-slate-200 shadow-sm sticky top-8">
                <CardHeader className="border-b border-slate-200 bg-white">
                  <CardTitle className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                    <FileText className="h-5 w-5 text-blue-600" />
                    Variables Disponibles
                  </CardTitle>
                  <CardDescription className="text-sm text-slate-600">
                    Haz clic para insertar en el contenido
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-4">
                  {loadingVariables ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-[calc(100vh-300px)] overflow-y-auto">
                      {variables.map((v) => (
                        <button
                          key={v.variable}
                          type="button"
                          onClick={() => insertVariable(v.variable)}
                          className="w-full text-left p-3 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50 transition-colors group"
                        >
                          <code className="text-xs font-mono text-blue-600 font-semibold">
                            {v.variable}
                          </code>
                          <p className="text-xs text-slate-600 mt-1">
                            {v.description}
                          </p>
                        </button>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex items-center justify-end gap-3">
            <Link href="/contract-templates">
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
              disabled={isLoading}
            >
              {isLoading ? (
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
    </div>
  );
}
