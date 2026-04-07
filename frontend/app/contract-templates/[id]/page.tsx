'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { contractTemplatesAPI, ContractTemplate } from '@/lib/api/contracts';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  ArrowLeft,
  Edit,
  Copy,
  Trash2,
  Star,
  CheckCircle,
  XCircle,
  FileText,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export default function ViewContractTemplatePage() {
  const router = useRouter();
  const params = useParams();
  const templateId = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [template, setTemplate] = useState<ContractTemplate | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load template
  useEffect(() => {
    if (isAuthenticated && templateId) {
      loadTemplate();
    }
  }, [isAuthenticated, templateId]);

  const loadTemplate = async () => {
    try {
      setIsLoading(true);
      setError('');
      const data = await contractTemplatesAPI.getTemplate(templateId);
      setTemplate(data);
    } catch (err: any) {
      console.error('Error loading template:', err);
      setError('Error al cargar la plantilla');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetDefault = async () => {
    if (!template) return;
    try {
      await contractTemplatesAPI.setDefault(template.id);
      loadTemplate();
    } catch (err: any) {
      console.error('Error setting default:', err);
      setError('Error al establecer plantilla por defecto');
    }
  };

  const handleDuplicate = async () => {
    if (!template) return;
    try {
      await contractTemplatesAPI.duplicate(template.id);
      router.push('/contract-templates');
    } catch (err: any) {
      console.error('Error duplicating template:', err);
      setError('Error al duplicar plantilla');
    }
  };

  const handleDelete = async () => {
    if (!template) return;
    try {
      await contractTemplatesAPI.deleteTemplate(template.id);
      router.push('/contract-templates');
    } catch (err: any) {
      console.error('Error deleting template:', err);
      setError('Error al eliminar plantilla');
      setDeleteDialogOpen(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error && !template) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="container mx-auto max-w-6xl">
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <div className="mt-4">
            <Link href="/contract-templates">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver a Plantillas
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!template) return null;

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Link href="/contract-templates">
              <Button variant="outline" size="sm" className="border-slate-200">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Volver
              </Button>
            </Link>
          </div>

          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <h1 className="text-2xl font-bold text-slate-900">
                  {template.name}
                </h1>
                {template.is_default && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    <Star className="h-3 w-3" />
                    Por Defecto
                  </span>
                )}
                {template.is_active ? (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <CheckCircle className="h-3 w-3" />
                    Activa
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    <XCircle className="h-3 w-3" />
                    Inactiva
                  </span>
                )}
              </div>
              {template.description && (
                <p className="text-sm text-slate-600">{template.description}</p>
              )}
            </div>

            <div className="flex items-center gap-2 ml-4">
              <Link href={`/contract-templates/${template.id}/edit`}>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-slate-200"
                >
                  <Edit className="h-4 w-4 mr-1" />
                  Editar
                </Button>
              </Link>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDuplicate}
                className="border-slate-200"
              >
                <Copy className="h-4 w-4 mr-1" />
                Duplicar
              </Button>
              {!template.is_default && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSetDefault}
                  className="border-slate-200"
                >
                  <Star className="h-4 w-4 mr-1" />
                  Marcar como Default
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteDialogOpen(true)}
                className="border-red-200 text-red-600 hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Template Content */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Contenido del Contrato
                </CardTitle>
                <CardDescription className="text-sm text-slate-600">
                  Plantilla con variables dinámicas
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-6">
                  <pre className="whitespace-pre-wrap text-sm text-slate-700 font-mono">
                    {template.content}
                  </pre>
                </div>
              </CardContent>
            </Card>

            {/* Footer Text */}
            {template.footer_text && (
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="border-b border-slate-200 bg-white">
                  <CardTitle className="text-lg font-semibold text-slate-900">
                    Pie de Página
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">
                    {template.footer_text}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar - Metadata */}
          <div className="lg:col-span-1 space-y-6">
            {/* Settings */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Información
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                    Estado
                  </p>
                  <div className="flex items-center gap-2">
                    {template.is_active ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <CheckCircle className="h-3 w-3" />
                        Activa
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <XCircle className="h-3 w-3" />
                        Inactiva
                      </span>
                    )}
                    {template.is_default && (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        <Star className="h-3 w-3" />
                        Por Defecto
                      </span>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-200">
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                    Creado
                  </p>
                  <p className="text-sm text-slate-700">
                    {new Date(template.created_at).toLocaleDateString('es-ES', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </p>
                  {template.created_by_name && (
                    <p className="text-xs text-slate-600 mt-1">
                      Por: {template.created_by_name}
                    </p>
                  )}
                </div>

                <div className="pt-4 border-t border-slate-200">
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                    Última Actualización
                  </p>
                  <p className="text-sm text-slate-700">
                    {new Date(template.updated_at).toLocaleDateString('es-ES', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Usage Info */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200 bg-white">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Uso
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="text-center py-4">
                  <FileText className="h-12 w-12 text-slate-400 mx-auto mb-3" />
                  <p className="text-sm text-slate-600">
                    Esta plantilla puede ser usada para generar contratos de
                    préstamo personalizados
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirmar Eliminación</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas eliminar la plantilla "
                {template.name}"? Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <div className="flex justify-end gap-3 mt-4">
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button variant="destructive" onClick={handleDelete}>
                Eliminar
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
