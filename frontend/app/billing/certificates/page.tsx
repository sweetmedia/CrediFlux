'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { billingAPI } from '@/lib/api/billing';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  ArrowLeft,
  Shield,
  ShieldCheck,
  ShieldX,
  AlertTriangle,
  Trash2,
  Upload,
} from 'lucide-react';
import { DigitalCertificate } from '@/types/billing';

export default function CertificatesPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [certificates, setCertificates] = useState<DigitalCertificate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) loadCertificates();
  }, [isAuthenticated]);

  const loadCertificates = async () => {
    try {
      setIsLoading(true);
      const response = await billingAPI.getCertificates();
      setCertificates(response.results || []);
    } catch (err) {
      setError('Error al cargar los certificados');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('¿Estás seguro de eliminar este certificado?')) return;
    try {
      await billingAPI.deleteCertificate(id);
      setSuccess('Certificado eliminado');
      loadCertificates();
    } catch (err) {
      setError('Error al eliminar el certificado');
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const isExpired = (dateString: string | null) => {
    if (!dateString) return false;
    return new Date(dateString) < new Date();
  };

  const isExpiringSoon = (dateString: string | null) => {
    if (!dateString) return false;
    const expDate = new Date(dateString);
    const thirtyDays = new Date();
    thirtyDays.setDate(thirtyDays.getDate() + 30);
    return expDate <= thirtyDays && expDate > new Date();
  };

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
          Volver a Facturación
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Certificados Digitales</h1>
            <p className="text-sm text-slate-600 mt-1">
              Administra los certificados digitales para firma de e-CF (.p12 / .pfx)
            </p>
          </div>
          {/* Upload would need a dialog/form - simplified for MVP */}
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="mb-6 border-green-200 bg-green-50">
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* Certificates */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      ) : certificates.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="text-center py-12">
            <Shield className="h-12 w-12 text-slate-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-2">Sin certificados</h3>
            <p className="text-slate-600 mb-4">
              Sube un certificado digital (.p12/.pfx) para poder firmar e-CF
            </p>
            <p className="text-xs text-slate-500">
              Los certificados se suben desde el panel de administración Django por ahora.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {certificates.map((cert) => {
            const expired = isExpired(cert.valid_until);
            const expiring = isExpiringSoon(cert.valid_until);

            return (
              <Card key={cert.id} className={`border shadow-sm ${expired ? 'border-red-200 bg-red-50/30' : expiring ? 'border-orange-200 bg-orange-50/30' : 'border-slate-200'}`}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className={`
                        h-12 w-12 rounded-xl flex items-center justify-center
                        ${expired ? 'bg-red-100' : cert.is_active ? 'bg-green-100' : 'bg-slate-100'}
                      `}>
                        {expired ? (
                          <ShieldX className="h-6 w-6 text-red-600" />
                        ) : cert.is_active ? (
                          <ShieldCheck className="h-6 w-6 text-green-600" />
                        ) : (
                          <Shield className="h-6 w-6 text-slate-400" />
                        )}
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-slate-900">{cert.name}</h3>
                        <p className="text-sm text-slate-600">{cert.issuer || 'Emisor no especificado'}</p>
                        {cert.serial_number && (
                          <p className="text-xs text-slate-500 font-mono mt-1">SN: {cert.serial_number}</p>
                        )}
                        <div className="flex items-center gap-4 mt-3">
                          <div>
                            <p className="text-xs text-slate-500">Válido desde</p>
                            <p className="text-sm font-medium text-slate-900">{formatDate(cert.valid_from)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Válido hasta</p>
                            <p className={`text-sm font-medium ${expired ? 'text-red-600' : expiring ? 'text-orange-600' : 'text-slate-900'}`}>
                              {formatDate(cert.valid_until)}
                              {expired && ' (Expirado)'}
                              {expiring && ' (Próximo a expirar)'}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {cert.is_active ? (
                        <span className="inline-flex items-center rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
                          Activo
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                          Inactivo
                        </span>
                      )}
                      {expiring && (
                        <AlertTriangle className="h-5 w-5 text-orange-500" />
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-red-500 hover:text-red-700"
                        onClick={() => handleDelete(cert.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
