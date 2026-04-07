'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Loader2,
  Plus,
  Search,
  FileText,
  Edit,
  Copy,
  Trash2,
  Star,
  CheckCircle,
  XCircle,
  Eye,
} from 'lucide-react';

export default function ContractTemplatesPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [templates, setTemplates] = useState<ContractTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<ContractTemplate | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load templates
  useEffect(() => {
    if (isAuthenticated) {
      loadTemplates();
    }
  }, [isAuthenticated, currentPage, searchTerm]);

  const loadTemplates = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: any = {
        page: currentPage,
      };

      if (searchTerm) params.search = searchTerm;

      const response = await contractTemplatesAPI.getTemplates(params);
      setTemplates(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error loading templates:', err);
      setError('Error al cargar las plantillas de contratos');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  const handleSetDefault = async (id: string) => {
    try {
      await contractTemplatesAPI.setDefault(id);
      loadTemplates();
    } catch (err: any) {
      console.error('Error setting default:', err);
      setError('Error al establecer plantilla por defecto');
    }
  };

  const handleDuplicate = async (id: string) => {
    try {
      await contractTemplatesAPI.duplicate(id);
      loadTemplates();
    } catch (err: any) {
      console.error('Error duplicating template:', err);
      setError('Error al duplicar plantilla');
    }
  };

  const handleDelete = async () => {
    if (!selectedTemplate) return;

    try {
      await contractTemplatesAPI.deleteTemplate(selectedTemplate.id);
      setDeleteDialogOpen(false);
      setSelectedTemplate(null);
      loadTemplates();
    } catch (err: any) {
      console.error('Error deleting template:', err);
      setError('Error al eliminar plantilla');
    }
  };

  const totalPages = Math.ceil(totalCount / 10);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Plantillas de Contratos</h1>
          <p className="text-sm text-slate-600 mt-1">
            Gestiona las plantillas de contratos para generar documentos personalizados
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Total Plantillas
                  </p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">{totalCount}</p>
                </div>
                <div className="rounded-xl bg-blue-100 p-3">
                  <FileText className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Activas
                  </p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">
                    {templates.filter((t) => t.is_active).length}
                  </p>
                </div>
                <div className="rounded-xl bg-green-100 p-3">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Por Defecto
                  </p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">
                    {templates.filter((t) => t.is_default).length}
                  </p>
                </div>
                <div className="rounded-xl bg-yellow-100 p-3">
                  <Star className="h-6 w-6 text-yellow-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Main Content Card */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="border-b border-slate-200 bg-white p-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Lista de Plantillas
                </CardTitle>
                <CardDescription className="text-sm text-slate-600 mt-1">
                  {totalCount} plantilla{totalCount !== 1 ? 's' : ''} disponible
                  {totalCount !== 1 ? 's' : ''}
                </CardDescription>
              </div>
              <div className="flex gap-3">
                <div className="relative w-80">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Buscar plantillas..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="pl-10 border-slate-200"
                  />
                </div>
                <Link href="/contract-templates/new">
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    <Plus className="mr-2 h-4 w-4" />
                    Nueva Plantilla
                  </Button>
                </Link>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
                <p className="text-slate-600">Cargando plantillas...</p>
              </div>
            ) : templates.length === 0 ? (
              <div className="text-center py-12">
                <div className="rounded-xl bg-slate-100 p-6 w-20 h-20 mx-auto mb-4 flex items-center justify-center">
                  <FileText className="h-10 w-10 text-slate-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  No hay plantillas
                </h3>
                <p className="text-sm text-slate-600 mb-6">
                  {searchTerm
                    ? 'No se encontraron plantillas con ese criterio'
                    : 'Crea tu primera plantilla de contrato'}
                </p>
                <Link href="/contract-templates/new">
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    <Plus className="mr-2 h-4 w-4" />
                    Crear Primera Plantilla
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-slate-200">
                {templates.map((template) => (
                  <div
                    key={template.id}
                    className="p-6 hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="text-lg font-semibold text-slate-900">
                            {template.name}
                          </h3>
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
                          <p className="text-sm text-slate-600 mb-3">
                            {template.description}
                          </p>
                        )}
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                          <span>Creado: {new Date(template.created_at).toLocaleDateString('es-ES')}</span>
                          {template.created_by_name && (
                            <span>Por: {template.created_by_name}</span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 ml-4">
                        <Link href={`/contract-templates/${template.id}`}>
                          <Button
                            variant="outline"
                            size="sm"
                            className="border-slate-200"
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            Ver
                          </Button>
                        </Link>
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
                          onClick={() => handleDuplicate(template.id)}
                          className="border-slate-200"
                        >
                          <Copy className="h-4 w-4 mr-1" />
                          Duplicar
                        </Button>
                        {!template.is_default && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSetDefault(template.id)}
                            className="border-slate-200"
                          >
                            <Star className="h-4 w-4 mr-1" />
                            Default
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setSelectedTemplate(template);
                            setDeleteDialogOpen(true);
                          }}
                          className="border-red-200 text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirmar Eliminación</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas eliminar la plantilla "
                {selectedTemplate?.name}"? Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <div className="flex justify-end gap-3 mt-4">
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
              >
                Eliminar
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
