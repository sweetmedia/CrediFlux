'use client';

import { useSearchParams } from 'next/navigation';
import { ShieldX, ArrowLeft, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function AccessDeniedPage() {
  const searchParams = useSearchParams();
  const reason = searchParams.get('reason') || 'No tienes permisos para acceder a esta página.';
  const requiredPermission = searchParams.get('permission');
  const returnUrl = searchParams.get('returnUrl') || '/dashboard';

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <Card className="max-w-2xl w-full">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-red-100">
            <ShieldX className="h-10 w-10 text-red-600" />
          </div>
          <CardTitle className="text-3xl font-bold text-gray-900">
            Acceso Denegado
          </CardTitle>
          <CardDescription className="text-lg">
            No tienes los permisos necesarios para acceder a este recurso
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Main reason */}
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="ml-2">
              <strong>Razón:</strong> {reason}
            </AlertDescription>
          </Alert>

          {/* Required permission */}
          {requiredPermission && (
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <h3 className="font-semibold text-gray-900 mb-2">Permiso Requerido:</h3>
              <p className="text-sm text-gray-600 font-mono bg-white px-3 py-2 rounded border border-gray-200">
                {requiredPermission}
              </p>
            </div>
          )}

          {/* What to do */}
          <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
            <h3 className="font-semibold text-blue-900 mb-2">¿Qué puedes hacer?</h3>
            <ul className="text-sm text-blue-800 space-y-2">
              <li className="flex items-start">
                <span className="mr-2">•</span>
                <span>Contacta a tu administrador para solicitar los permisos necesarios</span>
              </li>
              <li className="flex items-start">
                <span className="mr-2">•</span>
                <span>Verifica que estés usando la cuenta correcta</span>
              </li>
              <li className="flex items-start">
                <span className="mr-2">•</span>
                <span>Regresa a una página donde tengas acceso</span>
              </li>
            </ul>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4">
            <Button
              asChild
              className="flex-1"
              variant="default"
            >
              <Link href={returnUrl}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver
              </Link>
            </Button>
            <Button
              asChild
              className="flex-1"
              variant="outline"
            >
              <Link href="/dashboard">
                Ir al Dashboard
              </Link>
            </Button>
          </div>

          {/* Help section */}
          <div className="text-center pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              ¿Necesitas ayuda? Contacta a tu administrador del sistema
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
